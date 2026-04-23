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
from safetensors.torch import load_model
from transformers import CLIPTextModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observability import build_langfuse_media_list, log_langfuse_trace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WARM_ROOT = PROJECT_ROOT / "assets" / "presets" / "warm"
REMOVED_ROOT = PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "exp1_rembg"
OUTPUT_ROOT = PROJECT_ROOT / "generated" / "merged" / "powerpaint_v2_exp1"

POWERPAINT_REPO = Path(os.environ.get("POWERPAINT_REPO", "/tmp/PowerPaint"))
POWERPAINT_ASSETS = Path(
    os.environ.get("POWERPAINT_ASSETS", str(PROJECT_ROOT / "generated" / "_powerpaint_assets"))
)
BASE_MODEL_PATH = Path(os.environ.get("POWERPAINT_BASE_MODEL", "/tmp/brushnet_assets/data/ckpt/realisticVisionV60B1_v51VAE"))

sys.path.insert(0, str(POWERPAINT_REPO))

if not hasattr(huggingface_hub, "cached_download"):
    huggingface_hub.cached_download = huggingface_hub.hf_hub_download

from diffusers import UniPCMultistepScheduler  # noqa: E402
from powerpaint.models.BrushNet_CA import BrushNetModel  # noqa: E402
from powerpaint.models.unet_2d_condition import UNet2DConditionModel  # noqa: E402
from powerpaint.pipelines.pipeline_PowerPaint_Brushnet_CA import (  # noqa: E402
    StableDiffusionPowerPaintBrushNetPipeline,
)
from powerpaint.utils.utils import TokenizerWrapper, add_tokens  # noqa: E402


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
        prompt="waffle dessert plated at the center of a cafe table, photorealistic food photo",
        center_x=0.50,
        center_y=0.58,
        target_h_ratio=0.48,
    ),
    Case(
        name="waffle_on_2_dish_bg.png",
        fg_path=REMOVED_ROOT / "input_와플_no_bg.png",
        bg_path=WARM_ROOT / "2_dish_bg.png",
        prompt="waffle dessert on a plate near the lower center of a cozy cafe table, photorealistic",
        center_x=0.50,
        center_y=0.69,
        target_h_ratio=0.42,
    ),
    Case(
        name="drink_on_3_bg.png",
        fg_path=REMOVED_ROOT / "input_음료_no_bg.png",
        bg_path=WARM_ROOT / "3_bg.webp",
        prompt="iced cafe drink on a table, front-facing eye-level product photo, photorealistic",
        center_x=0.56,
        center_y=0.70,
        target_h_ratio=0.44,
    ),
    Case(
        name="cake_on_4_bg.png",
        fg_path=REMOVED_ROOT / "input_케이크_no_bg.png",
        bg_path=WARM_ROOT / "4_bg.webp",
        prompt="slice of cake on a cafe table at the lower right, photorealistic dessert photography",
        center_x=0.73,
        center_y=0.79,
        target_h_ratio=0.36,
    ),
]


def add_task(prompt: str, negative_prompt: str, task: str = "text-guided") -> tuple[str, str, str, str]:
    if task == "object-removal":
        prompt_a = f"{prompt} empty scene blur P_ctxt"
        prompt_b = f"{prompt} empty scene blur P_ctxt"
        negative_a = f"{negative_prompt} P_obj"
        negative_b = f"{negative_prompt} P_obj"
    elif task == "shape-guided":
        prompt_a = f"{prompt} P_shape"
        prompt_b = f"{prompt} P_ctxt"
        negative_a = f"{negative_prompt} P_shape"
        negative_b = f"{negative_prompt} P_ctxt"
    else:
        prompt_a = f"{prompt} P_obj"
        prompt_b = f"{prompt} P_obj"
        negative_a = f"{negative_prompt} P_obj"
        negative_b = f"{negative_prompt} P_obj"
    return prompt_a, prompt_b, negative_a, negative_b


