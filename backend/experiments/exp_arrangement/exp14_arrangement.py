from __future__ import annotations

import argparse
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from observability import log_langfuse_trace


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRAME_SIZE = 768
DEFAULT_EXP_ID = "exp14"
DEFAULT_INPUT_DIR = PROJECT_ROOT / "generated" / "removed_bg" / "exp_BiRefNet"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp14_from_exp4" / "exp_arrangement"
README_PATH = PROJECT_ROOT.parent / "experiment" / "log" / "log_exp14.md"
PRESET_DIR = PROJECT_ROOT / "assets" / "presets" / "warm"


@dataclass(frozen=True)
class Job:
    job_name: str
    object_name: str
    input_filename: str
    background_filename: str
    output_filename: str
    bg_scale: float
    bg_focus_x: float
    bg_focus_y: float
    anchor_x: float
    anchor_y: float
    target_bbox_h_ratio: float | None = None
    target_bbox_w_ratio: float | None = None
    shadow_opacity: float = 0.24
    shadow_blur: int = 24
    shadow_offset_y: int = 12
    notes: str = ""


JOBS = [
    Job(
        job_name="cake",
        object_name="케이크",
        input_filename="케이크_no_bg.png",
        background_filename="1_dish_bg.png",
        output_filename="cake_on_1_dish_bg.png",
        bg_scale=1.18,
        bg_focus_x=0.50,
        bg_focus_y=0.50,
        anchor_x=0.50,
        anchor_y=0.50,
        target_bbox_h_ratio=0.28,
        target_bbox_w_ratio=0.34,
        shadow_opacity=0.16,
        shadow_blur=18,
        shadow_offset_y=4,
        notes="top-down, centered inside dish",
    ),
    Job(
        job_name="waffle",
        object_name="와플",
        input_filename="와플_no_bg.png",
        background_filename="2_dish_bg.png",
        output_filename="waffle_on_2_dish_bg.png",
        bg_scale=1.34,
        bg_focus_x=0.50,
        bg_focus_y=0.68,
        anchor_x=0.50,
        anchor_y=0.78,
        target_bbox_h_ratio=0.50,
        shadow_opacity=0.26,
        shadow_blur=22,
        shadow_offset_y=10,
        notes="front view, standing on dish, subject about half frame height",
    ),
    Job(
        job_name="toast",
        object_name="토스트",
        input_filename="토스트_no_bg.png",
        background_filename="3_dish_bg.png",
        output_filename="toast_on_3_dish_bg.png",
        bg_scale=1.28,
        bg_focus_x=0.50,
        bg_focus_y=0.60,
        anchor_x=0.50,
        anchor_y=0.74,
        target_bbox_h_ratio=0.42,
        target_bbox_w_ratio=0.42,
        shadow_opacity=0.24,
        shadow_blur=20,
        shadow_offset_y=8,
        notes="front view, auto-fit to dish size",
    ),
    Job(
        job_name="drink",
        object_name="음료",
        input_filename="음료_no_bg.png",
        background_filename="4_bg.webp",
        output_filename="drink_on_4_bg.png",
        bg_scale=1.34,
        bg_focus_x=0.60,
        bg_focus_y=0.62,
        anchor_x=0.73,
        anchor_y=0.76,
        target_bbox_h_ratio=0.68,
        shadow_opacity=0.28,
        shadow_blur=24,
        shadow_offset_y=12,
        notes="front view, lower-right, exp4-sized subject",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exp14 arrangement stage based on exp4 layout logic.")
    parser.add_argument("--exp-id", default=DEFAULT_EXP_ID)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=1401)
    parser.add_argument("--jobs", nargs="*", default=None, help="Subset of jobs: cake waffle toast drink")
    return parser.parse_args()


def prepare_background(image: Image.Image, bg_scale: float, focus_x: float, focus_y: float) -> Image.Image:
    width, height = image.size
    scale = max(FRAME_SIZE / width, FRAME_SIZE / height) * bg_scale
    resized = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
    rw, rh = resized.size
    center_x = int(rw * focus_x)
    center_y = int(rh * focus_y)
    left = max(0, min(rw - FRAME_SIZE, center_x - FRAME_SIZE // 2))
    top = max(0, min(rh - FRAME_SIZE, center_y - FRAME_SIZE // 2))
    return resized.crop((left, top, left + FRAME_SIZE, top + FRAME_SIZE))


def crop_to_bbox(image: Image.Image) -> tuple[Image.Image, tuple[int, int]]:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("alpha channel is empty")
    cropped = image.crop(bbox)
    return cropped, (bbox[2] - bbox[0], bbox[3] - bbox[1])


def transform_object(obj: Image.Image, job: Job) -> Image.Image:
    obj, (bbox_w, bbox_h) = crop_to_bbox(obj)
    scales: list[float] = []
    if job.target_bbox_h_ratio is not None:
        scales.append((FRAME_SIZE * job.target_bbox_h_ratio) / bbox_h)
    if job.target_bbox_w_ratio is not None:
        scales.append((FRAME_SIZE * job.target_bbox_w_ratio) / bbox_w)
    if not scales:
        raise ValueError(f"missing scale rule for {job.job_name}")
    scale = min(scales)
    new_size = (max(1, int(obj.width * scale)), max(1, int(obj.height * scale)))
    return obj.resize(new_size, Image.Resampling.LANCZOS)


def append_readme_log(
    *,
    exp_id: str,
    stage: str,
    job: Job,
    seed: int,
    layout_params: dict[str, float],
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
            f"- 주요 파라미터(배치/광원/그림자/seed): "
            f"center=({layout_params.get('center_x', job.anchor_x):.2f}, {layout_params.get('center_y', job.anchor_y):.2f}), "
            f"scale={layout_params.get('scale', -1.0):.2f}, "
            f"shadow_opacity={job.shadow_opacity}, shadow_blur={job.shadow_blur}, "
            f"shadow_offset_y={job.shadow_offset_y}, seed={seed}\n"
        )
        fp.write(f"- 출력 경로: {output_path}\n")
        fp.write(f"- 관찰 메모(성공/실패 포인트): {'success' if success else 'failure'} | {note} | runtime={runtime_sec:.2f}s\n")


def log_stage(
    *,
    run_id: str,
    stage: str,
    exp_id: str,
    job: Job,
    input_path: Path,
    background_path: Path,
    seed: int,
    layout_params: dict[str, float],
    output_path: Path | None,
    runtime_sec: float,
    error: str | None,
) -> None:
    log_langfuse_trace(
        name=f"image_generator.{exp_id}.{stage}",
        input={
            "run_id": run_id,
            "stage": stage,
            "job_name": job.job_name,
            "input_image_path": str(input_path),
            "background_path": str(background_path),
            "seed": seed,
            "layout_params": layout_params,
            "ic_light_params": None,
        },
        output={
            "output_path": str(output_path) if output_path else None,
            "error": error,
        },
        metadata={"runtime_sec": runtime_sec, "error": error is not None},
        tags=["image_generator", exp_id, stage, job.job_name],
    )


def build_initial_composite(job: Job, input_dir: Path) -> tuple[Image.Image, dict[str, float], Path, Path]:
    input_path = input_dir / job.input_filename
    background_path = PRESET_DIR / job.background_filename
    obj = Image.open(input_path).convert("RGBA")
    bg = prepare_background(
        Image.open(background_path).convert("RGB"),
        job.bg_scale,
        job.bg_focus_x,
        job.bg_focus_y,
    )
    obj = transform_object(obj, job)

    frame = bg.convert("RGBA")
    ow, oh = obj.size
    cx = int(FRAME_SIZE * job.anchor_x)
    cy = int(FRAME_SIZE * job.anchor_y)
    x = max(0, min(FRAME_SIZE - ow, cx - ow // 2))
    y = max(0, min(FRAME_SIZE - oh, cy - oh // 2))

    alpha = obj.getchannel("A")
    shadow = alpha.filter(ImageFilter.GaussianBlur(radius=job.shadow_blur))
    shadow_layer = Image.new("RGBA", obj.size, (0, 0, 0, 0))
    shadow_layer.putalpha(shadow.point(lambda v: int(v * job.shadow_opacity)))
    frame.alpha_composite(shadow_layer, (x, min(FRAME_SIZE - oh, y + job.shadow_offset_y)))
    frame.alpha_composite(obj, (x, y))

    layout_params = {
        "center_x": cx / FRAME_SIZE,
        "center_y": cy / FRAME_SIZE,
        "scale": max(ow, oh) / FRAME_SIZE,
        "anchor_x": job.anchor_x,
        "anchor_y": job.anchor_y,
    }
    return frame.convert("RGB"), layout_params, input_path, background_path


def select_jobs(job_names: list[str] | None) -> list[Job]:
    if not job_names:
        return JOBS
    requested = set(job_names)
    return [job for job in JOBS if job.job_name in requested]


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{args.exp_id}-arrangement-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    failures = 0

    for idx, job in enumerate(select_jobs(args.jobs)):
        start_time = time.time()
        seed = args.seed + idx
        output_path = args.output_dir / job.output_filename
        try:
            composite, layout_params, input_path, background_path = build_initial_composite(job, args.input_dir)
            composite.save(output_path)
            runtime_sec = time.time() - start_time
            log_stage(
                run_id=run_id,
                stage="arrangement",
                exp_id=args.exp_id,
                job=job,
                input_path=input_path,
                background_path=background_path,
                seed=seed,
                layout_params=layout_params,
                output_path=output_path,
                runtime_sec=runtime_sec,
                error=None,
            )
            append_readme_log(
                exp_id=args.exp_id,
                stage="arrangement",
                job=job,
                seed=seed,
                layout_params=layout_params,
                output_path=output_path,
                runtime_sec=runtime_sec,
                success=True,
                note=job.notes,
            )
            print(f"[saved] {output_path}")
        except Exception as exc:
            failures += 1
            runtime_sec = time.time() - start_time
            input_path = args.input_dir / job.input_filename
            background_path = PRESET_DIR / job.background_filename
            error_message = f"{type(exc).__name__}: {exc}"
            log_stage(
                run_id=run_id,
                stage="arrangement",
                exp_id=args.exp_id,
                job=job,
                input_path=input_path,
                background_path=background_path,
                seed=seed,
                layout_params={"anchor_x": job.anchor_x, "anchor_y": job.anchor_y},
                output_path=None,
                runtime_sec=runtime_sec,
                error=error_message,
            )
            append_readme_log(
                exp_id=args.exp_id,
                stage="arrangement",
                job=job,
                seed=seed,
                layout_params={"anchor_x": job.anchor_x, "anchor_y": job.anchor_y},
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
