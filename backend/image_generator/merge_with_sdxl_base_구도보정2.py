from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import torch
from diffusers import AutoPipelineForImage2Image
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observability import build_langfuse_media_list, log_langfuse_trace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp7"
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

LAYOUT_PRESETS = {
    "4_bg": {
        "center_x": 0.73,
        "center_y": 0.79,
        "target_bbox_h_ratio": 0.74,
        "rotation_deg": 0,
        "note": "lower right, frame-filling hero scale",
    },
    "3_bg": {
        "center_x": 0.63,
        "center_y": 0.83,
        "target_bbox_h_ratio": 0.62,
        "rotation_deg": 0,
        "note": "lower right, much larger subject scale",
    },
    "3_dish_bg": {
        "center_x": 0.63,
        "center_y": 0.83,
        "target_bbox_h_ratio": 0.62,
        "rotation_deg": 0,
        "note": "lower right, much larger subject scale",
    },
    "2_bg": {
        "center_x": 0.50,
        "center_y": 0.79,
        "target_bbox_h_ratio": 0.50,
        "rotation_deg": 0,
        "note": "lower center, subject occupies about half the frame",
    },
    "2_dish_bg": {
        "center_x": 0.50,
        "center_y": 0.79,
        "target_bbox_h_ratio": 0.50,
        "rotation_deg": 0,
        "note": "lower center, subject occupies about half the frame",
    },
    "1_bg": {
        "center_x": 0.50,
        "center_y": 0.50,
        "target_bbox_w_ratio": 0.50,
        "rotation_deg": 0,
        "note": "centered subject, subject occupies about half the frame",
    },
    "1_dish_bg": {
        "center_x": 0.50,
        "center_y": 0.50,
        "target_bbox_w_ratio": 0.50,
        "rotation_deg": 0,
        "note": "centered subject, subject occupies about half the frame",
    },
}

JOBS = [
    {
        "name": "waffle_on_1_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "1_dish_bg.png",
        "prompt": (
            "Centered hero dessert composition, subject occupies about half of the frame, "
            "balanced composition, realistic contact shadow on table, "
            "preserve the waffle details, premium food photography, photorealistic."
        ),
        "bg_scale": 1.35,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.63,
    },
    {
        "name": "waffle_on_2_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "2_dish_bg.png",
        "prompt": (
            "Hero dessert composition, subject occupies about half of the frame in the lower center, "
            "clean lower-weighted framing with realistic grounding shadow, "
            "preserve the waffle details, realistic grounding shadow, photorealistic."
        ),
        "bg_scale": 1.55,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.74,
    },
    {
        "name": "drink_on_3_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_음료_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "3_dish_bg.png",
        "prompt": (
            "Extreme close-up hero drink, lower-right emphasis, large subject scale, "
            "tight framing, minimal empty table area, preserve drink details, "
            "realistic contact shadow and natural perspective, photorealistic."
        ),
        "bg_scale": 1.45,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.64,
    },
    {
        "name": "cake_on_4_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_케이크_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "4_bg.webp",
        "prompt": (
            "Extreme close-up hero cake, lower-right placement, "
            "subject fills most of frame height with intentional asymmetry, "
            "preserve cake details, strong realistic contact shadow, photorealistic."
        ),
        "bg_scale": 1.42,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.72,
    },
]

