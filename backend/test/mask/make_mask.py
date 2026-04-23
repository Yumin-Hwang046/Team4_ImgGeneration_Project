import argparse
import io
import sys

from PIL import Image, ImageOps

try:
    from rembg import remove, new_session
    import onnxruntime as ort
except Exception:
    print("필수 패키지(rembg, onnxruntime)가 누락되었습니다. 'pip install rembg onnxruntime'를 실행하세요.")
    sys.exit(1)


def _remove_background(image: Image.Image) -> Image.Image:
    # 사용 가능한 실행 프로바이더(CPU/GPU)를 감지하고 세션을 명시적으로 생성합니다.
    providers = ort.get_available_providers()
    session = new_session(providers=providers)
    
    result = remove(image, session=session)
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

    # 배경이 제거된 원본 객체(RGBA)도 함께 저장하여 합성 작업에 사용할 수 있도록 합니다.
    no_bg_path = args.output.replace("_mask.png", "_no_bg.png")
    cut.save(no_bg_path)

    print(f"마스크 저장 완료: {args.output}")
    print(f"배경 제거 이미지 저장 완료: {no_bg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
