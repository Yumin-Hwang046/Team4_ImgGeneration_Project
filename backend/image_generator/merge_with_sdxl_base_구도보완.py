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
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp3"
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
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "1_bg.webp",
        "object_scale": 0.74,
        "anchor_x": 0.50,
        "anchor_y": 0.53,
        "bg_scale": 1.25,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.52,
        "prompt": (
            "A realistic waffle dessert hero shot centered in frame, preserve the waffle exactly, "
            "strong composition, balanced negative space, grounded on the table plane, "
            "soft natural shadow, premium bakery advertising, photorealistic."
        ),
    },
    {
        "name": "waffle_on_2_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "2_bg.png",
        "object_scale": 0.82,
        "anchor_x": 0.50,
        "anchor_y": 0.78,
        "bg_scale": 1.42,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.68,
        "prompt": (
            "A realistic waffle dessert filling the lower center of the frame, preserve the waffle exactly, "
            "tight commercial composition, rich bakery mood, realistic tabletop contact, "
            "photorealistic food poster shot."
        ),
    },
    {
        "name": "drink_on_3_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_음료_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "3_bg.webp",
        "object_scale": 0.72,
        "anchor_x": 0.50,
        "anchor_y": 0.54,
        "bg_scale": 1.28,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.54,
        "prompt": (
            "A realistic drink hero shot centered in frame, preserve the drink exactly, "
            "clean cafe composition, realistic shadow and table grounding, "
            "premium beverage advertising, photorealistic."
        ),
    },
    {
        "name": "cake_on_4_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_케이크_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "4_bg.webp",
        "object_scale": 0.68,
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
    "cartoon, illustration, blurry, low quality, bad crop, distorted perspective"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose cutout food images with improved framing via SDXL Base img2img.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--guidance", type=float, default=6.5)
    parser.add_argument("--strength", type=float, default=0.36)
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


def fit_object(obj: Image.Image, frame_size: int, object_scale: float) -> Image.Image:
    ow, oh = obj.size
    ratio = min((frame_size * object_scale) / ow, (frame_size * object_scale) / oh)
    return obj.resize((max(1, int(ow * ratio)), max(1, int(oh * ratio))), Image.Resampling.LANCZOS)


def build_initial_composite(job: dict[str, object]) -> Image.Image:
    bg = prepare_background(
        Image.open(Path(job["background"])).convert("RGB"),
        float(job["bg_scale"]),
        float(job["bg_focus_x"]),
        float(job["bg_focus_y"]),
    )
    obj = fit_object(
        Image.open(Path(job["object"])).convert("RGBA"),
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
            outputs.append(run_job(pipe, job, args.output_dir, args.steps, args.guidance, args.strength, 200 + idx))
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
