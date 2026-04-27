from __future__ import annotations

import argparse
import sys
import time
import numpy as np
from pathlib import Path

import gc
import torch
from diffusers import ControlNetModel, StableDiffusionXLControlNetInpaintPipeline
from PIL import Image, ImageFilter, ImageStat, ImageEnhance
from transformers import pipeline as transformers_pipeline, CLIPTokenizer

try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from observability import build_langfuse_media_list, log_langfuse_trace
except ImportError:
    def build_langfuse_media_list(paths): return []
    def log_langfuse_trace(**kwargs): pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp47_depth"
SDXL_INPAINT_MODEL_ID = "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"
CONTROLNET_DEPTH_ID = "diffusers/controlnet-depth-sdxl-1.0"

# IP-Adapter 설정 (조명 및 스타일 전이용)
IP_ADAPTER_REPO = "h94/IP-Adapter"
IP_ADAPTER_SUBFOLDER = "sdxl_models"
IP_ADAPTER_WEIGHT = "ip-adapter_sdxl.bin"

SDXL_BASE_CACHE_ROOT = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--stabilityai--stable-diffusion-xl-base-1.0"
    / "snapshots"
)
FRAME_SIZE = 512

# 배경별 최적 구도 프리셋 (자동 계산용)
# anchor_y는 물체의 '하단'이 위치할 지점을 의미합니다 (접지감 극대화).
LAYOUT_PRESETS = {
    "1_dish_bg": {"object_scale": 0.48, "anchor_x": 0.50, "anchor_y": 0.51, "scale_by": "width", "view_angle": "slightly high angle"},
    "2_dish_bg": {"object_scale": 0.62, "anchor_x": 0.50, "anchor_y": 0.75, "scale_by": "width", "view_angle": "eye-level close-up"},
    "4_bg":      {"object_scale": 0.60, "anchor_x": 0.50, "anchor_y": 0.58, "scale_by": "max", "view_angle": "straight-on shot"},
    "3_bg":      {"object_scale": 0.55, "anchor_x": 0.58, "anchor_y": 0.98, "scale_by": "max", "view_angle": "cinematic low angle"},
}

JOBS = [
    {
        "name": "waffle_on_1_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "1_dish_bg.png",
        "prompt": (
            "A realistic waffle dessert hero shot centered in frame, "
            "strong composition, balanced negative space, grounded on the table plane, "
            "soft natural shadow, premium bakery advertising, photorealistic."
        ),
    },
    {
        "name": "waffle_on_2_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "2_dish_bg.png",
        "prompt": (
            "A realistic waffle dessert filling the lower center of the frame, "
            "tight commercial composition, rich bakery mood, realistic tabletop contact, "
            "photorealistic food poster shot."
        ),
    },
    {
        "name": "drink_on_3_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_음료_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "4_bg.webp",
        "prompt": (
            "A realistic drink hero shot centered in frame, "
            "clean cafe composition, realistic shadow and table grounding, "
            "premium beverage advertising, photorealistic."
        ),
    },
    {
        "name": "pudding_on_4_bg",
        "object": PROJECT_ROOT / "test" / "mask" / "input_푸딩_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "3_bg.webp",
        "prompt": (
            "A realistic cake placed in the lower right of the frame, "
            "intentional asymmetrical composition, grounded on the tabletop plane, "
            "soft directional shadow, premium dessert photography, photorealistic."
        ),
    },
    {
        "name": "cake_on_4_bg",
        "object": PROJECT_ROOT / "test" / "mask" / "input_케이크4_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "3_bg.webp",
        "prompt": (
            "A realistic cake placed in the lower right of the frame, "
            "intentional asymmetrical composition, grounded on the tabletop plane, "
            "soft directional shadow, premium dessert photography, photorealistic."
        ),
    },
    {
        "name": "cake_on_9_bg",
        "object": PROJECT_ROOT / "test" / "mask" / "input_케이크9_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "3_bg.webp",
        "prompt": (
            "A realistic cake placed in the lower right of the frame, "
            "intentional asymmetrical composition, grounded on the tabletop plane, "
            "soft directional shadow, premium dessert photography, photorealistic."
        ),
    },
]

