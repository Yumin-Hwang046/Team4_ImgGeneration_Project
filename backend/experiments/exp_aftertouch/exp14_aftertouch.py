from __future__ import annotations

import argparse
import gc
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from image_generator.exp12_ic_light import (
    FRAME_SIZE,
    NEGATIVE_PROMPT,
    build_pipelines,
    encode_prompt_pair,
    numpy2pytorch,
    pytorch2numpy,
    resize_without_crop,
)
from observability import log_langfuse_trace


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXP_ID = "exp14"
DEFAULT_INPUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp14_from_exp4" / "exp_arrangement"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp14_from_exp4" / "exp_aftertouch"
README_PATH = PROJECT_ROOT.parent / "experiment" / "log" / "log_exp14.md"
PRESET_DIR = PROJECT_ROOT / "assets" / "presets" / "warm"
FG_DIR = PROJECT_ROOT / "generated" / "removed_bg" / "exp_BiRefNet"


@dataclass(frozen=True)
class Job:
    job_name: str
    object_name: str
    foreground_filename: str
    background_filename: str
    arrangement_filename: str
    output_filename: str
    prompt: str
    width: int
    height: int
    steps: int
    guidance: float
    highres_scale: float
    highres_denoise: float
    ic_strength: float
    ic_shadow_strength: float
    anchor_x: float
    anchor_y: float
    scale: float


