import argparse
import io
import sys
from pathlib import Path

from PIL import Image, ImageOps

try:
    from rembg import remove, new_session
    import onnxruntime as ort
except Exception:
    print("필수 패키지(rembg, onnxruntime)가 누락되었습니다. 'pip install rembg onnxruntime'를 실행하세요.")
    sys.exit(1)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def resolve_providers() -> list[str]:
    """안정적인 GPU(CUDA) 및 CPU 프로바이더만 선택하여 반환합니다."""
    available = ort.get_available_providers()
    providers = []
    if "CUDAExecutionProvider" in available:
        providers.append("CUDAExecutionProvider")
    providers.append("CPUExecutionProvider")
    return providers


def _remove_background(
    image: Image.Image, 
    session=None, 
    post_process_mask: bool = False,
    alpha_matting: bool = False
) -> Image.Image:
    # 사용 가능한 실행 프로바이더(CPU/GPU)를 감지하고 세션을 명시적으로 생성합니다.
    if session is None:
        session = new_session(providers=resolve_providers())
    
    # alpha_matting 옵션 적용 (정교한 외곽선 추출용)
    result = remove(
        image, 
        session=session, 
        post_process_mask=post_process_mask,
        alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=10
    )
    if isinstance(result, bytes):
        return Image.open(io.BytesIO(result)).convert("RGBA")
    return result.convert("RGBA")


def process_image(input_path, output_path, session, post_process: bool = False, alpha_matting: bool = False):
    """단일 이미지에 대해 배경 제거 및 마스크 생성을 처리합니다."""
    img = Image.open(input_path).convert("RGBA")
    cut = _remove_background(img, session=session, post_process_mask=post_process, alpha_matting=alpha_matting)

    # 전경(음식)은 alpha=255, 배경은 alpha=0
    alpha = cut.split()[-1]
    # 음식(전경)=검정, 배경=흰색으로 뒤집기
    mask = ImageOps.invert(alpha).convert("L")
    mask.save(str(output_path))

    # 배경이 제거된 원본 객체(RGBA)도 함께 저장하여 합성 작업에 사용할 수 있도록 합니다.
    no_bg_path = str(output_path).replace("_mask.png", "_no_bg.png")
    cut.save(no_bg_path)

    print(f"마스크 저장 완료: {output_path}")
    print(f"배경 제거 이미지 저장 완료: {no_bg_path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="사용자 이미지 경로 (파일 또는 디렉토리)")
    parser.add_argument("--output", required=True, help="저장 경로 (파일인 경우 마스크 경로, 디렉토리인 경우 출력 디렉토리)")
    parser.add_argument("--post-process", action="store_true", help="마스크 외곽선 부드럽게 처리 (post_process_mask)")
    parser.add_argument("--alpha-matting", action="store_true", help="정교한 외곽선 추출 (alpha_matting)")
    parser.add_argument("--model", default="u2net", help="사용할 모델 (u2net, isnet-general-use, sam 등)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    # 세션 한 번만 생성하여 반복 작업 시 성능 최적화
    session = new_session(model_name=args.model, providers=resolve_providers())

    if input_path.is_dir():
        output_path.mkdir(parents=True, exist_ok=True)
        images = sorted([
            p for p in input_path.iterdir() 
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        ])
        
        if not images:
            print(f"이미지 파일을 찾을 수 없습니다: {input_path}")
            return 1

        for img_p in images:
            # 디렉토리 모드에서는 파일명_mask.png 형태로 저장
            target_mask = output_path / f"{img_p.stem}_mask.png"
            process_image(img_p, target_mask, session, args.post_process, args.alpha_matting)
    else:
        process_image(input_path, output_path, session, args.post_process, args.alpha_matting)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
