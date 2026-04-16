import argparse
import io
import sys
import torch
import numpy as np

from PIL import Image, ImageOps, ImageFilter
from transformers import AutoModelForImageSegmentation
from torchvision.transforms.functional import normalize

# 모델을 전역 변수로 관리하여 테스트 시 매번 로딩하는 시간을 절약합니다.
_MODEL = None
_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def get_model():
    global _MODEL
    if _MODEL is None:
        # BiRefNet은 1024x1024 해상도에서 미세한 경계를 잡는 데 특화된 고성능 모델입니다.
        print(f"BiRefNet 모델 로딩 중... (장치: {_DEVICE})")
        _MODEL = AutoModelForImageSegmentation.from_pretrained("ZhengPeng7/BiRefNet", trust_remote_code=True)
        _MODEL.to(_DEVICE)
        _MODEL.eval()
    return _MODEL

def _remove_background(image: Image.Image) -> Image.Image:
    """BiRefNet 모델을 사용하여 배경을 제거하고 Alpha 채널을 생성합니다."""
    model = get_model()

    # 전처리
    orig_size = image.size
    # BiRefNet은 1024x1024 해상도를 기본으로 사용합니다.
    input_images = image.convert("RGB").resize((1024, 1024), Image.LANCZOS)
    im_np = np.array(input_images) / 255.0
    im_tensor = torch.tensor(im_np, dtype=torch.float32).permute(2, 0, 1)
    # BiRefNet에 맞는 표준 ImageNet 정규화 적용
    im_tensor = normalize(im_tensor, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]).unsqueeze(0).to(_DEVICE)

    # 추론
    print(f"배경 분석 중... (해상도: {orig_size[0]}x{orig_size[1]})")
    with torch.no_grad():
        preds = model(im_tensor)
    
    # BiRefNet은 여러 계층의 출력을 반환하며, 마지막 결과가 가장 정교합니다.
    result = preds[-1] if isinstance(preds, (list, tuple)) else preds

    # 0~1 사이의 확률값으로 변환 및 스케일링
    result = torch.sigmoid(result).squeeze()
    
    # 모델 출력이 매우 균일할 경우(원본 그대로 나오는 현상)를 대비해 동적 스케일링 적용
    res_min, res_max = result.min(), result.max()
    if res_max > res_min:
        result = (result - res_min) / (res_max - res_min + 1e-8)
    
    # [개선] 감마 보정 극대화 (0.4 -> 0.3)
    # 포크 날 끝자락의 아주 미미한 신호까지 전경으로 끌어올립니다.
    result = torch.pow(result, 0.3)

    result_np = (result * 255).cpu().numpy().astype(np.uint8)

    # [핵심 수정] 저해상도 단계에서 안전 마진 확보
    # 고해상도로 리사이징할 때 얇은 선이 뭉개지는 것을 방지하기 위해 
    # 1024 해상도 상태에서 먼저 3x3 필터로 선을 약간 두껍게 만든 뒤 확장합니다.
    mask_temp = Image.fromarray(result_np).filter(ImageFilter.MaxFilter(size=3))
    mask_pil = mask_temp.resize(orig_size, Image.BILINEAR)

    # [수정] 노이즈 억제를 위해 시각화 임계값을 약간 상향 조정 (10 -> 30)
    mask_pil = mask_pil.point(lambda p: 255 if p > 30 else 0)
    
    # 원본 이미지에 마스크(Alpha) 적용
    result_image = image.copy().convert("RGBA")
    result_image.putalpha(mask_pil)
    return result_image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="사용자 이미지 경로")
    parser.add_argument("--output", required=True, help="마스크 저장 경로")
    parser.add_argument("--cpu", action="store_true", help="GPU 호환성 이슈 발생 시 CPU 사용 강제")
    args = parser.parse_args()

    if args.cpu:
        global _DEVICE
        _DEVICE = torch.device("cpu")
        print("CPU 모드로 실행합니다.")

    # 이미지 로드 시 EXIF 정보를 바탕으로 회전 보정 적용
    img_raw = Image.open(args.input)
    img = ImageOps.exif_transpose(img_raw).convert("RGBA")
    cut = _remove_background(img)

    # 전경(음식)은 alpha=255, 배경은 alpha=0
    alpha = cut.split()[-1]
    
    # 1. 배경 제거된 원본 이미지 저장 (RGBA) - 사용자 확인용
    # 이제 설정하신 output 경로로 배경이 투명한 실제 음식 사진이 저장됩니다.
    cut.save(args.output)
    print(f"배경 제거 완료 (RGBA): {args.output}")

    # 2. 인페인팅(Case 5) 전용 흑백 마스크 별도 생성 및 저장
    # 파일명 뒤에 _mask가 붙은 형태로 자동 저장됩니다.
    mask_path = args.output.rsplit('.', 1)[0] + "_mask.png"
    
    # 임계값 적용: 음식 부분은 검정(0), 배경 부분은 흰색(255)
    # 배경 노이즈 유입을 막기 위해 이진화 임계값을 조정 (20 -> 40)
    mask_bin = alpha.point(lambda p: 0 if p > 40 else 255)

    # [개선] 해상도 비례 필터 크기 자동 계산 (기준: 4000px일 때 7, 9)
    # 필터 크기는 반드시 홀수여야 하므로 계산 후 조정 로직을 추가합니다.
    width, _ = alpha.size
    def get_odd_size(base_size):
        size = int(base_size * (width / 4000))
        return max(3, size if size % 2 != 0 else size + 1)

    dynamic_median = get_odd_size(7)
    dynamic_morph = get_odd_size(9)

    # 1. MedianFilter를 먼저 적용하여 팽창 전 잔먼지를 제거합니다.
    mask_bin = mask_bin.filter(ImageFilter.MedianFilter(size=dynamic_median))
    # 2. 팽창(Min)과 침식(Max)의 크기를 동일하게 맞춰 노이즈 증식을 억제합니다.
    mask_bin = mask_bin.filter(ImageFilter.MinFilter(size=dynamic_morph))
    mask_bin = mask_bin.filter(ImageFilter.MaxFilter(size=dynamic_morph))
    
    mask_final = mask_bin.convert("L")
    mask_final.save(mask_path)
    print(f"인페인팅용 마스크 저장 완료 (L): {mask_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
