import argparse
import shutil
from pathlib import Path

from case4_ip_adapter import generate_image_case4_ip_adapter

DEFAULT_REFERENCE_IMAGE = (
    Path(__file__).resolve().parent / "reference_presets" / "default.png"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run image generation pipeline (Case4 IP-Adapter)")

    parser.add_argument("--prompt", type=str, required=True, help="Main generation prompt")
    parser.add_argument("--output_dir", type=str, default="outputs", help="Output directory")

    # 기존 흐름에서 전달되는 사용자 이미지
    parser.add_argument("--image_path", type=str, default=None, help="User source image path")

    # 무드별 프리셋 이미지 경로 (없으면 기본 프리셋 사용)
    parser.add_argument(
        "--reference_image_path",
        type=str,
        default=str(DEFAULT_REFERENCE_IMAGE),
        help="Reference preset image path",
    )

    parser.add_argument("--format_type", type=str, default="피드")
    parser.add_argument("--ip_adapter_scale", type=float, default=0.7)
    parser.add_argument("--strength", type=float, default=0.6)

    return parser


def run_pipeline() -> None:
    parser = build_parser()
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not args.image_path:
        raise ValueError("Case4 requires --image_path (user image).")

    ref_path = Path(args.reference_image_path)
    if not ref_path.exists():
        raise FileNotFoundError(f"Reference image not found: {ref_path}")

    result = generate_image_case4_ip_adapter(
        user_image_path=args.image_path,
        reference_image_path=str(ref_path),
        user_prompt=args.prompt,
        format_type=args.format_type,
        ip_adapter_scale=args.ip_adapter_scale,
        strength=args.strength,
    )

    generated_path = Path(result["path"])
    target_path = output_dir / "base_0.png"
    shutil.copyfile(generated_path, target_path)

    print("\n[Pipeline] Case4 generation done.")
    print(f"[Pipeline] Source: {generated_path}")
    print(f"[Pipeline] Copied to: {target_path}")


if __name__ == "__main__":
    run_pipeline()
