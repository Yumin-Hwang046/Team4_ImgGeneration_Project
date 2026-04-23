from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import huggingface_hub
import numpy as np
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observability import build_langfuse_media_list, log_langfuse_trace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WARM_ROOT = PROJECT_ROOT / "assets" / "presets" / "warm"
REMOVED_ROOT = PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "exp1_rembg"
OUTPUT_ROOT = PROJECT_ROOT / "generated" / "merged" / "exp10_brushnet"

BRUSHNET_REPO = Path(os.environ.get("BRUSHNET_REPO", "/tmp/BrushNet"))
BRUSHNET_ASSETS = Path(os.environ.get("BRUSHNET_ASSETS", "/tmp/brushnet_assets")) / "data" / "ckpt"

sys.path.insert(0, str(BRUSHNET_REPO / "src"))

if not hasattr(huggingface_hub, "cached_download"):
    huggingface_hub.cached_download = huggingface_hub.hf_hub_download

from diffusers import BrushNetModel, StableDiffusionBrushNetPipeline, UniPCMultistepScheduler  # noqa: E402


@dataclass(frozen=True)
class Case:
    name: str
    fg_path: Path
    bg_path: Path
    prompt: str
    center_x: float
    center_y: float
    target_h_ratio: float


CASES = [
    Case(
        name="waffle_on_1_dish_bg.png",
        fg_path=REMOVED_ROOT / "input_와플_no_bg.png",
        bg_path=WARM_ROOT / "1_dish_bg.png",
        prompt="A realistic waffle dessert plated at the center of a cafe table, natural perspective, soft cafe lighting, photorealistic food photography.",
        center_x=0.50,
        center_y=0.58,
        target_h_ratio=0.48,
    ),
    Case(
        name="waffle_on_2_dish_bg.png",
        fg_path=REMOVED_ROOT / "input_와플_no_bg.png",
        bg_path=WARM_ROOT / "2_dish_bg.png",
        prompt="A realistic waffle dessert on a plate near the lower center of a cozy cafe table, photorealistic, warm natural light.",
        center_x=0.50,
        center_y=0.69,
        target_h_ratio=0.42,
    ),
    Case(
        name="drink_on_3_bg.png",
        fg_path=REMOVED_ROOT / "input_음료_no_bg.png",
        bg_path=WARM_ROOT / "3_bg.webp",
        prompt="A realistic iced cafe drink on a table, front-facing eye-level product photo, not top-down, photorealistic, soft daylight.",
        center_x=0.56,
        center_y=0.70,
        target_h_ratio=0.44,
    ),
    Case(
        name="cake_on_4_bg.png",
        fg_path=REMOVED_ROOT / "input_케이크_no_bg.png",
        bg_path=WARM_ROOT / "4_bg.webp",
        prompt="A realistic slice of cake on a cafe table at the lower right, photorealistic dessert photography, natural cafe light.",
        center_x=0.73,
        center_y=0.79,
        target_h_ratio=0.36,
    ),
]


def load_pipeline() -> StableDiffusionBrushNetPipeline:
    brushnet = BrushNetModel.from_pretrained(
        BRUSHNET_ASSETS / "segmentation_mask_brushnet_ckpt",
        torch_dtype=torch.float16,
    )
    pipe = StableDiffusionBrushNetPipeline.from_pretrained(
        BRUSHNET_ASSETS / "realisticVisionV60B1_v51VAE",
        brushnet=brushnet,
        torch_dtype=torch.float16,
        low_cpu_mem_usage=False,
        safety_checker=None,
    )
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.enable_model_cpu_offload()
    return pipe


def alpha_bbox(alpha: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(alpha > 0)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def composite(case: Case, size: int = 768) -> tuple[Image.Image, Image.Image]:
    bg = Image.open(case.bg_path).convert("RGB").resize((size, size), Image.LANCZOS)
    fg = Image.open(case.fg_path).convert("RGBA")

    fg_np = np.array(fg)
    alpha = fg_np[:, :, 3]
    x1, y1, x2, y2 = alpha_bbox(alpha)
    fg_np = fg_np[y1:y2, x1:x2]

    target_h = int(size * case.target_h_ratio)
    scale = target_h / max(1, fg_np.shape[0])
    new_w = max(8, int(fg_np.shape[1] * scale))
    new_h = max(8, int(fg_np.shape[0] * scale))
    fg_img = Image.fromarray(fg_np).resize((new_w, new_h), Image.LANCZOS)

    cx = int(size * case.center_x)
    cy = int(size * case.center_y)
    left = int(cx - new_w / 2)
    top = int(cy - new_h / 2)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(fg_img, (left, top))

    comp = bg.convert("RGBA")
    comp.alpha_composite(canvas)
    comp_np = np.array(comp)

    alpha_full = comp_np[:, :, 3]
    alpha_bin = (alpha_full > 0).astype(np.uint8) * 255
    ring_outer = cv2.dilate(alpha_bin, np.ones((31, 31), np.uint8), iterations=1)
    ring_inner = cv2.erode(alpha_bin, np.ones((11, 11), np.uint8), iterations=1)
    seam_mask = np.clip(ring_outer - ring_inner, 0, 255)

    shadow = np.zeros_like(seam_mask)
    shadow_center = (cx, min(size - 1, top + int(new_h * 0.88)))
    axes = (max(12, int(new_w * 0.30)), max(8, int(new_h * 0.07)))
    cv2.ellipse(shadow, shadow_center, axes, 0, 0, 360, 255, -1)
    shadow = cv2.GaussianBlur(shadow, (0, 0), sigmaX=9, sigmaY=5)

    mask = np.maximum(seam_mask, shadow)
    mask_rgb = np.repeat(mask[:, :, None], 3, axis=2)

    init_rgb = comp_np[:, :, :3].copy()
    init_rgb[mask > 0] = 0
    return Image.fromarray(init_rgb), Image.fromarray(mask_rgb)


def run() -> None:
    start_time = time.time()
    try:
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        pipe = load_pipeline()
        outputs = []

        for i, case in enumerate(CASES, start=1):
            init_image, mask_image = composite(case)
            generator = torch.Generator("cuda").manual_seed(1000 + i)
            image = pipe(
                prompt=case.prompt,
                image=init_image,
                mask=mask_image,
                num_inference_steps=22,
                guidance_scale=6.5,
                brushnet_conditioning_scale=1.0,
                generator=generator,
            ).images[0]
            out_path = OUTPUT_ROOT / case.name
            image.save(out_path)
            outputs.append(str(out_path))
            print(f"saved {out_path}")

        log_langfuse_trace(
            name="image_generator.brushnet_experiment",
            input={"cases": [case.__dict__ for case in CASES], "output_root": str(OUTPUT_ROOT)},
            output={"saved_paths": outputs, "output_images": build_langfuse_media_list(outputs)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "brushnet"],
        )
    except Exception as e:
        log_langfuse_trace(
            name="image_generator.brushnet_experiment.error",
            input={"output_root": str(OUTPUT_ROOT)},
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "brushnet", "error"],
        )
        raise


if __name__ == "__main__":
    run()
