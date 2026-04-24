from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observability import build_langfuse_media_list, log_langfuse_trace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp23"
SDXL_BASE_MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"
SDXL_BASE_CACHE_ROOT = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--stabilityai--stable-diffusion-xl-base-1.0"
    / "snapshots"
)
FRAME_SIZE = 768

# 배경별 최적 구도 프리셋 (자동 계산용)
# anchor_y는 물체의 '하단'이 위치할 지점을 의미합니다 (접지감 극대화).
LAYOUT_PRESETS = {
    "1_dish_bg": {"object_scale": 0.48, "anchor_x": 0.50, "anchor_y": 0.51, "scale_by": "width"},
    "2_dish_bg": {"object_scale": 0.62, "anchor_x": 0.50, "anchor_y": 0.75, "scale_by": "width"},
    "4_bg":      {"object_scale": 0.60, "anchor_x": 0.50, "anchor_y": 0.58, "scale_by": "max"},
    "3_bg":      {"object_scale": 0.55, "anchor_x": 0.58, "anchor_y": 0.98, "scale_by": "max"},
}

JOBS = [
    {
        "name": "waffle_on_1_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "1_dish_bg.png",
        "prompt": (
            "A realistic waffle dessert hero shot centered in frame, preserve the waffle exactly, "
            "strong composition, balanced negative space, grounded on the table plane, "
            "soft natural shadow, premium bakery advertising, photorealistic."
        ),
    },
    {
        "name": "waffle_on_2_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "2_dish_bg.png",
        "prompt": (
            "A realistic waffle dessert filling the lower center of the frame, preserve the waffle exactly, "
            "tight commercial composition, rich bakery mood, realistic tabletop contact, "
            "photorealistic food poster shot."
        ),
    },
    {
        "name": "drink_on_3_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_음료_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "4_bg.webp",
        "prompt": (
            "A realistic drink hero shot centered in frame, preserve the drink exactly, "
            "clean cafe composition, realistic shadow and table grounding, "
            "premium beverage advertising, photorealistic."
        ),
    },
    {
        "name": "pudding_on_4_bg",
        "object": PROJECT_ROOT / "test" / "mask" / "input_푸딩_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "3_bg.webp",
        "prompt": (
            "A realistic cake placed in the lower right of the frame, preserve the cake exactly, "
            "intentional asymmetrical composition, grounded on the tabletop plane, "
            "soft directional shadow, premium dessert photography, photorealistic."
        ),
    },
    {
        "name": "cake_on_4_bg",
        "object": PROJECT_ROOT / "test" / "mask" / "input_케이크4_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "3_bg.webp",
        "prompt": (
            "A realistic cake placed in the lower right of the frame, preserve the cake exactly, "
            "intentional asymmetrical composition, grounded on the tabletop plane, "
            "soft directional shadow, premium dessert photography, photorealistic."
        ),
    },
]

