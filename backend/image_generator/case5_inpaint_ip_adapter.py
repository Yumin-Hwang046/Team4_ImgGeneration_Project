import os
import time
from typing import Optional

import torch
from PIL import Image, ImageOps
from diffusers import AutoPipelineForInpainting

from observability import log_langfuse_trace, log_wandb

# SDXL Inpaint 모델
SDXL_INPAINT_ID = os.getenv(
    "SDXL_INPAINT_ID",
    "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
)

# IP-Adapter 설정
IP_ADAPTER_REPO = os.getenv("IP_ADAPTER_REPO", "h94/IP-Adapter")
IP_ADAPTER_SUBFOLDER = os.getenv("IP_ADAPTER_SUBFOLDER", "sdxl_models")
IP_ADAPTER_WEIGHT = os.getenv("IP_ADAPTER_WEIGHT", "ip-adapter_sdxl.bin")

# 경로 설정
GENERATED_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "generated"))
PUBLIC_URL_PREFIX = os.getenv("GENERATED_URL_PREFIX", "/static/generated")

NEGATIVE_PROMPT = "swapped food, altered food, wrong food, extra food"


def get_sdxl_size(format_type: str) -> tuple[int, int]:
    if format_type == "스토리":
        return (1024, 1792)
    elif format_type == "웹 배너":
        return (1792, 1024)
    else:
        return (1024, 1024)


def generate_image_case5_inpaint_ip_adapter(
    user_image_path: str,
    reference_image_path: str,
    mask_image_path: str,
    user_prompt: str,
    format_type: str = "피드",
    ip_adapter_scale: float = 0.6,
    strength: float = 0.35,
    steps: int = 30,
    guidance: float = 7.0,
    mask_invert: bool = False,
    output_name: Optional[str] = None,
    output_subdir: Optional[str] = None,
    seed: Optional[int] = None,
    request_id: Optional[str] = None,
) -> dict:
    """
    Case5: 인페인팅 + IP-Adapter
    - image = 사용자 이미지
    - mask_image = 배경만 흰색(=inpaint 영역), 음식은 검정(=보존)
    - ip_adapter_image = 레퍼런스 이미지(스타일)
    """
    if not os.path.exists(user_image_path):
        raise FileNotFoundError(f"사용자 이미지가 없습니다: {user_image_path}")
    if not os.path.exists(reference_image_path):
        raise FileNotFoundError(f"레퍼런스 이미지가 없습니다: {reference_image_path}")
    if not os.path.exists(mask_image_path):
        raise FileNotFoundError(f"마스크 이미지가 없습니다: {mask_image_path}")

    start_time = time.time()
    width, height = get_sdxl_size(format_type)

    init_image = Image.open(user_image_path).convert("RGB").resize((width, height), Image.BICUBIC)
    ref_image = Image.open(reference_image_path).convert("RGB").resize((width, height), Image.BICUBIC)
    mask_image = Image.open(mask_image_path).convert("L").resize((width, height), Image.BICUBIC)
    if mask_invert:
        mask_image = ImageOps.invert(mask_image)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    pipe = AutoPipelineForInpainting.from_pretrained(
        SDXL_INPAINT_ID,
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if device == "cuda" else None,
    ).to(device)

    pipe.load_ip_adapter(
        IP_ADAPTER_REPO,
        subfolder=IP_ADAPTER_SUBFOLDER,
        weight_name=IP_ADAPTER_WEIGHT,
    )
    pipe.set_ip_adapter_scale(ip_adapter_scale)

    generator = torch.Generator(device=device).manual_seed(seed) if seed else None

    final_prompt = build_case5_prompt(user_prompt)
    image = pipe(
        prompt=final_prompt,
        negative_prompt=NEGATIVE_PROMPT,
        image=init_image,
        mask_image=mask_image,
        ip_adapter_image=ref_image,
        strength=strength,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=generator,
    ).images[0]

    out_dir = GENERATED_ROOT
    if output_subdir:
        out_dir = os.path.join(GENERATED_ROOT, output_subdir)
    os.makedirs(out_dir, exist_ok=True)
    filename = output_name or f"sdxl_case5_inpaint_{int(time.time())}.png"
    out_path = os.path.join(out_dir, filename)
    image.save(out_path)

    url_path = f"{PUBLIC_URL_PREFIX}/{filename}"
    if output_subdir:
        url_path = f"{PUBLIC_URL_PREFIX}/{output_subdir}/{filename}"

    result = {
        "path": out_path,
        "url": url_path,
        "user_image_path": user_image_path,
        "reference_image_path": reference_image_path,
        "mask_image_path": mask_image_path,
    }

    duration = time.time() - start_time
    log_payload = {
        "request_id": request_id,
        "case": "case5",
        "format_type": format_type,
        "width": width,
        "height": height,
        "user_prompt": user_prompt,
        "final_prompt": final_prompt,
        "negative_prompt": NEGATIVE_PROMPT,
        "user_image_path": user_image_path,
        "reference_image_path": reference_image_path,
        "mask_image_path": mask_image_path,
        "ip_adapter_scale": ip_adapter_scale,
        "strength": strength,
        "steps": steps,
        "guidance": guidance,
        "seed": seed,
        "model_id": SDXL_INPAINT_ID,
        "ip_adapter_repo": IP_ADAPTER_REPO,
        "ip_adapter_subfolder": IP_ADAPTER_SUBFOLDER,
        "ip_adapter_weight": IP_ADAPTER_WEIGHT,
        "output_path": out_path,
        "output_url": result["url"],
        "duration_sec": duration,
    }
    log_wandb("case5.pipeline", log_payload)
    log_langfuse_trace(
        name="case5.pipeline",
        input={
            "request_id": request_id,
            "user_prompt": user_prompt,
            "format_type": format_type,
            "user_image_path": user_image_path,
            "reference_image_path": reference_image_path,
            "mask_image_path": mask_image_path,
        },
        output=result,
        metadata=log_payload,
        tags=["pipeline", "case5"],
    )

    return result


def build_case5_prompt(user_prompt: str) -> str:
    base = (
        "Keep the food exactly as in the user image. "
        "Only change the masked background and table setting to match the reference style. "
        "Do not alter the food size, shape, texture, or position. "
        "Photorealistic product photo, studio lighting, sharp focus."
    )
    return f"{base} {user_prompt.strip()}"
