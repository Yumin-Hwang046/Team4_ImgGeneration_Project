from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observability import build_langfuse_media_list, log_langfuse_trace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp18"
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

JOBS = [
    {
        "name": "waffle_on_1_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "1_dish_bg.png",
        "object_scale": 0.48,
        "anchor_x": 0.50,
        "anchor_y": 0.51,
        "bg_scale": 1.0,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.50,
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
        "object_scale": 0.62,
        "anchor_x": 0.50,
        "anchor_y": 0.75,
        "bg_scale": 1.0,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.50,
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
        "object_scale": 0.60,
        "anchor_x": 0.50,
        "anchor_y": 0.58,
        "bg_scale": 1.0,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.50,
        "prompt": (
            "A realistic drink hero shot centered in frame, preserve the drink exactly, "
            "clean cafe composition, realistic shadow and table grounding, "
            "premium beverage advertising, photorealistic."
        ),
    },
    {
        "name": "cake_on_4_bg",
        "object": PROJECT_ROOT / "test" / "mask" / "input_케이크2_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "3_bg.webp",
        "object_scale": 0.55,
        "anchor_x": 0.58,
        "anchor_y": 0.98,
        "bg_scale": 1.0,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.50,
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


def fit_object(obj: Image.Image, frame_size: int, object_scale: float) -> Image.Image:
    ow, oh = obj.size
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
    bg_img = Image.open(bg_path).convert("RGB")
    
    bg = prepare_background(
        bg_img,
        float(job["bg_scale"]),
        float(job["bg_focus_x"]),
        float(job["bg_focus_y"]),
    )
    obj_raw = Image.open(resolve_existing_path(Path(job["object"]))).convert("RGBA")
    obj = fit_object(
        crop_to_bbox(obj_raw),
        FRAME_SIZE,
        float(job["object_scale"]),
    )

    # Color Matching: 제품의 색감을 배경의 전반적인 톤에 맞춤 (strength=0.15는 원본을 크게 해치지 않는 수준)
    obj = apply_color_match(obj, bg, strength=0.15)

    # Anti-aliasing: 제품 외곽의 날카로운 경계선을 부드럽게 하기 위해 알파 채널에 미세한 블러 적용
    aa_alpha = obj.getchannel("A").filter(ImageFilter.GaussianBlur(radius=1.2))
    obj.putalpha(aa_alpha)

    frame = bg.convert("RGBA")
    fw, fh = frame.size
    ow, oh = obj.size

    # Calculate desired reference point on the frame based on anchor_x, anchor_y
    # anchor_x: horizontal center of the object aligns with fw * anchor_x
    # anchor_y: vertical alignment point on the frame.
    #           If anchor_y >= 0.9, object's bottom aligns with fh * anchor_y.
    #           Otherwise, object's center aligns with fh * anchor_y.
    target_x_on_frame = int(fw * float(job["anchor_x"]))
    target_y_on_frame = int(fh * float(job["anchor_y"]))

    # Calculate object's top-left x coordinate
    x = target_x_on_frame - ow // 2

    # Calculate object's top-left y coordinate
    if float(job["anchor_y"]) >= 0.9:
        y = target_y_on_frame - oh # Align bottom of object
    else:
        y = target_y_on_frame - oh // 2 # Align center of object

    # Clamp x and y to ensure the object stays within the frame boundaries
    x = max(0, min(fw - ow, x))
    y = max(0, min(fh - oh, y))

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
