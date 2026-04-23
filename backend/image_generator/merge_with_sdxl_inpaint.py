from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import torch
from diffusers import AutoPipelineForInpainting
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observability import build_langfuse_media_list, log_langfuse_trace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "merged"
LOCAL_INPAINT_MODEL = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--diffusers--stable-diffusion-xl-1.0-inpainting-0.1"
    / "snapshots"
    / "115134f363124c53c7d878647567d04daf26e41e"
)

JOBS = [
    {
        "name": "waffle_on_1_bg",
        "object": PROJECT_ROOT / "generated" / "background_removed" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "1_bg.webp",
        "scale": 0.50,
        "offset_y": 0.10,
        "prompt": (
            "A realistic plated waffle naturally placed in the cafe scene, "
            "keep the waffle shape and details unchanged, create coherent table contact, "
            "soft natural shadow, photorealistic food photography."
        ),
    },
    {
        "name": "waffle_on_2_bg",
        "object": PROJECT_ROOT / "generated" / "background_removed" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "2_bg.png",
        "scale": 0.44,
        "offset_y": 0.10,
        "prompt": (
            "A realistic plated waffle naturally integrated into the warm bakery scene, "
            "preserve the waffle exactly, add subtle contact shadow and atmospheric depth, "
            "photorealistic commercial food shot."
        ),
    },
    {
        "name": "drink_on_3_bg",
        "object": PROJECT_ROOT / "generated" / "background_removed" / "input_음료_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "3_bg.webp",
        "scale": 0.46,
        "offset_y": 0.08,
        "prompt": (
            "A realistic iced drink naturally placed in the cafe scene, "
            "preserve the drink exactly, align the cup with the tabletop, "
            "add realistic contact shadow, photorealistic food advertising."
        ),
    },
    {
        "name": "cake_on_4_bg",
        "object": PROJECT_ROOT / "generated" / "background_removed" / "input_케이크_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "4_bg.webp",
        "scale": 0.48,
        "offset_y": 0.11,
        "prompt": (
            "A realistic cake naturally integrated into the cozy cafe scene, "
            "preserve the cake exactly, realistic plate contact and soft table shadow, "
            "high-end photorealistic dessert photography."
        ),
    },
]

NEGATIVE_PROMPT = (
    "deformed food, duplicated object, extra food, distorted plate, blurry, low quality, "
    "cartoon, illustration, floating object, disconnected shadow"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge cutout food images into backgrounds.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for merged output images.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=26,
        help="Number of diffusion inference steps.",
    )
    parser.add_argument(
        "--guidance",
        type=float,
        default=6.5,
        help="Classifier-free guidance scale.",
    )
    parser.add_argument(
        "--strength",
        type=float,
        default=0.55,
        help="Inpainting strength.",
    )
    return parser.parse_args()


def resize_background(image: Image.Image, target: int = 1024) -> Image.Image:
    width, height = image.size
    scale = target / min(width, height)
    new_size = (int(width * scale), int(height * scale))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def fit_object(obj: Image.Image, background_size: tuple[int, int], scale: float) -> Image.Image:
    bg_w, bg_h = background_size
    obj_w, obj_h = obj.size
    ratio = min((bg_w * scale) / obj_w, (bg_h * scale) / obj_h)
    new_size = (max(1, int(obj_w * ratio)), max(1, int(obj_h * ratio)))
    return obj.resize(new_size, Image.Resampling.LANCZOS)


def make_shadow(alpha: Image.Image, dx: int, dy: int) -> Image.Image:
    shadow = alpha.filter(ImageFilter.GaussianBlur(radius=24))
    layer = Image.new("L", alpha.size, 0)
    layer.paste(shadow, (dx, dy))
    return layer