NEGATIVE_PROMPT = (
    "deformed food, extra food, duplicate object, floating object, disconnected shadow, "
    "cartoon, illustration, blurry, low quality, bad crop, distorted perspective, cropped product, cut off"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose cutout food images with improved framing via SDXL Base img2img.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--use-ai", action="store_true", help="AI 모델을 사용하여 자연스러운 후보정(Harmonization) 수행")
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--guidance", type=float, default=6.5)
    parser.add_argument("--strength", type=float, default=0.35, help="합성 강도 (0.35~0.45 권장: 테두리가 부드러워짐)")
    parser.add_argument("--ip-scale", type=float, default=0.5, help="IP-Adapter의 영향력 조절 (0.0 ~ 1.0)")
    parser.add_argument("--control-scale", type=float, default=0.7, help="ControlNet의 영향력 조절 (0.4 ~ 1.0)")
    parser.add_argument("--shadow-darkness", type=float, default=0.4, help="그림자 색상 농도 (0.1~0.5, 높을수록 연함)")
    parser.add_argument("--shadow-opacity", type=float, default=1.0, help="그림자 투명도 배율 (0.1~1.5)")
    return parser.parse_args()


def resolve_base_model_path() -> str:
    if SDXL_BASE_CACHE_ROOT.exists():
        snapshots = sorted(path for path in SDXL_BASE_CACHE_ROOT.iterdir() if path.is_dir())
        if snapshots:
            return str(snapshots[0])
    return SDXL_INPAINT_MODEL_ID


def _apply_ip_adapter_tuple_patch() -> None:
    """
    Monkey-patch ALL diffusers attention processor classes to handle any-depth
    tuple encoder_hidden_states produced by IP-Adapter + ControlNet pipelines.

    - IP-Adapter processors: strip only extra *outer* tuple wrapping; they need
      the inner (text_tensor, ip_embeds) 2-tuple to remain intact.
    - All other processors: strip ALL tuple wrapping so they receive a plain tensor.

    Patching happens at the class level so it covers every future instance,
    including those created by load_ip_adapter().
    """
    try:
        import diffusers.models.attention_processor as ap

        def _make_patched(orig_fn: callable, is_ip_cls: bool) -> callable:
            def patched_call(self, attn, hidden_states, encoder_hidden_states=None, **kwargs):
                if encoder_hidden_states is not None:
                    if is_ip_cls:
                        # Unwrap extra outer layers only; keep the innermost 2-tuple intact.
                        while (
                            isinstance(encoder_hidden_states, (tuple, list))
                            and len(encoder_hidden_states) > 0
                            and isinstance(encoder_hidden_states[0], (tuple, list))
                        ):
                            encoder_hidden_states = encoder_hidden_states[0]
                    else:
                        # Non-IP processor: dig down to the raw tensor.
                        while isinstance(encoder_hidden_states, (tuple, list)):
                            if len(encoder_hidden_states) == 0:
                                encoder_hidden_states = None
                                break
                            encoder_hidden_states = encoder_hidden_states[0]
                return orig_fn(self, attn, hidden_states, encoder_hidden_states, **kwargs)
            return patched_call

        patched = []
        for name in dir(ap):
            cls = getattr(ap, name)
            if not (isinstance(cls, type) and "Processor" in name and callable(getattr(cls, "__call__", None))):
                continue
            if getattr(cls, "_tuple_safe_patched", False):
                continue
            cls.__call__ = _make_patched(cls.__call__, "IPAdapter" in name)
            cls._tuple_safe_patched = True
            patched.append(name)

        print(f"[IP-Adapter Fix] Patched {len(patched)} processor classes: {', '.join(patched)}")
    except Exception as exc:
        print(f"[IP-Adapter Fix] WARNING: patch failed: {exc}")


def load_pipeline() -> StableDiffusionXLControlNetInpaintPipeline:
    """배경 보존 및 자연스러운 합성을 위한 SDXL Inpainting 파이프라인을 로드합니다."""
    model_path = resolve_base_model_path()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    print(f"loading controlnet: {CONTROLNET_DEPTH_ID}")
    controlnet = ControlNetModel.from_pretrained(
        CONTROLNET_DEPTH_ID,
        torch_dtype=dtype,
        use_safetensors=True
    )

    print(f"loading inpainting model: {model_path} on {device}")
    pipe = StableDiffusionXLControlNetInpaintPipeline.from_pretrained(
        model_path,
        controlnet=controlnet,
        torch_dtype=dtype,
        variant="fp16" if device == "cuda" else None,
        use_safetensors=True
    )

    # IP-Adapter 로드: 배경의 조명과 색감을 객체에 투영하기 위함
    print(f"Loading IP-Adapter from {IP_ADAPTER_REPO}...")
    pipe.load_ip_adapter(
        IP_ADAPTER_REPO,
        subfolder=IP_ADAPTER_SUBFOLDER,
        weight_name=IP_ADAPTER_WEIGHT,
    )

    # load_ip_adapter() 호출 후 모든 프로세서 클래스를 패치한다.
    # 파일 패치는 캐시/버전 문제로 불안정하므로, 런타임 monkey-patch로 대체.
    _apply_ip_adapter_tuple_patch()

    if device == "cuda":
        try:
            pipe.enable_xformers_memory_efficient_attention()
            print("[Pipeline] xformers memory efficient attention enabled")
        except Exception as xe:
            print(f"[Pipeline] xformers unavailable, falling back to default attention: {xe}")
        pipe.enable_vae_slicing()
        pipe.enable_vae_tiling()
        # sequential offload: 레이어 단위로 VRAM ↔ RAM 이동 → model_cpu_offload 대비 RAM 사용량 대폭 감소
        pipe.enable_sequential_cpu_offload()

    # Depth 추정 모델은 CPU에서 실행하여 VRAM 충돌 방지
    print("Loading depth estimator (CPU)...")
    pipe.depth_estimator = transformers_pipeline(
        "depth-estimation", model="Intel/dpt-hybrid-midas", device="cpu"
    )

    # CLIP 토크나이저: 프롬프트 길이 제한용 (SDXL 두 인코더 모두 77 토큰 한계)
    pipe._clip_tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-large-patch14")
    return pipe


def clip_truncate(text: str, tokenizer: CLIPTokenizer, max_tokens: int = 60) -> str:
    """CLIP 토크나이저 기준으로 텍스트를 max_tokens 이하로 자릅니다."""
    ids = tokenizer.encode(text, add_special_tokens=False)
    if len(ids) <= max_tokens:
        return text
    return tokenizer.decode(ids[:max_tokens], skip_special_tokens=True)


def prepare_background(image: Image.Image) -> Image.Image:
    """배경의 비율을 유지하며 잘림이나 패딩 없이 리사이즈합니다."""
    w, h = image.size
    # 8의 배수를 유지하면서 FRAME_SIZE에 가장 가깝게 스케일링
    scale = FRAME_SIZE / max(w, h)
    new_w = int(round(w * scale / 8) * 8)
    new_h = int(round(h * scale / 8) * 8)
    
    return image.resize((new_w, new_h), Image.Resampling.LANCZOS)


def resolve_existing_path(path: Path) -> Path:
    if path.exists():
        return path
    nested_candidate = path.parent / "exp1_rembg" / path.name
    if nested_candidate.exists():
        return nested_candidate
    raise FileNotFoundError(path)


def crop_to_bbox(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        # 경계선이 너무 타이트하게 잘려 안티앨리어싱이 깨지는 것을 방지하기 위해 2px 여백 추가
        left, top, right, bottom = bbox
        padding = 2
        bbox = (max(0, left - padding), max(0, top - padding), 
                min(image.width, right + padding), min(image.height, bottom + padding))
        return image.crop(bbox)
    return image


def fit_object(obj: Image.Image, frame_dim: tuple[int, int], object_scale: float, scale_by: str = "max") -> Image.Image:
    fw, fh = frame_dim
    ow, oh = obj.size
    if scale_by == "width":
        ratio = (fw * object_scale) / ow
    elif scale_by == "height":
        ratio = (fh * object_scale) / oh
    else:
        # 배경의 짧은 축을 기준으로 물체가 잘리지 않게 조정
        ratio = (min(fw, fh) * object_scale) / max(ow, oh)
        
    return obj.resize((max(1, int(ow * ratio)), max(1, int(oh * ratio))), Image.Resampling.LANCZOS)


def apply_color_match(obj: Image.Image, bg: Image.Image, strength: float = 0.25) -> Image.Image:
    """배경의 평균 색상을 분석하여 제품의 색조를 배경에 맞게 미세 조정합니다."""
    obj_stats = ImageStat.Stat(obj.convert("RGB"))
    bg_stats = ImageStat.Stat(bg.convert("RGB"))
    shift = [(bg_m - obj_m) * strength for bg_m, obj_m in zip(bg_stats.mean, obj_stats.mean)]
    r, g, b, a = obj.split()
    r = r.point(lambda i: max(0, min(255, int(i + shift[0]))))
    g = g.point(lambda i: max(0, min(255, int(i + shift[1]))))
    b = b.point(lambda i: max(0, min(255, int(i + shift[2]))))
    return Image.merge("RGBA", (r, g, b, a))


def apply_noise_match(image: Image.Image, reference: Image.Image, weight: float = 0.7) -> Image.Image:
    """배경의 노이즈(그레인) 분포를 분석하여 이미지 전체의 질감을 통일합니다."""
    # 1. 배경의 고주파 성분(노이즈) 강도 측정
    ref_gray = np.array(reference.convert("L")).astype(np.float32)
    ref_blur = reference.convert("L").filter(ImageFilter.GaussianBlur(radius=1))
    noise_sample = ref_gray - np.array(ref_blur).astype(np.float32)
    sigma = np.std(noise_sample)

    # 2. 분석된 강도에 따라 가우시안 노이즈 생성
    img_arr = np.array(image).astype(np.float32)
    np.random.seed(42) # 결과 재현성 확보
    noise = np.random.normal(0, sigma * weight, img_arr.shape)

    # 3. 노이즈 적용 및 데이터 타입 복구
    noisy_result = np.clip(img_arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy_result)


def apply_beauty_retouch(image: Image.Image, object_mask: Image.Image = None) -> Image.Image:
    """광고 사진처럼 선명도와 하이라이트 글로우를 강화하는 리터칭을 적용합니다."""
    # 1. 제품 영역 내 특정 포인트(토핑 등) 강조 (Selective Masking)
    if object_mask:
        # 이미지에서 채도(Saturation) 채널 추출하여 '생동감 있는 부분' 찾기
        hsv = image.convert("HSV")
        _, s, _ = hsv.split()
        
        # 제품 마스크와 채도 맵을 결합하여 '강조 마스크' 생성 (과일 등 채도 높은 부분 위주)
        saliency_mask = Image.fromarray(
            (np.array(s).astype(float) * (np.array(object_mask).astype(float) / 255.0)).astype(np.uint8)
        ).filter(ImageFilter.GaussianBlur(radius=5))
        
        # 강조용 버전 생성 (채도와 선명도를 대폭 높임)
        vibrant = ImageEnhance.Color(image).enhance(1.2)
        vibrant = ImageEnhance.Sharpness(vibrant).enhance(1.5)
        
        # 강조 마스크를 이용해 원본과 합성
        image = Image.composite(vibrant, image, saliency_mask)

    # 2. 전역 선명도(Sharpness) 강화: 제품의 질감을 바삭하게 살림
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.5)

    # 3. 블룸(Bloom/Glow) 효과 절제: 임계값을 높이고 반경을 줄여 "뽀샤시"함 제거
    bloom_mask = image.convert("L").point(lambda x: 255 if x > 235 else 0).filter(ImageFilter.GaussianBlur(radius=4))
    bloom_layer = image.filter(ImageFilter.GaussianBlur(radius=2))
    image = Image.composite(bloom_layer, image, bloom_mask)

    # 4. 대비 및 채도 미세 조정
    image = ImageEnhance.Contrast(image).enhance(1.05)
    image = ImageEnhance.Color(image).enhance(1.1)
    return image


def apply_light_wrap(obj: Image.Image, bg_patch: Image.Image, mask: Image.Image, radius: int = 5) -> Image.Image:
    """배경의 빛이 물체 테두리에 미세하게 스며드는 효과를 생성합니다."""
    # 1. 물체 테두리 영역 추출 (Rim)
    rim_mask = mask.filter(ImageFilter.MaxFilter(size=3)).convert("L")
    inner_mask = mask.filter(ImageFilter.MinFilter(size=9)).convert("L")
    rim_only = Image.fromarray(np.clip(np.array(rim_mask) - np.array(inner_mask), 0, 255).astype(np.uint8))

    # 2. 배경을 흐리게 하여 빛의 산란 시뮬레이션
    blurred_bg = bg_patch.filter(ImageFilter.GaussianBlur(radius=radius))
    
    # 3. 테두리 부분에만 배경색을 아주 살짝(20% 농도) 섞음
    return Image.composite(Image.blend(obj.convert("RGB"), blurred_bg, 0.15).convert("RGBA"), obj, rim_only)


def build_initial_composite(job: dict[str, object], args: argparse.Namespace) -> tuple[Image.Image, Image.Image, Image.Image, Image.Image]:
    bg_path = resolve_existing_path(Path(job["background"]))
    preset = LAYOUT_PRESETS.get(bg_path.stem, {"object_scale": 0.5, "anchor_x": 0.5, "anchor_y": 0.5, "scale_by": "max"})
    
    bg_img = Image.open(bg_path).convert("RGB")
    
    bg = prepare_background(bg_img)
    fw, fh = bg.size
    
    # 1. 객체 로드 및 초기 테두리 정리 (Halos Removal)
    obj_src = Image.open(resolve_existing_path(Path(job["object"]))).convert("RGBA")
    obj_src = crop_to_bbox(obj_src)

    # [해결] RGB 엣지 확장: 알파 채널 수축 전 RGB 색상을 바깥으로 밀어내어 검은 테두리 원인 제거
    rgb = obj_src.convert("RGB")
    # 아주 미세한 블러 후 원래 알파와 합성하면 테두리 색상이 안쪽 색상으로 채워집니다.
    edge_fix = rgb.filter(ImageFilter.MaxFilter(size=3))
    obj_src = Image.merge("RGBA", (*edge_fix.split(), obj_src.getchannel("A")))

    # 테두리 검은 잔해 제거를 위해 수축 강도 유지
    alpha_clean = obj_src.getchannel("A").filter(ImageFilter.MinFilter(size=5)) 
    obj_src.putalpha(alpha_clean)

    scale = float(job.get("object_scale", preset["object_scale"]))
    obj = fit_object(
        obj_src,
        (fw, fh),
        scale,
        scale_by=preset.get("scale_by", "max")
    )
    
    ow, oh = obj.size
    ax = float(job.get("anchor_x", preset["anchor_x"]))
    ay = float(job.get("anchor_y", preset["anchor_y"]))
    x = max(0, min(fw - ow, int(fw * ax) - ow // 2))
    y = max(0, min(fh - oh, int(fh * ay) - oh // 2))

    # Local Color Matching: 제품이 놓일 위치의 배경 영역(bg_patch) 색상을 분석하여 매칭
    bg_patch = bg.crop((x, y, x + ow, y + oh))
    obj = apply_color_match(obj, bg_patch, strength=0.25)
    
    # Light Wrap: 배경 광원이 테두리에 스며들게 함 (AI 가이드 강화)
    obj = apply_light_wrap(obj, bg_patch, obj.getchannel("A"), radius=max(2, oh // 100))

    # Anti-aliasing: 수축된 경계선을 부드럽게 처리
    aa_alpha = obj.getchannel("A").filter(ImageFilter.GaussianBlur(radius=1.2))
    obj.putalpha(aa_alpha)
    
    # --- 엠비언트 섀도우 로직: 바닥 색상을 반영한 그림자 ---
    bg_stats = ImageStat.Stat(bg_patch)
    avg_bg_rgb = bg_stats.mean[:3]
    # shadow_darkness가 높을수록 배경색에 가까워져 그림자가 연해짐
    shadow_rgb = tuple(int(c * args.shadow_darkness) for c in avg_bg_rgb)

    frame = bg.convert("RGBA")
    alpha = obj.getchannel("A")
    
    shadow_layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    temp_mask_canvas = Image.new("L", frame.size, 0)
    temp_mask_canvas.paste(alpha, (x, y))

    # 이중 그림자 로직
    occlusion_shadow = temp_mask_canvas.filter(ImageFilter.GaussianBlur(radius=1)) # 밀착 그림자 범위 축소
    contact_shadow = temp_mask_canvas.filter(ImageFilter.GaussianBlur(radius=max(2, oh // 60)))
    soft_shadow = temp_mask_canvas.filter(ImageFilter.GaussianBlur(radius=max(20, oh // 15)))
    
    # 추출한 shadow_rgb 적용
    shadow_layer.paste((*shadow_rgb, int(40 * args.shadow_opacity)), (0, max(5, oh // 20)), mask=soft_shadow)
    shadow_layer.paste((*shadow_rgb, int(90 * args.shadow_opacity)), (0, max(2, oh // 40)), mask=contact_shadow)
    # 밀착 그림자의 투명도를 살짝 낮추고 오프셋을 유지하여 테두리 오염 방지
    shadow_layer.paste((*shadow_rgb, int(100 * args.shadow_opacity)), (0, 3), mask=occlusion_shadow)
    
    frame.alpha_composite(shadow_layer)
    frame.alpha_composite(obj, (x, y))

    # --- Rim + Shadow Masking: 제품 바깥 영역만 AI가 수정 ---
    # 제품 내부는 건드리지 않고, 제품 경계 바깥 얇은 테두리 + 그림자 영역만 마스킹
    dilated_rim = temp_mask_canvas.filter(ImageFilter.MaxFilter(size=11))
    # 제품 바깥으로 확장된 영역 - 원본 제품 마스크 = 제품 바깥 테두리만
    rim_area = np.clip(
        np.array(dilated_rim).astype(int) - np.array(temp_mask_canvas).astype(int),
        0, 255
    ).astype(np.uint8)

    # 접지면 및 그림자 영역 (제품 아래로 이동)
    expanded_shadow = temp_mask_canvas.filter(ImageFilter.MaxFilter(size=41))
    shadow_mask_only = Image.new("L", frame.size, 0)
    shadow_mask_only.paste(expanded_shadow, (0, max(20, oh // 6)))

    # 최종 마스크: 바깥 테두리 + 그림자 (제품 내부 픽셀 없음)
    combined_mask = np.maximum(rim_area, np.array(shadow_mask_only))
    final_mask = Image.fromarray(combined_mask.astype(np.uint8))
    final_mask = final_mask.filter(ImageFilter.GaussianBlur(radius=10))

    # 최종 합성 전 미세 보정: 배경과 너무 따로 놀지 않게 전체적인 채도/대비 미세 조정
    final_img = frame.convert("RGB")
    enhancer = ImageEnhance.Color(final_img)
    final_img = enhancer.enhance(1.05) # 채도 아주 살짝 강화
    enhancer = ImageEnhance.Contrast(final_img)
    final_img = enhancer.enhance(1.02) # 대비 아주 살짝 강화

    return final_img, final_mask, bg.convert("RGB"), temp_mask_canvas, obj, (x, y)


def run_job(
    pipe: StableDiffusionXLControlNetInpaintPipeline | None,
    job: dict[str, object],
    output_dir: Path,
    args: argparse.Namespace,
) -> Path:
    image, mask, bg_ref, obj_mask, original_obj, obj_pos = build_initial_composite(job, args)
    
    # --- ControlNet용 가이드 이미지 생성 (Depth Map) ---
    # 객체의 3차원 형태를 추출하여 볼륨감과 거리감을 AI에게 전달
    print(f"Generating depth map for {job['name']}...")
    depth_result = pipe.depth_estimator(image)
    control_image = depth_result["depth"].convert("RGB")

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    if pipe is not None:
        print(f"Refining {job['name']} with AI (Strength: {args.strength}) for Harmony & Generative Fill...")
        
        # 사용자가 입력한 IP-Adapter 스케일 적용
        pipe.set_ip_adapter_scale(args.ip_scale)

        # 배경 프리셋에서 카메라 각도 힌트 추출
        bg_path = resolve_existing_path(Path(job["background"]))
        view_angle = LAYOUT_PRESETS.get(bg_path.stem, {}).get("view_angle", "professional photography angle")

        # CLIP 77 토큰 제한 대응: 고정 suffix(~17 토큰)를 남기고 사용자 프롬프트를 60 토큰 이내로 자름
        tokenizer = getattr(pipe, "_clip_tokenizer", None)
        user_prompt = job.get("prompt", "")
        if tokenizer is not None:
            user_prompt = clip_truncate(user_prompt, tokenizer, max_tokens=50)

        # Harmonization에 집중된 프롬프트: 새로운 생성보다는 '조화'와 '광원 일치'를 강조
        refine_prompt = (
            f"food photography, {user_prompt}. {view_angle}. "
            "natural lighting, realistic shadows, sharp textures, high quality."
        )
        negative_prompt = f"{NEGATIVE_PROMPT}, plastic look, flat lighting, low contrast, dull colors"
        
        # ControlNet과 Inpainting을 결합하여 실행
        image = pipe(
            prompt=refine_prompt,
            negative_prompt=NEGATIVE_PROMPT,
            image=image,
            control_image=control_image,
            mask_image=mask,
            ip_adapter_image=bg_ref,
            controlnet_conditioning_scale=args.control_scale, # 형태 제어 강도
            control_guidance_end=0.85, # 생성 마지막 단계에서 제어를 풀어 자연스러운 블렌딩 유도
            strength=args.strength,
            num_inference_steps=args.steps,
            guidance_scale=args.guidance,
            generator=torch.manual_seed(42),
        ).images[0]

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # AI가 제품 영역을 임의로 바꾸지 않도록 원본 누끼를 그 자리에 다시 붙임
        image_rgba = image.convert("RGBA")
        image_rgba.alpha_composite(original_obj, obj_pos)
        image = image_rgba.convert("RGB")

        # 1. 광고용 뷰티 리터칭 적용 (블룸 효과 축소 버전)
        image = apply_beauty_retouch(image, obj_mask)

        # 2. 후처리: 모든 필터링이 끝난 후 마지막에 노이즈를 입혀 선명도 유지
        image = apply_noise_match(image, bg_ref, weight=0.7)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    # 결과 파일명에 스케일 값을 포함하여 비교를 용이하게 함
    output_path = output_dir / f"{job['name']}_s{args.ip_scale}.png"
    image.save(output_path)
    print(f"saved {output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    start_time = time.time()
    try:
        pipe = load_pipeline() if args.use_ai else None
        outputs = []
        for idx, job in enumerate(JOBS):
            outputs.append(run_job(pipe, job, args.output_dir, args))
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        log_langfuse_trace(
            name="image_generator.merge_with_sdxl_base_composition_v1",
            input={"args": vars(args), "jobs": [{k: str(v) if isinstance(v, Path) else v for k, v in job.items()} for job in JOBS]},
            output={"saved_paths": [str(path) for path in outputs], "output_images": build_langfuse_media_list([str(path) for path in outputs])},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "sdxl", "composition"],
        )
    except Exception as e:
        log_langfuse_trace(
            name="image_generator.merge_with_sdxl_base_composition_v1.error",
            input={"args": vars(args)},
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "sdxl", "composition", "error"],
        )
        raise


if __name__ == "__main__":
    main()
