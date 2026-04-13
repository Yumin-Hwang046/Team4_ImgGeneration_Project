"""
이미지 생성 모듈

파이프라인:
  - 단일 SDXL 파이프라인 (Juggernaut XL v9)
  - ref_image 없음 → SDXL 배경 생성 (IP-Adapter 비활성)
  - ref_image 있음 → SDXL + IP-Adapter Plus (레퍼런스 스타일 반영)
  - 경계 인페인팅 → SD 1.5 inpainting (별도, 경량)
"""

import asyncio
import io
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import torch
from PIL import Image

# ─── 공통 상수 ────────────────────────────────────────────────

SIZE_MAP: dict[str, tuple[str, int, int]] = {
    "square":    ("1024x1024", 1024, 1024),
    "portrait":  ("1024x1792", 1024, 1792),
    "landscape": ("1792x1024", 1792, 1024),
    "naver":     ("1024x1792",  860, 1200),
}

_executor = ThreadPoolExecutor(max_workers=1)

# ─── SDXL 파이프라인 ───────────────────────────────────────────

_SDXL_MODEL  = os.getenv("IMAGE_MODEL_ID", "RunDiffusion/Juggernaut-XL-v9")
_SDXL_STEPS  = int(os.getenv("SDXL_STEPS", "15"))
_SDXL_GUIDANCE = float(os.getenv("SDXL_GUIDANCE", "7.0"))

_sdxl_pipeline = None
_ip_adapter_loaded = False

_NO_OBJECTS_SUFFIX = (
    ", pure empty background surface only, absolutely no food, no drinks, "
    "no products, no objects, no people, no hands, no text, no logos, "
    "no watermarks, no decorations, no props, just the background surface, photorealistic"
)

_SDXL_NEGATIVE = (
    "food, drink, dish, bowl, plate, cup, glass, bottle, utensils, cutlery, "
    "product, object, person, hands, animal, "
    "furniture, chair, table decoration, vase, flower, plant, candle, lamp, "
    "text, watermark, logo, signature, brand, label, "
    "busy background, cluttered, random objects, props, decorative items, "
    "centered subject, hero shot, blurry, low quality, oversaturated, "
    "deformed, distorted, ugly, bad anatomy"
)


def _load_sdxl_pipeline():
    global _sdxl_pipeline, _ip_adapter_loaded

    if _sdxl_pipeline is not None:
        return _sdxl_pipeline

    from diffusers import DPMSolverMultistepScheduler, StableDiffusionXLPipeline

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    logging.info(f"[SDXL] 모델 로딩: {_SDXL_MODEL} ({device})")
    pipe = StableDiffusionXLPipeline.from_pretrained(
        _SDXL_MODEL,
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if dtype == torch.float16 else None,
    )

    # DPM++ 2M Karras — 25 steps에서 최고 품질/속도 균형
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(
        pipe.scheduler.config,
        algorithm_type="dpmsolver++",
        use_karras_sigmas=True,
    )

    pipe = pipe.to(device)

    # IP-Adapter는 attention slicing 전에 로드해야 함
    # (slicing이 먼저 적용되면 SlicedAttnProcessor 충돌 발생)
    ip_weight = os.getenv("IP_ADAPTER_WEIGHT", "ip-adapter_sdxl.safetensors")
    try:
        pipe.load_ip_adapter(
            "h94/IP-Adapter",
            subfolder="sdxl_models",
            weight_name=ip_weight,
        )
        _ip_adapter_loaded = True
        logging.info(f"[SDXL] IP-Adapter 로드 완료: {ip_weight}")
    except Exception as e:
        _ip_adapter_loaded = False
        logging.warning(f"[SDXL] IP-Adapter 로드 실패 (선택사항): {e}")

    if device == "cuda":
        # IP-Adapter 로드 시 attention slicing 생략 (processor 충돌 방지)
        # VAE 최적화만으로 8GB VRAM 내 동작 가능
        if not _ip_adapter_loaded:
            pipe.enable_attention_slicing(1)
        pipe.vae.enable_slicing()
        pipe.vae.enable_tiling()

    _sdxl_pipeline = pipe
    logging.info("[SDXL] 모델 로딩 완료")
    return pipe


