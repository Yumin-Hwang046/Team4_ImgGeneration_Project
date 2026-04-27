from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import torch
from diffusers import AutoPipelineForImage2Image
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observability import build_langfuse_media_list, log_langfuse_trace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp9_sdxl_base"
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
        "name": "waffle_on_1_dish_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "1_dish_bg.png",
        "object_scale": 0.64,
        "anchor_x": 0.50,
        "anchor_y": 0.47,
        "bg_scale": 1.22,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.48,
        "prompt": (
            "A realistic waffle dessert centered on the plate in the middle of the frame, "
            "preserve the waffle exactly, natural centered plating, grounded on the dish surface, "
            "soft natural shadow, premium bakery advertising, photorealistic."
        ),
    },
    {
        "name": "waffle_on_2_dish_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "2_dish_bg.png",
        "object_scale": 0.60,
        "anchor_x": 0.50,
        "anchor_y": 0.78,
        "bg_scale": 1.40,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.68,
        "prompt": (
            "A realistic waffle dessert placed on the lower dish area, preserve the waffle exactly, "
            "slightly smaller than a poster crop, clearly resting on the plate, "
            "rich bakery mood, realistic tabletop contact, photorealistic."
        ),
    },
    {
        "name": "drink_on_3_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_음료_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "3_bg.webp",
        "object_scale": 0.52,
        "anchor_x": 0.50,
        "anchor_y": 0.56,
        "bg_scale": 1.18,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.50,
        "prompt": (
            "A realistic drink shown fully in frame, preserve the drink exactly, "
            "slightly smaller subject so the whole cup is visible, front-facing eye-level beverage shot, "
            "not top-down, natural cafe perspective, premium beverage advertising, photorealistic."
        ),
    },
    {
        "name": "cake_on_4_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_케이크_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "4_bg.webp",
        "object_scale": 0.44,
        "anchor_x": 0.73,
        "anchor_y": 0.76,
        "bg_scale": 1.34,
        "bg_focus_x": 0.60,
        "bg_focus_y": 0.62,
        "prompt": (
            "A realistic cake placed in the lower right of the frame, preserve the cake exactly, "
            "intentional asymmetrical composition, grounded on the tabletop plane, "
            "soft directional shadow, premium dessert photography, photorealistic."
        ),
    },
]

NEGATIVE_PROMPT = (
    "deformed food, extra food, duplicate object, floating object, disconnected shadow, "
    "cartoon, illustration, blurry, low quality, bad crop, distorted perspective, "
    "top-down shot, overhead angle, cropped cup, clipped drink"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose exp9 images via SDXL Base img2img with adjusted dish/drink framing.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--guidance", type=float, default=6.5)
    parser.add_argument("--strength", type=float, default=0.34)
    return parser.parse_args()


def resolve_base_model_path() -> str:
    if SDXL_BASE_CACHE_ROOT.exists():
        snapshots = sorted(path for path in SDXL_BASE_CACHE_ROOT.iterdir() if path.is_dir())
        if snapshots:
            return str(snapshots[0])
    return SDXL_BASE_MODEL_ID


def prepare_background(image: Image.Image, bg_scale: float, focus_x: float, focus_y: float) -> Image.Image:
    width, height = image.size
    scale = max((FRAME_SIZE / width), (FRAME_SIZE / height)) * bg_scale
    resized = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
    rw, rh = resized.size
    center_x = int(rw * focus_x)
    center_y = int(rh * focus_y)
    left = max(0, min(rw - FRAME_SIZE, center_x - FRAME_SIZE // 2))
    top = max(0, min(rh - FRAME_SIZE, center_y - FRAME_SIZE // 2))
    return resized.crop((left, top, left + FRAME_SIZE, top + FRAME_SIZE))


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


def build_initial_composite(job: dict[str, object]) -> Image.Image:
    bg = prepare_background(
        Image.open(resolve_existing_path(Path(job["background"]))).convert("RGB"),
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

    frame = bg.convert("RGBA")
    ow, oh = obj.size
    cx = int(FRAME_SIZE * float(job["anchor_x"]))
    cy = int(FRAME_SIZE * float(job["anchor_y"]))
    x = max(0, min(FRAME_SIZE - ow, cx - ow // 2))
    y = max(0, min(FRAME_SIZE - oh, cy - oh // 2))

    alpha = obj.getchannel("A")
    shadow = alpha.filter(ImageFilter.GaussianBlur(radius=max(18, oh // 18)))
    shadow_layer = Image.new("RGBA", obj.size, (0, 0, 0, 0))
    shadow_layer.putalpha(shadow.point(lambda v: int(v * 0.25)))
    frame.alpha_composite(shadow_layer, (x, min(FRAME_SIZE - oh, y + max(10, oh // 20))))
    frame.alpha_composite(obj, (x, y))
    return frame.convert("RGB")


def load_pipeline() -> AutoPipelineForImage2Image:
    model_path = resolve_base_model_path()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    kwargs = {"torch_dtype": dtype, "use_safetensors": True}
    if device == "cuda":
        kwargs["variant"] = "fp16"

    print(f"loading model: {model_path}")
    pipe = AutoPipelineForImage2Image.from_pretrained(model_path, **kwargs)
    pipe.enable_attention_slicing()
    if hasattr(pipe, "vae"):
        pipe.vae.enable_slicing()
        pipe.vae.enable_tiling()
    if device == "cuda":
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)
    return pipe


def run_job(
    pipe: AutoPipelineForImage2Image,
    job: dict[str, object],
    output_dir: Path,
    steps: int,
    guidance: float,
    strength: float,
    seed: int,
) -> Path:
    init_image = build_initial_composite(job)
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    device = pipe._execution_device.type if hasattr(pipe, "_execution_device") else "cpu"
    generator = torch.Generator(device=device).manual_seed(seed)
    image = pipe(
        prompt=str(job["prompt"]),
        negative_prompt=NEGATIVE_PROMPT,
        image=init_image,
        strength=strength,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=generator,
    ).images[0]
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{job['name']}.png"
    image.save(output_path)
    print(f"saved {output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    start_time = time.time()
    try:
        pipe = load_pipeline()
        outputs = []
        for idx, job in enumerate(JOBS):
            outputs.append(run_job(pipe, job, args.output_dir, args.steps, args.guidance, args.strength, 500 + idx))
        log_langfuse_trace(
            name="image_generator.exp9_sdxl_base",
            input={
                "output_dir": str(args.output_dir),
                "steps": args.steps,
                "guidance": args.guidance,
                "strength": args.strength,
                "jobs": [{k: str(v) if isinstance(v, Path) else v for k, v in job.items()} for job in JOBS],
            },
            output={"saved_paths": [str(path) for path in outputs], "output_images": build_langfuse_media_list([str(path) for path in outputs])},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "exp9", "sdxl"],
        )
    except Exception as e:
        log_langfuse_trace(
            name="image_generator.exp9_sdxl_base.error",
            input={"output_dir": str(args.output_dir), "steps": args.steps, "guidance": args.guidance, "strength": args.strength},
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "exp9", "sdxl", "error"],
        )
        raise


if __name__ == "__main__":
    main()
