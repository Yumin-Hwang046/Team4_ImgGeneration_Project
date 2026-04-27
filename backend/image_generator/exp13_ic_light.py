from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exp12_ic_light import (
    FRAME_SIZE,
    JOBS,
    NEGATIVE_PROMPT,
    build_pipelines,
    encode_prompt_pair,
    fit_object,
    prepare_background,
    pytorch2numpy,
    resolve_existing_path,
    resize_without_crop,
    numpy2pytorch,
)
from observability import build_langfuse_media_list, log_langfuse_trace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp13"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compose exp13 images with exp9 layout preserved more strongly using IC-Light."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--steps", type=int, default=18)
    parser.add_argument("--guidance", type=float, default=6.0)
    parser.add_argument("--strength", type=float, default=0.72)
    parser.add_argument("--width", type=int, default=384)
    parser.add_argument("--height", type=int, default=384)
    parser.add_argument("--highres-scale", type=float, default=1.25)
    parser.add_argument("--highres-denoise", type=float, default=0.45)
    return parser.parse_args()


def build_condition_images(job: dict[str, object]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    bg = prepare_background(
        Image.open(resolve_existing_path(Path(job["background"]))).convert("RGB"),
        float(job["bg_scale"]),
        float(job["bg_focus_x"]),
        float(job["bg_focus_y"]),
    )
    obj = fit_object(
        Image.open(resolve_existing_path(Path(job["object"]))).convert("RGBA"),
        FRAME_SIZE,
        float(job["object_scale"]),
    )

    ow, oh = obj.size
    cx = int(FRAME_SIZE * float(job["anchor_x"]))
    cy = int(FRAME_SIZE * float(job["anchor_y"]))
    x = max(0, min(FRAME_SIZE - ow, cx - ow // 2))
    y = max(0, min(FRAME_SIZE - oh, cy - oh // 2))

    fg_canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (127, 127, 127, 255))
    fg_canvas.alpha_composite(obj, (x, y))

    init_composite = bg.convert("RGBA")
    init_composite.alpha_composite(obj, (x, y))
    return np.array(fg_canvas.convert("RGB")), np.array(bg), np.array(init_composite)


def run_job(
    *,
    job: dict[str, object],
    output_dir: Path,
    steps: int,
    guidance: float,
    strength: float,
    width: int,
    height: int,
    highres_scale: float,
    highres_denoise: float,
    seed: int,
    device: torch.device,
    tokenizer,
    text_encoder,
    vae,
    unet,
    t2i_pipe,
    i2i_pipe,
) -> Path:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    foreground, background, init_composite = build_condition_images(job)
    conds, unconds = encode_prompt_pair(
        positive_prompt=f"{job['prompt']}, preserve exact object placement and scale, best quality",
        negative_prompt=NEGATIVE_PROMPT,
        tokenizer=tokenizer,
        text_encoder=text_encoder,
        device=device,
    )

    fg_small = resize_without_crop(foreground, width, height)
    bg_small = resize_without_crop(background, width, height)
    concat_conds = numpy2pytorch([fg_small, bg_small], device=vae.device, dtype=vae.dtype)
    concat_conds = vae.encode(concat_conds).latent_dist.mode() * vae.config.scaling_factor
    concat_conds = torch.cat([part[None, ...] for part in concat_conds], dim=1)

    generator = torch.Generator(device=device.type).manual_seed(seed)
    latents = t2i_pipe(
        prompt_embeds=conds,
        negative_prompt_embeds=unconds,
        width=width,
        height=height,
        num_inference_steps=steps,
        num_images_per_prompt=1,
        generator=generator,
        output_type="latent",
        guidance_scale=guidance,
        cross_attention_kwargs={"concat_conds": concat_conds},
    ).images.to(vae.dtype) / vae.config.scaling_factor

    upscale_w = int(round(width * highres_scale / 64.0) * 64)
    upscale_h = int(round(height * highres_scale / 64.0) * 64)
    base_preview = vae.decode(latents).sample
    base_preview_image = Image.fromarray(pytorch2numpy(base_preview)[0]).resize(
        (upscale_w, upscale_h),
        Image.Resampling.LANCZOS,
    )
    fg_hr = resize_without_crop(foreground, upscale_w, upscale_h)
    bg_hr = resize_without_crop(background, upscale_w, upscale_h)
    concat_conds = numpy2pytorch([fg_hr, bg_hr], device=vae.device, dtype=vae.dtype)
    concat_conds = vae.encode(concat_conds).latent_dist.mode() * vae.config.scaling_factor
    concat_conds = torch.cat([part[None, ...] for part in concat_conds], dim=1)

    latents = i2i_pipe(
        image=base_preview_image,
        strength=highres_denoise,
        prompt_embeds=conds,
        negative_prompt_embeds=unconds,
        width=upscale_w,
        height=upscale_h,
        num_inference_steps=max(steps, int(round(steps / highres_denoise))),
        num_images_per_prompt=1,
        generator=generator,
        output_type="latent",
        guidance_scale=guidance,
        cross_attention_kwargs={"concat_conds": concat_conds},
    ).images.to(vae.dtype) / vae.config.scaling_factor

    result = vae.decode(latents).sample
    image = Image.fromarray(pytorch2numpy(result)[0]).resize((FRAME_SIZE, FRAME_SIZE), Image.Resampling.LANCZOS)

    del foreground, background, init_composite, fg_small, bg_small, fg_hr, bg_hr, concat_conds, conds, unconds, latents, result, base_preview
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{job['name']}.png"
    image.save(output_path)
    print(f"saved {output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    start_time = time.time()
    try:
        device, tokenizer, text_encoder, vae, unet, t2i_pipe, i2i_pipe = build_pipelines()
        print(f"device={device}")
        outputs = []
        for idx, job in enumerate(JOBS):
            outputs.append(
                run_job(
                    job=job,
                    output_dir=args.output_dir,
                    steps=args.steps,
                    guidance=args.guidance,
                    strength=args.strength,
                    width=args.width,
                    height=args.height,
                    highres_scale=args.highres_scale,
                    highres_denoise=args.highres_denoise,
                    seed=1300 + idx,
                    device=device,
                    tokenizer=tokenizer,
                    text_encoder=text_encoder,
                    vae=vae,
                    unet=unet,
                    t2i_pipe=t2i_pipe,
                    i2i_pipe=i2i_pipe,
                )
            )
        log_langfuse_trace(
            name="image_generator.exp13_ic_light",
            input={"args": vars(args), "jobs": [{k: str(v) if isinstance(v, Path) else v for k, v in job.items()} for job in JOBS]},
            output={"saved_paths": [str(path) for path in outputs], "output_images": build_langfuse_media_list([str(path) for path in outputs])},
            metadata={"duration_sec": time.time() - start_time, "device": str(device)},
            tags=["image_generator", "experiment", "exp13", "ic-light"],
        )
    except Exception as e:
        log_langfuse_trace(
            name="image_generator.exp13_ic_light.error",
            input={"args": vars(args)},
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "exp13", "ic-light", "error"],
        )
        raise


if __name__ == "__main__":
    main()
