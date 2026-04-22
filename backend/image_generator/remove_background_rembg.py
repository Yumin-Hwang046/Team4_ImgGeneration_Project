from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import onnxruntime as ort
from PIL import Image
from rembg import new_session, remove

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observability import build_langfuse_media_list, log_langfuse_trace, to_langfuse_media

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove backgrounds from images with rembg."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("backend/test/user_input/cafe"),
        help="Directory containing input images.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backend/generated/background_removed"),
        help="Directory to save transparent PNG outputs.",
    )
    parser.add_argument(
        "--model",
        default="u2net",
        help="rembg session model name. Defaults to the locally cached u2net model.",
    )
    return parser.parse_args()


def resolve_providers() -> list[str]:
    providers = ort.get_available_providers()
    if "CUDAExecutionProvider" in providers:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    if "ROCMExecutionProvider" in providers:
        return ["ROCMExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]


def iter_images(input_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def remove_backgrounds(input_dir: Path, output_dir: Path, model_name: str) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    images = iter_images(input_dir)
    if not images:
        raise FileNotFoundError(f"No input images found in: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    providers = resolve_providers()
    print(f"using providers: {providers}")
    session = new_session(model_name, providers=providers)

    saved_paths: list[Path] = []
    for image_path in images:
        with Image.open(image_path) as image:
            output = remove(image.convert("RGBA"), session=session)

        save_path = output_dir / f"{image_path.stem}_no_bg.png"
        output.save(save_path)
        saved_paths.append(save_path)
        print(f"saved {save_path}")

    return saved_paths


def main() -> None:
    args = parse_args()
    start_time = time.time()
    try:
        saved_paths = remove_backgrounds(args.input_dir, args.output_dir, args.model)
        log_langfuse_trace(
            name="image_generator.remove_background_rembg",
            input={
                "input_dir": str(args.input_dir),
                "output_dir": str(args.output_dir),
                "model": args.model,
                "input_images": build_langfuse_media_list([str(path) for path in iter_images(args.input_dir)]),
            },
            output={
                "saved_paths": [str(path) for path in saved_paths],
                "output_images": build_langfuse_media_list([str(path) for path in saved_paths]),
            },
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "rembg"],
        )
    except Exception as e:
        log_langfuse_trace(
            name="image_generator.remove_background_rembg.error",
            input={
                "input_dir": str(args.input_dir),
                "output_dir": str(args.output_dir),
                "model": args.model,
            },
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "rembg", "error"],
        )
        raise


if __name__ == "__main__":
    main()