NEGATIVE_PROMPT = (
    "deformed food, extra food, duplicate object, floating object, disconnected shadow, "
    "cartoon, illustration, blurry, low quality, bad crop, distorted perspective"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose cutout food images with improved framing via SDXL Base img2img.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--guidance", type=float, default=6.5)
    parser.add_argument("--strength", type=float, default=0.32)
    return parser.parse_args()


def resolve_base_model_path() -> str:
    if SDXL_BASE_CACHE_ROOT.exists():
        snapshots = sorted(path for path in SDXL_BASE_CACHE_ROOT.iterdir() if path.is_dir())
        if snapshots:
            return str(snapshots[0])
    return SDXL_BASE_MODEL_ID


def prepare_background(image: Image.Image, bg_scale: float, focus_x: float, focus_y: float) -> Image.Image:
    # 원본 비율을 유지하며 리사이즈하여 왜곡을 방지합니다.
    w, h = image.size
    scale = FRAME_SIZE / max(w, h)
    new_w, new_h = int(w * scale), int(h * scale)
    # SDXL은 8의 배수 해상도를 선호하므로 조정합니다.
    new_w, new_h = (new_w // 8) * 8, (new_h // 8) * 8
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
        return image.crop(bbox)
    return image


def fit_object(obj: Image.Image, frame_size: int, object_scale: float, scale_by: str = "max") -> Image.Image:
    ow, oh = obj.size
    if scale_by == "width":
        ratio = (frame_size * object_scale) / ow
    else:
        # 기본값 'max': 물체의 긴 축을 기준으로 스케일 조정
        ratio = min((frame_size * object_scale) / ow, (frame_size * object_scale) / oh)
    return obj.resize((max(1, int(ow * ratio)), max(1, int(oh * ratio))), Image.Resampling.LANCZOS)


def apply_color_match(obj: Image.Image, bg: Image.Image, strength: float = 0.15) -> Image.Image:
    """배경의 평균 색상을 분석하여 제품의 색조를 배경에 맞게 미세 조정합니다."""
    obj_stats = ImageStat.Stat(obj.convert("RGB"))
    bg_stats = ImageStat.Stat(bg.convert("RGB"))
    shift = [(bg_m - obj_m) * strength for bg_m, obj_m in zip(bg_stats.mean, obj_stats.mean)]
    r, g, b, a = obj.split()
    r = r.point(lambda i: max(0, min(255, int(i + shift[0]))))
    g = g.point(lambda i: max(0, min(255, int(i + shift[1]))))
    b = b.point(lambda i: max(0, min(255, int(i + shift[2]))))
    return Image.merge("RGBA", (r, g, b, a))


def build_initial_composite(job: dict[str, object]) -> Image.Image:
    bg_path = resolve_existing_path(Path(job["background"]))
    preset = LAYOUT_PRESETS.get(bg_path.stem, {"object_scale": 0.5, "anchor_x": 0.5, "anchor_y": 0.5, "scale_by": "max"})
    
    bg_img = Image.open(bg_path).convert("RGB")
    
    bg = prepare_background(
        bg_img,
        float(job.get("bg_scale", 1.0)),
        float(job.get("bg_focus_x", 0.5)),
        float(job.get("bg_focus_y", 0.5)),
    )
    obj_raw = Image.open(resolve_existing_path(Path(job["object"]))).convert("RGBA")
    
    scale = float(job.get("object_scale", preset["object_scale"]))
    obj = fit_object(
        crop_to_bbox(obj_raw),
        FRAME_SIZE,
        scale,
        scale_by=preset.get("scale_by", "max")
    )

    # Color Matching: 제품의 색감을 배경의 전반적인 톤에 맞춤 (strength=0.15는 원본을 크게 해치지 않는 수준)
    obj = apply_color_match(obj, bg, strength=0.15)

    # Anti-aliasing: 제품 외곽의 날카로운 경계선을 부드럽게 하기 위해 알파 채널에 미세한 블러 적용
    aa_alpha = obj.getchannel("A").filter(ImageFilter.GaussianBlur(radius=1.2))
    obj.putalpha(aa_alpha)

    frame = bg.convert("RGBA")
    fw, fh = frame.size
    ow, oh = obj.size
    
    ax = float(job.get("anchor_x", preset["anchor_x"]))
    ay = float(job.get("anchor_y", preset["anchor_y"]))

    cx = int(fw * ax)
    cy = int(fh * ay)

    x = max(0, min(fw - ow, cx - ow // 2))
    y = max(0, min(fh - oh, cy - oh // 2)) # 중앙 정렬 기준 복구

    alpha = obj.getchannel("A")
    shadow = alpha.filter(ImageFilter.GaussianBlur(radius=max(18, oh // 18)))
    shadow_layer = Image.new("RGBA", obj.size, (0, 0, 0, 0))
    shadow_layer.putalpha(shadow.point(lambda v: int(v * 0.25)))
    frame.alpha_composite(shadow_layer, (x, min(FRAME_SIZE - oh, y + max(10, oh // 20))))
    frame.alpha_composite(obj, (x, y))
    return frame.convert("RGB")


def run_job(
    job: dict[str, object],
    output_dir: Path,
) -> Path:
    # AI 보정 없이 누끼 이미지를 배경에 그대로 합성한 결과물을 사용합니다.
    image = build_initial_composite(job)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{job['name']}.png"
    image.save(output_path)
    print(f"saved {output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    start_time = time.time()
    try:
        outputs = []
        for idx, job in enumerate(JOBS):
            outputs.append(run_job(job, args.output_dir))
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
