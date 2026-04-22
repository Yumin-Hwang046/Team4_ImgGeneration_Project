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
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp2"
SDXL_BASE_MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"
SDXL_BASE_CACHE_ROOT = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--stabilityai--stable-diffusion-xl-base-1.0"
    / "snapshots"
)

JOBS = [
    {
        "name": "waffle_on_1_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "1_bg.webp",
        "scale": 0.50,
        "offset_y": 0.10,
        "prompt": (
            "A realistic waffle dessert naturally arranged on the cafe table, "
            "preserve the waffle exactly, warm bakery atmosphere, coherent plate contact, "
            "soft natural shadow, premium food photography, photorealistic."
        ),
    },
    {
        "name": "waffle_on_2_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "2_bg.png",
        "scale": 0.44,
        "offset_y": 0.10,
        "prompt": (
            "A realistic waffle dessert naturally placed in the warm bakery scene, "
            "preserve the waffle exactly, cozy cafe styling, grounded on the tabletop, "
            "high-end commercial food photography."
        ),
    },
    {
        "name": "drink_on_3_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_음료_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "3_bg.webp",
        "scale": 0.46,
        "offset_y": 0.08,
        "prompt": (
            "A realistic drink naturally placed in the cafe scene, preserve the drink exactly, "
            "balanced composition, subtle glass shadow, photorealistic beverage advertising."
        ),
    },
    {
        "name": "cake_on_4_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_케이크_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "4_bg.webp",
        "scale": 0.48,
        "offset_y": 0.11,
        "prompt": (
            "A realistic slice of cake naturally placed in the cozy cafe scene, "
            "preserve the cake exactly, clean tabletop composition, soft shadow, "
            "premium dessert photography, photorealistic."
        ),
    },
]

NEGATIVE_PROMPT = (
    "deformed food, extra food, duplicate object, floating object, bad anatomy, "
    "illustration, cartoon, blurry, low quality, cropped, disconnected shadow"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose cutout food images with SDXL Base img2img.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for merged images.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=30,
        help="Diffusion steps.",
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
        default=0.38,
        help="Img2img strength.",
    )
    return parser.parse_args()


def resolve_base_model_path() -> str:
    if SDXL_BASE_CACHE_ROOT.exists():
        snapshots = sorted(path for path in SDXL_BASE_CACHE_ROOT.iterdir() if path.is_dir())
        if snapshots:
            return str(snapshots[0])
    return SDXL_BASE_MODEL_ID


def resize_background(image: Image.Image, target: int = 768) -> Image.Image:
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


def build_initial_composite(
    object_path: Path,
    background_path: Path,
    scale: float,
    offset_y: float,
) -> Image.Image:
    background = resize_background(Image.open(background_path).convert("RGB"))
    obj = Image.open(object_path).convert("RGBA")
    obj = fit_object(obj, background.size, scale)

    bg_w, bg_h = background.size
    obj_w, obj_h = obj.size
    x = (bg_w - obj_w) // 2
    y = int(bg_h * offset_y + (bg_h - obj_h) * 0.35)

    alpha = obj.getchannel("A")
    shadow = alpha.filter(ImageFilter.GaussianBlur(radius=26))
    shadow_layer = Image.new("RGBA", obj.size, (0, 0, 0, 0))
    shadow_layer.putalpha(shadow.point(lambda v: int(v * 0.24)))

    composite = background.convert("RGBA")
    composite.alpha_composite(shadow_layer, (x, y + max(14, obj_h // 28)))
    composite.alpha_composite(obj, (x, y))
    return composite.convert("RGB")


def load_pipeline() -> AutoPipelineForImage2Image:
    model_path = resolve_base_model_path()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    load_kwargs = {
        "torch_dtype": dtype,
        "use_safetensors": True,
    }
    if device == "cuda":
        load_kwargs["variant"] = "fp16"

    print(f"loading model: {model_path}")
    pipe = AutoPipelineForImage2Image.from_pretrained(model_path, **load_kwargs)
    pipe.enable_attention_slicing()
    pipe.enable_vae_slicing()
    pipe.enable_vae_tiling()
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
    init_image = build_initial_composite(
        object_path=Path(job["object"]),
        background_path=Path(job["background"]),
        scale=float(job["scale"]),
        offset_y=float(job["offset_y"]),
    )
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
            outputs.append(run_job(
                pipe=pipe,
                job=job,
                output_dir=args.output_dir,
                steps=args.steps,
                guidance=args.guidance,
                strength=args.strength,
                seed=100 + idx,
            ))
        log_langfuse_trace(
            name="image_generator.merge_with_sdxl_base",
            input={"args": vars(args), "jobs": [{k: str(v) if isinstance(v, Path) else v for k, v in job.items()} for job in JOBS]},
            output={"saved_paths": [str(path) for path in outputs], "output_images": build_langfuse_media_list([str(path) for path in outputs])},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "sdxl", "merge"],
        )
    except Exception as e:
        log_langfuse_trace(
            name="image_generator.merge_with_sdxl_base.error",
            input={"args": vars(args)},
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "sdxl", "merge", "error"],
        )
        raise


if __name__ == "__main__":
    main()