def _generate_sdxl_sync(
    prompt: str,
    width: int,
    height: int,
    ip_adapter_image: Image.Image | None,
) -> bytes:
    width  = (width  // 8) * 8
    height = (height // 8) * 8

    pipe = _load_sdxl_pipeline()
    ip_scale = float(os.getenv("IP_ADAPTER_SCALE", "0.40"))

    if _ip_adapter_loaded:
        pipe.set_ip_adapter_scale(ip_scale if ip_adapter_image else 0.0)

    clean_prompt = _trim_prompt(
        "no text, no letters, no words, no watermark, no logo, "
        "no objects, no food, no products, pure background surface only, "
        + prompt
    )

    kwargs: dict = {
        "prompt":          clean_prompt,
        "negative_prompt": _trim_prompt(_SDXL_NEGATIVE),
        "width":           width,
        "height":          height,
        "num_inference_steps": _SDXL_STEPS,
        "guidance_scale":  _SDXL_GUIDANCE,
    }
    if _ip_adapter_loaded:
        # IP-Adapter가 로드된 UNet은 image_embeds 필수
        # ref 없을 때는 중립 이미지로 충족 (scale=0.0이라 실제 영향 없음)
        kwargs["ip_adapter_image"] = ip_adapter_image if ip_adapter_image is not None \
            else Image.new("RGB", (224, 224), (128, 128, 128))

    result = pipe(**kwargs)

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    buf = io.BytesIO()
    result.images[0].save(buf, format="PNG")
    return buf.getvalue()


async def generate_background_image(
    prompt: str,
    size: str = "square",
    ip_adapter_image_bytes: bytes | None = None,
    **kwargs,
) -> bytes:
    """Juggernaut XL + 선택적 IP-Adapter Plus로 배경 이미지 생성.

    ip_adapter_image_bytes가 있으면 레퍼런스 스타일 반영 (scale 0.4).
    없으면 프롬프트만으로 생성 (scale 0.0).
    """
    _, width, height = SIZE_MAP.get(size, SIZE_MAP["square"])
    safe_prompt = prompt + _NO_OBJECTS_SUFFIX

    ip_pil = None
    if ip_adapter_image_bytes:
        ip_pil = Image.open(io.BytesIO(ip_adapter_image_bytes)).convert("RGB")

    loop = asyncio.get_running_loop()
    try:
        image_bytes = await loop.run_in_executor(
            _executor, _generate_sdxl_sync, safe_prompt, width, height, ip_pil
        )
        logging.info("[SDXL] 배경 이미지 생성 성공")
        return image_bytes
    except Exception as e:
        raise RuntimeError(f"배경 이미지 생성 실패: {e}") from e


# ─── SD 1.5 인페인팅 (경계 자연화 전용) ──────────────────────

_SD15_INPAINT_MODEL = "runwayml/stable-diffusion-inpainting"
_inpaint_pipeline = None


def _load_inpaint_pipeline():
    global _inpaint_pipeline
    if _inpaint_pipeline is not None:
        return _inpaint_pipeline

    from diffusers import StableDiffusionInpaintPipeline

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    logging.info(f"[inpaint] 모델 로딩: {_SD15_INPAINT_MODEL} ({device})")
    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        _SD15_INPAINT_MODEL,
        torch_dtype=dtype,
        safety_checker=None,
        requires_safety_checker=False,
        use_safetensors=False,
    )

    pipe = pipe.to(device)
    if device == "cuda":
        pipe.enable_attention_slicing()

    _inpaint_pipeline = pipe
    logging.info("[inpaint] 모델 로딩 완료")
    return pipe


def _inpaint_boundary_sync(
    composited: "Image.Image",
    product_mask: "Image.Image",
    prompt: str,
    boundary_px: int = 32,
    steps: int = 20,
) -> "Image.Image":
    """제품-배경 경계 영역을 SD 1.5 inpainting으로 자연스럽게 보간."""
    import numpy as np
    from PIL import ImageFilter

    pipe = _load_inpaint_pipeline()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    orig_size = composited.size
    inpaint_w = min(orig_size[0], 512)
    inpaint_h = min(orig_size[1], 512)
    inpaint_w = (inpaint_w // 8) * 8
    inpaint_h = (inpaint_h // 8) * 8

    image_in = composited.resize((inpaint_w, inpaint_h), Image.LANCZOS).convert("RGB")
    mask_in  = product_mask.resize((inpaint_w, inpaint_h), Image.LANCZOS)

    ksize = max((boundary_px * inpaint_w // orig_size[0]) | 1, 5)
    dilated = np.array(mask_in.filter(ImageFilter.MaxFilter(ksize)), dtype=np.int32)
    eroded  = np.array(mask_in.filter(ImageFilter.MinFilter(ksize)), dtype=np.int32)
    boundary_arr = np.clip(dilated - eroded, 0, 255).astype(np.uint8)
    inpaint_mask = Image.fromarray(boundary_arr, "L")

    clean_prompt = _trim_prompt("seamless background, natural transition, " + prompt)
    result = pipe(
        prompt=clean_prompt,
        image=image_in,
        mask_image=inpaint_mask,
        num_inference_steps=steps,
        guidance_scale=7.5,
    )

    if device == "cuda":
        torch.cuda.empty_cache()

    inpainted = result.images[0].resize(orig_size, Image.LANCZOS)
    boundary_full = inpaint_mask.resize(orig_size, Image.LANCZOS)
    return Image.composite(inpainted, composited, boundary_full)


async def inpaint_boundary(
    composited_bytes: bytes,
    product_mask: "Image.Image",
    prompt: str,
) -> bytes:
    """비동기 래퍼 — 경계 인페인팅 실행 후 PNG bytes 반환."""
    composited = Image.open(io.BytesIO(composited_bytes)).convert("RGB")
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            _executor, _inpaint_boundary_sync, composited, product_mask, prompt
        )
    except Exception as e:
        logging.warning(f"[inpaint] 경계 인페인팅 실패 (스킵): {e}")
        return composited_bytes

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()


def _trim_prompt(prompt: str, max_tokens: int = 75) -> str:
    """CLIP 77토큰 한계에 맞게 프롬프트를 단어 단위로 트리밍."""
    words = prompt.split(", ")
    result = []
    total = 0
    for word in words:
        token_count = len(word.split()) + 1
        if total + token_count > max_tokens:
            break
        result.append(word)
        total += token_count
    return ", ".join(result)
