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
from observability import build_langfuse_media_list, log_langfuse_trace
from image_generator.exp9_sdxl_base import JOBS, build_initial_composite


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp16"
WARM_PRESET_MAP = {
    "1": PROJECT_ROOT / "assets" / "presets" / "warm" / "1_dish_bg.png",
    "2": PROJECT_ROOT / "assets" / "presets" / "warm" / "2_dish_bg.png",
    "3": PROJECT_ROOT / "assets" / "presets" / "warm" / "3_dish_bg.png",
    "4": PROJECT_ROOT / "assets" / "presets" / "warm" / "4_bg.webp",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compose exp16 images using gpt-image-1-mini edits with exp9 layout."
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
        "Do not crop away the subject. "
        "Use the provided image as the composition reference."
    )


def create_client() -> OpenAI:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing in backend/.env")
    return OpenAI(api_key=api_key)


def resolve_existing_path(path: Path) -> Path:
    if path.exists():
        return path
    nested_candidate = path.parent / "exp1_rembg" / path.name
    if nested_candidate.exists():
        return nested_candidate
    rembg_candidate = PROJECT_ROOT / "generated" / "removed_bg" / "exp_rembg" / path.name
    if rembg_candidate.exists():
        return rembg_candidate
    rembg_nested_candidate = PROJECT_ROOT / "generated" / "removed_bg" / "exp_rembg" / "exp_rembg" / path.name
    if rembg_nested_candidate.exists():
        return rembg_nested_candidate
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


def encode_file_as_data_url(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        mime = "image/png"
    elif suffix in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif suffix == ".webp":
        mime = "image/webp"
    else:
        mime = "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def extract_generated_image_b64(response) -> str:
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) == "image_generation_call":
            result = getattr(item, "result", None)
            if result:
                return result
    raise RuntimeError("image_generation_call result not found in responses output")


def call_responses_image_api(
    client: OpenAI,
    input_images: list[str],
    prompt: str,
    model: str,
    size: str,
) -> str:
    content = [{"type": "input_text", "text": prompt}]
    content.extend({"type": "input_image", "image_url": image_url} for image_url in input_images)
    response = client.responses.create(
        model="gpt-5-mini",
        input=[
            {
                "role": "user",
                "content": content,
            }
        ],
        tools=[
            {
                "type": "image_generation",
                "model": model,
                "size": size,
            }
        ],
    )
    return extract_generated_image_b64(response)


def run_job(client: OpenAI, job: dict[str, object], output_dir: Path, model: str, size: str) -> tuple[Path, Path]:
    resolved_job = resolve_job_paths(job)
    init_image = build_initial_composite(resolved_job)
    output_dir.mkdir(parents=True, exist_ok=True)

    init_path = output_dir / f"{job['name']}_init.png"
    init_image.save(init_path)

    image_bytes = encode_png(init_image)
    result_b64 = call_responses_image_api(
        client=client,
        input_images=[f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}"],
        prompt=build_edit_prompt(job),
        model=model,
        size=size,
    )
    result_image = Image.open(BytesIO(base64.b64decode(result_b64))).convert("RGB")
    output_path = output_dir / f"{job['name']}.png"
    result_image.save(output_path)
    print(f"saved {output_path}")
    return init_path, output_path


def build_api_prompt(user_prompt: str, warm_choice: str, format_type: str) -> str:
    return (
        f"{user_prompt.strip()} "
        "Use the first image as the user subject and content reference. "
        f"Use the second image as the warm preset reference for choice {warm_choice}. "
        "Keep the subject grounded naturally in the scene and match the warm background mood. "
        f"Generate a photorealistic ad image for format {format_type}. "
        "Do not duplicate the subject. Do not add floating artifacts. Do not add boxy edge artifacts."
    )


def size_from_format(format_type: str) -> str:
    if format_type == "story":
        return "1024x1792"
    if format_type in {"웹 배너", "banner"}:
        return "1792x1024"
    return "1024x1024"


def generate_image_exp16_api(
    *,
    user_image_path: str,
    warm_choice: str,
    user_prompt: str,
    format_type: str = "피드",
    output_name: str | None = None,
    output_subdir: str | None = None,
    model: str = "gpt-image-1-mini",
) -> dict[str, str]:
    if warm_choice not in WARM_PRESET_MAP:
        raise ValueError("warm_choice must be one of 1, 2, 3, 4")

    client = create_client()
    user_path = Path(user_image_path)
    if not user_path.exists():
        raise FileNotFoundError(f"user image not found: {user_path}")

    warm_path = WARM_PRESET_MAP[warm_choice]
    output_dir = DEFAULT_OUTPUT_DIR if output_subdir is None else DEFAULT_OUTPUT_DIR / output_subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (output_name or f"exp16_warm_{warm_choice}_{int(time.time())}.png")

    start_time = time.time()
    result_b64 = call_responses_image_api(
        client=client,
        input_images=[encode_file_as_data_url(user_path), encode_file_as_data_url(warm_path)],
        prompt=build_api_prompt(user_prompt, warm_choice, format_type),
        model=model,
        size=size_from_format(format_type),
    )
    result_image = Image.open(BytesIO(base64.b64decode(result_b64))).convert("RGB")
    result_image.save(output_path)

    log_langfuse_trace(
        name="image_generator.exp16_gpt_image_mini.router",
        input={
            "user_image_path": str(user_path),
            "reference_image_path": str(warm_path),
            "warm_choice": warm_choice,
            "format_type": format_type,
            "user_prompt": user_prompt,
        },
        output={"saved_path": str(output_path)},
        metadata={"duration_sec": time.time() - start_time},
        tags=["image_generator", "exp16", "router", "gpt-image-1-mini"],
    )

    return {
        "path": str(output_path),
        "user_image_path": str(user_path),
        "reference_image_path": str(warm_path),
        "warm_choice": warm_choice,
        "format_type": format_type,
    }


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
            name="image_generator.exp16_gpt_image_mini",
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
            tags=["image_generator", "experiment", "exp16", "gpt-image-1-mini"],
        )
    except Exception as e:
        log_langfuse_trace(
            name="image_generator.exp16_gpt_image_mini.error",
            input={"args": vars(args)},
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "exp16", "gpt-image-1-mini", "error"],
        )
        raise


if __name__ == "__main__":
    main()
