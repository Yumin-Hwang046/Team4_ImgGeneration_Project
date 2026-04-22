from __future__ import annotations

import argparse
import base64
import os
import sys
import time
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observability import build_langfuse_media_list, log_langfuse_trace, to_langfuse_media
from image_generator.exp9_sdxl_base import JOBS, build_initial_composite


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp14"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compose exp14 images using gpt-image-1-mini edits with exp9 layout."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default="gpt-image-1-mini")
    parser.add_argument("--size", default="1024x1024")
    return parser.parse_args()


def build_edit_prompt(job: dict[str, object]) -> str:
    return (
        f"{job['prompt']} "
        "Preserve the exact object placement, scale, and composition from the provided image. "
        "Keep the subject grounded on the same surface and maintain a photorealistic ad image look. "
        "Do not move the object to a different area of the frame. "
        "Do not crop away the subject."
    )


def create_client() -> OpenAI:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    load_dotenv(PROJECT_ROOT.parent / ".env", override=True)
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def resolve_existing_path(path: Path) -> Path:
    if path.exists():
        return path
    nested_candidate = path.parent / "exp1_rembg" / path.name
    if nested_candidate.exists():
        return nested_candidate
    return path


def resolve_job_paths(job: dict[str, object]) -> dict[str, object]:
    resolved = dict(job)
    resolved["object"] = resolve_existing_path(Path(job["object"]))
    resolved["background"] = resolve_existing_path(Path(job["background"]))
    return resolved


def encode_png(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def run_job(client: OpenAI, job: dict[str, object], output_dir: Path, model: str, size: str) -> tuple[Path, Path]:
    resolved_job = resolve_job_paths(job)
    init_image = build_initial_composite(resolved_job)
    output_dir.mkdir(parents=True, exist_ok=True)

    init_path = output_dir / f"{job['name']}_init.png"
    init_image.save(init_path)

    image_bytes = encode_png(init_image)
    response = client.images.edit(
        model=model,
        image=("input.png", image_bytes, "image/png"),
        prompt=build_edit_prompt(job),
        size=size,
        response_format="b64_json",
    )

    result_b64 = response.data[0].b64_json
    result_image = Image.open(BytesIO(base64.b64decode(result_b64))).convert("RGB")
    output_path = output_dir / f"{job['name']}.png"
    result_image.save(output_path)
    print(f"saved {output_path}")
    return init_path, output_path


def main() -> None:
    args = parse_args()
    start_time = time.time()
    try:
        client = create_client()
        init_paths: list[str] = []
        output_paths: list[str] = []

        for job in JOBS:
            init_path, output_path = run_job(
                client=client,
                job=job,
                output_dir=args.output_dir,
                model=args.model,
                size=args.size,
            )
            init_paths.append(str(init_path))
            output_paths.append(str(output_path))

        log_langfuse_trace(
            name="image_generator.exp14_gpt_image_mini",
            input={
                "args": vars(args),
                "jobs": [{k: str(v) if isinstance(v, Path) else v for k, v in job.items()} for job in JOBS],
                "init_images": build_langfuse_media_list(init_paths),
            },
            output={
                "saved_paths": output_paths,
                "output_images": build_langfuse_media_list(output_paths),
            },
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "exp14", "gpt-image-1-mini"],
        )
    except Exception as e:
        log_langfuse_trace(
            name="image_generator.exp14_gpt_image_mini.error",
            input={"args": vars(args)},
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "exp14", "gpt-image-1-mini", "error"],
        )
        raise


if __name__ == "__main__":
    main()
