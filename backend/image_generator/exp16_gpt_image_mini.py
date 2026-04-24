from __future__ import annotations

import base64
import os
import sys
import time
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from observability import log_langfuse_trace


PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_OUTPUT_ROOT = BACKEND_DIR / "generated"
DEFAULT_PRODUCT_SCALE = 0.58
TEXT_SAFE_RATIO = 0.34


def create_client() -> OpenAI:
    load_dotenv(BACKEND_DIR / ".env", override=True)
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")
    return OpenAI(api_key=api_key)


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


def encode_pil_as_data_url(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def extract_generated_image_b64(response) -> str:
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) == "image_generation_call":
            result = getattr(item, "result", None)
            if result:
                return result
    raise RuntimeError("image_generation_call result not found in responses output")


def build_edit_prompt(user_prompt: str, format_type: str) -> str:
    return (
        f"{user_prompt.strip()} "
        "Use the provided image as the exact composition reference. "
        "Keep the isolated subject identity, food/product details, scale, and position unchanged. "
        "Refine the background mood and overall ad quality without moving or duplicating the subject. "
        f"Generate a photorealistic ad image for format {format_type}. "
        "Do not add floating artifacts, duplicate objects, or broken edges."
    )


def size_from_format(format_type: str) -> str:
    normalized = (format_type or "").lower()
    if normalized in {"story", "스토리"}:
        return "1024x1792"
    if normalized in {"웹 배너", "banner"}:
        return "1792x1024"
    return "1024x1024"


def call_responses_image_api(
    client: OpenAI,
    *,
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


def remove_background_rgba(image_path: Path) -> Image.Image:
    try:
        from rembg import remove
    except ImportError as exc:
        raise RuntimeError("rembg is not installed") from exc

    try:
        result = remove(image_path.read_bytes(), alpha_matting=False)
        cutout = Image.open(BytesIO(result)).convert("RGBA")
        return cutout
    except Exception:
        raise


def _compute_subject_position(
    subject_size: tuple[int, int],
    canvas_size: tuple[int, int],
) -> tuple[int, int]:
    subject_w, subject_h = subject_size
    canvas_w, canvas_h = canvas_size
    x = (canvas_w - subject_w) // 2
    safe_center_y = int(canvas_h * ((1.0 - TEXT_SAFE_RATIO) * 0.52))
    y = safe_center_y - subject_h // 2
    max_y = int(canvas_h * (1.0 - TEXT_SAFE_RATIO)) - subject_h
    return x, max(0, min(y, max_y))


def build_initial_composite(
    *,
    user_image_path: Path,
    reference_image_path: Path,
    format_type: str,
) -> Image.Image:
    canvas_size = tuple(int(v) for v in size_from_format(format_type).split("x"))
    background = Image.open(reference_image_path).convert("RGB").resize(canvas_size, Image.LANCZOS)

    subject = remove_background_rgba(user_image_path)
    subject.thumbnail(
        (int(canvas_size[0] * DEFAULT_PRODUCT_SCALE), int(canvas_size[1] * DEFAULT_PRODUCT_SCALE)),
        Image.LANCZOS,
    )

    canvas = background.convert("RGBA")
    position = _compute_subject_position(subject.size, canvas_size)
    canvas.alpha_composite(subject, position)
    return canvas.convert("RGB")


def generate_image_exp16_api(
    *,
    user_image_path: str,
    reference_image_path: str,
    user_prompt: str,
    format_type: str = "피드",
    output_name: str | None = None,
    output_subdir: str | None = None,
    model: str = "gpt-image-1-mini",
) -> dict[str, str]:
    user_path = Path(user_image_path)
    if not user_path.exists():
        raise FileNotFoundError(f"user image not found: {user_path}")

    reference_path = Path(reference_image_path)
    if not reference_path.exists():
        raise FileNotFoundError(f"reference image not found: {reference_path}")

    client = create_client()

    output_dir = DEFAULT_OUTPUT_ROOT if output_subdir is None else DEFAULT_OUTPUT_ROOT / output_subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (output_name or f"exp16_{int(time.time())}.png")
    init_path = output_dir / f"exp16_init_{int(time.time())}.png"

    prompt = build_edit_prompt(user_prompt, format_type)
    start_time = time.time()
    init_image = build_initial_composite(
        user_image_path=user_path,
        reference_image_path=reference_path,
        format_type=format_type,
    )
    init_image.save(init_path)

    result_b64 = call_responses_image_api(
        client=client,
        input_images=[
            encode_pil_as_data_url(init_image),
        ],
        prompt=prompt,
        model=model,
        size=size_from_format(format_type),
    )
    result_image = Image.open(BytesIO(base64.b64decode(result_b64))).convert("RGB")
    result_image.save(output_path)

    log_langfuse_trace(
        name="image_generator.exp16_gpt_image_mini",
        input={
            "user_image_path": str(user_path),
            "reference_image_path": str(reference_path),
            "init_composite_path": str(init_path),
            "format_type": format_type,
            "user_prompt": user_prompt,
            "model": model,
        },
        output={"saved_path": str(output_path)},
        metadata={"duration_sec": time.time() - start_time},
        tags=["image_generator", "exp16", "gpt-image-1-mini"],
    )

    return {
        "path": str(output_path),
        "user_image_path": str(user_path),
        "reference_image_path": str(reference_path),
        "init_composite_path": str(init_path),
        "format_type": format_type,
    }