NEGATIVE_PROMPT = (
    "deformed food, extra food, duplicate object, floating object, disconnected shadow, "
    "cartoon, illustration, blurry, low quality, distorted perspective, warped plate, bad crop, "
    "tiny subject, wide shot, far camera, too much empty table"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose exp7 images with precise per-background layout presets.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--guidance", type=float, default=4.5)
    parser.add_argument("--strength", type=float, default=0.18)
    return parser.parse_args()



def resolve_base_model_path() -> str:
    if SDXL_BASE_CACHE_ROOT.exists():
        snapshots = sorted(path for path in SDXL_BASE_CACHE_ROOT.iterdir() if path.is_dir())
        if snapshots:
            return str(snapshots[0])
    return SDXL_BASE_MODEL_ID


def alpha_bbox(alpha: Image.Image) -> tuple[int, int, int, int]:
    alpha_np = np.array(alpha)
    ys, xs = np.nonzero(alpha_np > 10)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def crop_to_bbox(image: Image.Image) -> tuple[Image.Image, tuple[int, int]]:
    alpha = image.getchannel("A")
    bbox = alpha_bbox(alpha)
    cropped = image.crop((bbox[0], bbox[1], bbox[2] + 1, bbox[3] + 1))
    return cropped, (bbox[2] - bbox[0] + 1, bbox[3] - bbox[1] + 1)


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


def transform_object(object_path: Path, preset: dict[str, float]) -> Image.Image:
    obj = Image.open(object_path).convert("RGBA")
    obj, (bbox_w, bbox_h) = crop_to_bbox(obj)

    rotation = float(preset.get("rotation_deg", 0))
    if rotation:
        obj = obj.rotate(rotation, resample=Image.Resampling.BICUBIC, expand=True)
        obj, (bbox_w, bbox_h) = crop_to_bbox(obj)

    scale_by_h = None
    scale_by_w = None
    if "target_bbox_h_ratio" in preset:
        scale_by_h = (FRAME_SIZE * float(preset["target_bbox_h_ratio"])) / bbox_h
    if "target_bbox_w_ratio" in preset:
        scale_by_w = (FRAME_SIZE * float(preset["target_bbox_w_ratio"])) / bbox_w

    scale = scale_by_h if scale_by_h is not None else scale_by_w
    if scale_by_h is not None and scale_by_w is not None:
        scale = min(scale_by_h, scale_by_w)

    new_size = (max(1, int(obj.width * scale)), max(1, int(obj.height * scale)))
    return obj.resize(new_size, Image.Resampling.LANCZOS)


def make_shadow(alpha: Image.Image, opacity: float, blur: int) -> Image.Image:
    shadow = alpha.filter(ImageFilter.GaussianBlur(radius=blur))
    return shadow.point(lambda v: int(v * opacity))


def build_initial_composite(job: dict[str, object]) -> tuple[Image.Image, Image.Image, tuple[int, int], int]:
    bg_name = Path(job["background"]).stem
    preset = LAYOUT_PRESETS[bg_name]

    background = prepare_background(
        Image.open(Path(job["background"])).convert("RGB"),
        float(job["bg_scale"]),
        float(job["bg_focus_x"]),
        float(job["bg_focus_y"]),
    )
    obj = transform_object(Path(job["object"]), preset)

    frame = background.convert("RGBA")
    ow, oh = obj.size
    cx = int(FRAME_SIZE * float(preset["center_x"]))
    cy = int(FRAME_SIZE * float(preset["center_y"]))
    x = max(0, min(FRAME_SIZE - ow, cx - ow // 2))
    y = max(0, min(FRAME_SIZE - oh, cy - oh // 2))

    print(
        f"[layout] {job['name']} center=({cx / FRAME_SIZE:.2f}, {cy / FRAME_SIZE:.2f}) "
        f"bbox=({ow / FRAME_SIZE:.2f}w, {oh / FRAME_SIZE:.2f}h) note={preset['note']}"
    )

    alpha = obj.getchannel("A")
    shadow_alpha = make_shadow(alpha, opacity=0.34, blur=max(10, oh // 28))
    shadow_layer = Image.new("RGBA", obj.size, (0, 0, 0, 0))
    shadow_layer.putalpha(shadow_alpha)
    shadow_y = min(FRAME_SIZE - oh, y + max(6, oh // 30))

    frame.alpha_composite(shadow_layer, (x, shadow_y))
    frame.alpha_composite(obj, (x, y))
    return frame.convert("RGB"), obj, (x, y), shadow_y



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


def lock_subject_on_result(result: Image.Image, obj: Image.Image, pos: tuple[int, int], shadow_y: int) -> Image.Image:
    x, y = pos
    ow, oh = obj.size
    frame = result.convert("RGBA")

    alpha = obj.getchannel("A")
    shadow_alpha = make_shadow(alpha, opacity=0.38, blur=max(8, oh // 30))
    shadow_layer = Image.new("RGBA", obj.size, (0, 0, 0, 0))
    shadow_layer.putalpha(shadow_alpha)

    frame.alpha_composite(shadow_layer, (x, shadow_y))
    frame.alpha_composite(obj, (x, y))
    return frame.convert("RGB")


def run_job(
    pipe: AutoPipelineForImage2Image,
    job: dict[str, object],
    output_dir: Path,
    steps: int,
    guidance: float,
    strength: float,
    seed: int,
) -> Path:
    init_image, obj, pos, shadow_y = build_initial_composite(job)

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    device = pipe._execution_device.type if hasattr(pipe, "_execution_device") else "cpu"
    generator = torch.Generator(device=device).manual_seed(seed)

    generated = pipe(
        prompt=str(job["prompt"]),
        negative_prompt=NEGATIVE_PROMPT,
        image=init_image,
        strength=strength,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=generator,
    ).images[0]

    # 핵심: 최종 결과 위에 누끼를 다시 덮어써서 크기/위치를 절대 고정
    image = lock_subject_on_result(generated, obj, pos, shadow_y)

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
            outputs.append(run_job(pipe, job, args.output_dir, args.steps, args.guidance, args.strength, 300 + idx))
        log_langfuse_trace(
            name="image_generator.merge_with_sdxl_base_composition_v2",
            input={"args": vars(args), "jobs": [{k: str(v) if isinstance(v, Path) else v for k, v in job.items()} for job in JOBS]},
            output={"saved_paths": [str(path) for path in outputs], "output_images": build_langfuse_media_list([str(path) for path in outputs])},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "sdxl", "composition"],
        )
    except Exception as e:
        log_langfuse_trace(
            name="image_generator.merge_with_sdxl_base_composition_v2.error",
            input={"args": vars(args)},
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "sdxl", "composition", "error"],
        )
        raise


if __name__ == "__main__":
    main()