JOBS = [
    Job(
        job_name="cake",
        object_name="케이크",
        foreground_filename="케이크_no_bg.png",
        background_filename="1_dish_bg.png",
        arrangement_filename="cake_on_1_dish_bg.png",
        output_filename="cake_on_1_dish_bg.png",
        prompt="top-down plated cake, preserve exact arrangement and dish-centered placement, realistic cafe light, soft contact shadow, photorealistic",
        width=384,
        height=384,
        steps=16,
        guidance=5.8,
        highres_scale=1.25,
        highres_denoise=0.42,
        ic_strength=0.22,
        ic_shadow_strength=0.22,
        anchor_x=0.50,
        anchor_y=0.50,
        scale=0.34,
    ),
    Job(
        job_name="waffle",
        object_name="와플",
        foreground_filename="와플_no_bg.png",
        background_filename="2_dish_bg.png",
        arrangement_filename="waffle_on_2_dish_bg.png",
        output_filename="waffle_on_2_dish_bg.png",
        prompt="front-view waffle on dish, preserve exact placement and subject height, realistic cafe lighting, stronger contact shadow, photorealistic",
        width=384,
        height=384,
        steps=18,
        guidance=6.0,
        highres_scale=1.25,
        highres_denoise=0.45,
        ic_strength=0.28,
        ic_shadow_strength=0.28,
        anchor_x=0.50,
        anchor_y=0.78,
        scale=0.50,
    ),
    Job(
        job_name="toast",
        object_name="토스트",
        foreground_filename="토스트_no_bg.png",
        background_filename="3_dish_bg.png",
        arrangement_filename="toast_on_3_dish_bg.png",
        output_filename="toast_on_3_dish_bg.png",
        prompt="front-view toast on dish, preserve exact plate fit, no oversize no undersize, realistic light and natural grounding shadow, photorealistic",
        width=384,
        height=384,
        steps=18,
        guidance=6.0,
        highres_scale=1.25,
        highres_denoise=0.45,
        ic_strength=0.26,
        ic_shadow_strength=0.26,
        anchor_x=0.50,
        anchor_y=0.74,
        scale=0.42,
    ),
    Job(
        job_name="drink",
        object_name="음료",
        foreground_filename="음료_no_bg.png",
        background_filename="4_bg.webp",
        arrangement_filename="drink_on_4_bg.png",
        output_filename="drink_on_4_bg.png",
        prompt="front-view drink at lower-right, preserve exp4-like size and exact placement, realistic cafe light, clear table contact shadow, photorealistic",
        width=384,
        height=384,
        steps=18,
        guidance=6.0,
        highres_scale=1.25,
        highres_denoise=0.45,
        ic_strength=0.30,
        ic_shadow_strength=0.30,
        anchor_x=0.73,
        anchor_y=0.76,
        scale=0.68,
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exp14 aftertouch stage with mandatory IC-light.")
    parser.add_argument("--exp-id", default=DEFAULT_EXP_ID)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=2401)
    parser.add_argument("--jobs", nargs="*", default=None, help="Subset of jobs: cake waffle toast drink")
    return parser.parse_args()


def select_jobs(job_names: list[str] | None) -> list[Job]:
    if not job_names:
        return JOBS
    requested = set(job_names)
    return [job for job in JOBS if job.job_name in requested]


def load_foreground_as_rgb(path: Path) -> np.ndarray:
    rgba = np.array(Image.open(path).convert("RGBA"))
    alpha = rgba[..., 3:4].astype(np.float32) / 255.0
    rgb = rgba[..., :3].astype(np.float32)
    neutral = np.full_like(rgb, 127.0)
    merged = neutral + (rgb - neutral) * alpha
    return merged.clip(0, 255).astype(np.uint8)


def append_readme_log(
    *,
    exp_id: str,
    stage: str,
    job: Job,
    seed: int,
    output_path: Path,
    runtime_sec: float,
    success: bool,
    note: str,
) -> None:
    README_PATH.parent.mkdir(parents=True, exist_ok=True)
    with README_PATH.open("a", encoding="utf-8") as fp:
        fp.write(f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {exp_id} | {stage} | {job.job_name}\n")
        fp.write(f"- 매핑 정보: {job.object_name} -> {job.background_filename}\n")
        fp.write(
            f"- 주요 파라미터(배치/광원/그림자/seed): center=({job.anchor_x:.2f}, {job.anchor_y:.2f}), "
            f"scale={job.scale:.2f}, steps={job.steps}, guidance={job.guidance}, "
            f"ic_strength={job.ic_strength}, ic_shadow_strength={job.ic_shadow_strength}, "
            f"highres_scale={job.highres_scale}, highres_denoise={job.highres_denoise}, seed={seed}\n"
        )
        fp.write(f"- 출력 경로: {output_path}\n")
        fp.write(f"- 관찰 메모(성공/실패 포인트): {'success' if success else 'failure'} | {note} | runtime={runtime_sec:.2f}s\n")


def log_stage(
    *,
    run_id: str,
    exp_id: str,
    job: Job,
    arrangement_path: Path,
    foreground_path: Path,
    background_path: Path,
    output_path: Path | None,
    seed: int,
    runtime_sec: float,
    error: str | None,
) -> None:
    log_langfuse_trace(
        name=f"image_generator.{exp_id}.aftertouch",
        input={
            "run_id": run_id,
            "stage": "aftertouch",
            "job_name": job.job_name,
            "input_image_path": str(arrangement_path),
            "background_path": str(background_path),
            "seed": seed,
            "layout_params": {
                "center": [job.anchor_x, job.anchor_y],
                "scale": job.scale,
                "anchor": [job.anchor_x, job.anchor_y],
            },
            "ic_light_params": {
                "strength": job.ic_strength,
                "shadow_strength": job.ic_shadow_strength,
                "steps": job.steps,
                "guidance": job.guidance,
                "highres_scale": job.highres_scale,
                "highres_denoise": job.highres_denoise,
            },
        },
        output={"output_path": str(output_path) if output_path else None, "error": error},
        metadata={"runtime_sec": runtime_sec, "error": error is not None},
        tags=["image_generator", exp_id, "aftertouch", "ic-light", job.job_name],
    )


@torch.inference_mode()
def run_job(
    *,
    job: Job,
    args: argparse.Namespace,
    seed: int,
    device: torch.device,
    tokenizer,
    text_encoder,
    vae,
    i2i_pipe,
) -> Path:
    arrangement_path = args.input_dir / job.arrangement_filename
    foreground_path = FG_DIR / job.foreground_filename
    background_path = PRESET_DIR / job.background_filename

    arrangement_image = Image.open(arrangement_path).convert("RGB")
    foreground = load_foreground_as_rgb(foreground_path)
    background = np.array(Image.open(background_path).convert("RGB"))

    conds, unconds = encode_prompt_pair(
        positive_prompt=f"{job.prompt}, preserve exact arrangement, preserve original silhouette, best quality",
        negative_prompt=NEGATIVE_PROMPT,
        tokenizer=tokenizer,
        text_encoder=text_encoder,
        device=device,
    )

    fg_small = resize_without_crop(foreground, job.width, job.height)
    bg_small = resize_without_crop(background, job.width, job.height)
    concat_conds = numpy2pytorch([fg_small, bg_small], device=vae.device, dtype=vae.dtype)
    concat_conds = vae.encode(concat_conds).latent_dist.mode() * vae.config.scaling_factor
    concat_conds = torch.cat([part[None, ...] for part in concat_conds], dim=1)

    generator = torch.Generator(device=device.type).manual_seed(seed)
    init_small = arrangement_image.resize((job.width, job.height), Image.Resampling.LANCZOS)
    latents = i2i_pipe(
        image=init_small,
        strength=job.ic_strength,
        prompt_embeds=conds,
        negative_prompt_embeds=unconds,
        width=job.width,
        height=job.height,
        num_inference_steps=job.steps,
        num_images_per_prompt=1,
        generator=generator,
        output_type="latent",
        guidance_scale=job.guidance,
        cross_attention_kwargs={"concat_conds": concat_conds},
    ).images.to(vae.dtype) / vae.config.scaling_factor

    upscale_w = int(round(job.width * job.highres_scale / 64.0) * 64)
    upscale_h = int(round(job.height * job.highres_scale / 64.0) * 64)
    preview = vae.decode(latents).sample
    preview_image = Image.fromarray(pytorch2numpy(preview)[0]).resize((upscale_w, upscale_h), Image.Resampling.LANCZOS)

    fg_hr = resize_without_crop(foreground, upscale_w, upscale_h)
    bg_hr = resize_without_crop(background, upscale_w, upscale_h)
    concat_conds = numpy2pytorch([fg_hr, bg_hr], device=vae.device, dtype=vae.dtype)
    concat_conds = vae.encode(concat_conds).latent_dist.mode() * vae.config.scaling_factor
    concat_conds = torch.cat([part[None, ...] for part in concat_conds], dim=1)

    latents = i2i_pipe(
        image=preview_image,
        strength=job.highres_denoise,
        prompt_embeds=conds,
        negative_prompt_embeds=unconds,
        width=upscale_w,
        height=upscale_h,
        num_inference_steps=max(job.steps, int(round(job.steps / job.highres_denoise))),
        num_images_per_prompt=1,
        generator=generator,
        output_type="latent",
        guidance_scale=job.guidance,
        cross_attention_kwargs={"concat_conds": concat_conds},
    ).images.to(vae.dtype) / vae.config.scaling_factor

    result = vae.decode(latents).sample
    image = Image.fromarray(pytorch2numpy(result)[0]).resize((FRAME_SIZE, FRAME_SIZE), Image.Resampling.LANCZOS)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / job.output_filename
    image.save(output_path)

    del foreground, background, fg_small, bg_small, fg_hr, bg_hr, conds, unconds, concat_conds, latents, preview, result
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return output_path


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{args.exp_id}-aftertouch-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    failures = 0

    device, tokenizer, text_encoder, vae, unet, t2i_pipe, i2i_pipe = build_pipelines()
    del unet, t2i_pipe
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    for idx, job in enumerate(select_jobs(args.jobs)):
        start_time = time.time()
        seed = args.seed + idx
        arrangement_path = args.input_dir / job.arrangement_filename
        foreground_path = FG_DIR / job.foreground_filename
        background_path = PRESET_DIR / job.background_filename
        output_path = args.output_dir / job.output_filename
        try:
            saved_path = run_job(
                job=job,
                args=args,
                seed=seed,
                device=device,
                tokenizer=tokenizer,
                text_encoder=text_encoder,
                vae=vae,
                i2i_pipe=i2i_pipe,
            )
            runtime_sec = time.time() - start_time
            log_stage(
                run_id=run_id,
                exp_id=args.exp_id,
                job=job,
                arrangement_path=arrangement_path,
                foreground_path=foreground_path,
                background_path=background_path,
                output_path=saved_path,
                seed=seed,
                runtime_sec=runtime_sec,
                error=None,
            )
            append_readme_log(
                exp_id=args.exp_id,
                stage="aftertouch",
                job=job,
                seed=seed,
                output_path=saved_path,
                runtime_sec=runtime_sec,
                success=True,
                note="IC-light mandatory aftertouch completed",
            )
            print(f"[saved] {saved_path}")
        except Exception as exc:
            failures += 1
            runtime_sec = time.time() - start_time
            error_message = f"{type(exc).__name__}: {exc}"
            log_stage(
                run_id=run_id,
                exp_id=args.exp_id,
                job=job,
                arrangement_path=arrangement_path,
                foreground_path=foreground_path,
                background_path=background_path,
                output_path=None,
                seed=seed,
                runtime_sec=runtime_sec,
                error=error_message,
            )
            append_readme_log(
                exp_id=args.exp_id,
                stage="aftertouch",
                job=job,
                seed=seed,
                output_path=output_path,
                runtime_sec=runtime_sec,
                success=False,
                note=error_message,
            )
            print(f"[error] {job.job_name}: {error_message}")
            traceback.print_exc()

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