def alpha_bbox(alpha: Image.Image) -> tuple[int, int, int, int]:
    alpha_np = np.array(alpha)
    ys, xs = np.nonzero(alpha_np > 10)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def build_composite_and_mask(
    object_path: Path,
    background_path: Path,
    scale: float,
    offset_y: float,
) -> tuple[Image.Image, Image.Image]:
    background = resize_background(Image.open(background_path).convert("RGB"))
    obj = Image.open(object_path).convert("RGBA")
    obj = fit_object(obj, background.size, scale)

    bg_w, bg_h = background.size
    obj_w, obj_h = obj.size
    x = (bg_w - obj_w) // 2
    y = int(bg_h * offset_y + (bg_h - obj_h) * 0.35)

    composite = background.copy().convert("RGBA")

    shadow_alpha = make_shadow(obj.getchannel("A"), dx=0, dy=max(16, obj_h // 28))
    shadow_layer = Image.new("RGBA", obj.size, (0, 0, 0, 0))
    shadow_layer.putalpha(shadow_alpha.point(lambda v: int(v * 0.28)))
    composite.alpha_composite(shadow_layer, (x, y))
    composite.alpha_composite(obj, (x, y))

    mask = Image.new("L", background.size, 0)
    alpha_canvas = Image.new("L", background.size, 0)
    alpha_canvas.paste(obj.getchannel("A"), (x, y))
    bbox = alpha_bbox(alpha_canvas)
    ring = alpha_canvas.filter(ImageFilter.MaxFilter(41))
    inner = alpha_canvas.filter(ImageFilter.MaxFilter(9))
    ring_np = np.array(ring, dtype=np.uint8)
    inner_np = np.array(inner, dtype=np.uint8)
    halo_np = np.clip(ring_np - inner_np, 0, 255)
    mask = Image.fromarray(halo_np, mode="L")

    draw = ImageDraw.Draw(mask)
    contact_top = min(bg_h - 1, bbox[3] - max(4, obj_h // 40))
    contact_bottom = min(bg_h - 1, bbox[3] + max(26, obj_h // 16))
    contact_left = max(0, bbox[0] + max(12, obj_w // 8))
    contact_right = min(bg_w - 1, bbox[2] - max(12, obj_w // 8))
    draw.rounded_rectangle(
        (contact_left, contact_top, contact_right, contact_bottom),
        radius=max(18, obj_h // 24),
        fill=255,
    )

    return composite.convert("RGB"), mask.filter(ImageFilter.GaussianBlur(radius=9))


def load_pipeline() -> AutoPipelineForInpainting:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    pipe = AutoPipelineForInpainting.from_pretrained(
        str(LOCAL_INPAINT_MODEL),
        torch_dtype=dtype,
        local_files_only=True,
        variant="fp16" if device == "cuda" else None,
    )
    pipe = pipe.to(device)
    pipe.enable_attention_slicing()
    return pipe


def run_job(
    pipe: AutoPipelineForInpainting,
    job: dict[str, object],
    output_dir: Path,
    steps: int,
    guidance: float,
    strength: float,
) -> Path:
    init_image, mask_image = build_composite_and_mask(
        object_path=Path(job["object"]),
        background_path=Path(job["background"]),
        scale=float(job["scale"]),
        offset_y=float(job["offset_y"]),
    )
    device = pipe._execution_device.type if hasattr(pipe, "_execution_device") else "cpu"
    generator = torch.Generator(device=device).manual_seed(42)
    result = pipe(
        prompt=str(job["prompt"]),
        negative_prompt=NEGATIVE_PROMPT,
        image=init_image,
        mask_image=mask_image,
        num_inference_steps=steps,
        guidance_scale=guidance,
        strength=strength,
        generator=generator,
    ).images[0]
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{job['name']}.png"
    result.save(output_path)
    print(f"saved {output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    start_time = time.time()
    try:
        pipe = load_pipeline()
        outputs = []
        for job in JOBS:
            outputs.append(
                run_job(
                    pipe=pipe,
                    job=job,
                    output_dir=args.output_dir,
                    steps=args.steps,
                    guidance=args.guidance,
                    strength=args.strength,
                )
            )
        log_langfuse_trace(
            name="image_generator.merge_with_sdxl_inpaint",
            input={"args": vars(args), "jobs": [{k: str(v) if isinstance(v, Path) else v for k, v in job.items()} for job in JOBS]},
            output={"saved_paths": [str(path) for path in outputs], "output_images": build_langfuse_media_list([str(path) for path in outputs])},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "sdxl", "inpaint"],
        )
    except Exception as e:
        log_langfuse_trace(
            name="image_generator.merge_with_sdxl_inpaint.error",
            input={"args": vars(args)},
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "sdxl", "inpaint", "error"],
        )
        raise


if __name__ == "__main__":
    main()