def load_pipeline() -> StableDiffusionPowerPaintBrushNetPipeline:
    unet = UNet2DConditionModel.from_pretrained(
        BASE_MODEL_PATH,
        subfolder="unet",
        torch_dtype=torch.float16,
    )
    text_encoder_brushnet = CLIPTextModel.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        subfolder="text_encoder",
        torch_dtype=torch.float16,
    )
    brushnet = BrushNetModel.from_unet(unet)
    pipe = StableDiffusionPowerPaintBrushNetPipeline.from_pretrained(
        BASE_MODEL_PATH,
        brushnet=brushnet,
        text_encoder_brushnet=text_encoder_brushnet,
        torch_dtype=torch.float16,
        low_cpu_mem_usage=False,
        safety_checker=None,
    )
    pipe.unet = UNet2DConditionModel.from_pretrained(
        BASE_MODEL_PATH,
        subfolder="unet",
        torch_dtype=torch.float16,
    )
    pipe.tokenizer = TokenizerWrapper(
        from_pretrained=BASE_MODEL_PATH,
        subfolder="tokenizer",
    )
    add_tokens(
        tokenizer=pipe.tokenizer,
        text_encoder=pipe.text_encoder_brushnet,
        placeholder_tokens=["P_ctxt", "P_shape", "P_obj"],
        initialize_tokens=["a", "a", "a"],
        num_vectors_per_token=10,
    )
    load_model(
        pipe.brushnet,
        str(POWERPAINT_ASSETS / "PowerPaint_Brushnet" / "diffusion_pytorch_model.safetensors"),
    )
    pipe.text_encoder_brushnet.load_state_dict(
        torch.load(
            POWERPAINT_ASSETS / "PowerPaint_Brushnet" / "pytorch_model.bin",
            map_location="cpu",
        ),
        strict=False,
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
    ring_outer = cv2.dilate(alpha_bin, np.ones((35, 35), np.uint8), iterations=1)
    ring_inner = cv2.erode(alpha_bin, np.ones((11, 11), np.uint8), iterations=1)
    seam_mask = np.clip(ring_outer - ring_inner, 0, 255)

    shadow = np.zeros_like(seam_mask)
    shadow_center = (cx, min(size - 1, top + int(new_h * 0.88)))
    axes = (max(12, int(new_w * 0.30)), max(8, int(new_h * 0.07)))
    cv2.ellipse(shadow, shadow_center, axes, 0, 0, 360, 255, -1)
    shadow = cv2.GaussianBlur(shadow, (0, 0), sigmaX=9, sigmaY=5)

    mask = np.maximum(seam_mask, shadow)
    init_rgb = comp_np[:, :, :3].copy()
    init_rgb[mask > 0] = 0
    return Image.fromarray(init_rgb), Image.fromarray(np.repeat(mask[:, :, None], 3, axis=2))


def run() -> None:
    start_time = time.time()
    try:
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        pipe = load_pipeline()
        negative = "deformed food, duplicate object, extra plate, blurry, low quality"
        outputs = []

        for i, case in enumerate(CASES, start=1):
            init_image, mask_image = composite(case)
            prompt_a, prompt_b, negative_a, negative_b = add_task(case.prompt, negative, "text-guided")
            image = pipe(
                promptA=prompt_a,
                promptB=prompt_b,
                promptU=case.prompt,
                tradoff=1.0,
                tradoff_nag=1.0,
                image=init_image.convert("RGB"),
                mask=mask_image.convert("RGB"),
                num_inference_steps=18,
                generator=torch.Generator("cuda").manual_seed(2000 + i),
                brushnet_conditioning_scale=1.0,
                negative_promptA=negative_a,
                negative_promptB=negative_b,
                negative_promptU=negative,
                guidance_scale=7.0,
                width=768,
                height=768,
            ).images[0]
            out_path = OUTPUT_ROOT / case.name
            image.save(out_path)
            outputs.append(str(out_path))
            print(f"saved {out_path}")

        log_langfuse_trace(
            name="image_generator.powerpaint_v2_experiment",
            input={"cases": [case.__dict__ for case in CASES], "output_root": str(OUTPUT_ROOT)},
            output={"saved_paths": outputs, "output_images": build_langfuse_media_list(outputs)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "powerpaint"],
        )
    except Exception as e:
        log_langfuse_trace(
            name="image_generator.powerpaint_v2_experiment.error",
            input={"output_root": str(OUTPUT_ROOT)},
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "powerpaint", "error"],
        )
        raise


if __name__ == "__main__":
    run()
