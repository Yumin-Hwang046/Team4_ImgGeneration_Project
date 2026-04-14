import argparse
import io
import sys

from PIL import Image, ImageOps

try:
    from rembg import remove
except Exception:
    print("rembg가 필요합니다. 먼저 `pip install rembg`를 실행하세요.")
    sys.exit(1)


def _remove_background(image: Image.Image) -> Image.Image:
    result = remove(image)
    if isinstance(result, bytes):
        return Image.open(io.BytesIO(result)).convert("RGBA")
    return result.convert("RGBA")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="사용자 이미지 경로")
    parser.add_argument("--output", required=True, help="마스크 저장 경로")
    args = parser.parse_args()

    img = Image.open(args.input).convert("RGBA")
    cut = _remove_background(img)

    # 전경(음식)은 alpha=255, 배경은 alpha=0
    alpha = cut.split()[-1]
    # 음식(전경)=검정, 배경=흰색으로 뒤집기
    mask = ImageOps.invert(alpha).convert("L")
    mask.save(args.output)
    print(f"마스크 저장 완료: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
