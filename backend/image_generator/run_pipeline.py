import argparse
from pathlib import Path

from inference_base import SDXLBaseGenerator, save_images as save_base_images


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run image generation pipeline")

    parser.add_argument("--prompt", type=str, required=True, help="Main generation prompt")
    parser.add_argument(
        "--negative_prompt",
        type=str,
        default=(
            "egg, mushroom, strange food, mixed dishes, "
            "deformed, unrealistic, weird texture, blurry, low quality"
        ),
        help="Negative prompt",
    )
    parser.add_argument("--output_dir", type=str, default="outputs", help="Output directory")
    parser.add_argument("--num_images_per_prompt", type=int, default=1)
    parser.add_argument("--num_inference_steps", type=int, default=25)
    parser.add_argument("--guidance_scale", type=float, default=7.5)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--width", type=int, default=768)

    # 현재는 안 써도 백엔드에서 넘길 수 있게 자리만 열어둠
    parser.add_argument("--image_path", type=str, default=None, help="Optional source image path")

    return parser


def run_pipeline() -> None:
    parser = build_parser()
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_generator = SDXLBaseGenerator()
    base_images = base_generator.generate(
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        num_images_per_prompt=args.num_images_per_prompt,
        num_inference_steps=args.num_inference_steps,
        guidance_scale=args.guidance_scale,
        height=args.height,
        width=args.width,
    )
    save_base_images(base_images, str(output_dir), "base")

    print("\n[Pipeline] Base generation done.")
    print(f"[Pipeline] Check outputs in {output_dir}")


if __name__ == "__main__":
    run_pipeline()