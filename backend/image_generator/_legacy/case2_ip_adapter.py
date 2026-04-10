import os
import time
from typing import Optional

import torch
from PIL import Image
from diffusers import AutoPipelineForText2Image

# SDXL Base 모델
SDXL_BASE_ID = "stabilityai/stable-diffusion-xl-base-1.0"

# IP-Adapter 설정 (필요 시 환경변수로 바꾸기 가능)
IP_ADAPTER_REPO = os.getenv("IP_ADAPTER_REPO", "h94/IP-Adapter")
IP_ADAPTER_SUBFOLDER = os.getenv("IP_ADAPTER_SUBFOLDER", "sdxl_models")
IP_ADAPTER_WEIGHT = os.getenv(
    "IP_ADAPTER_WEIGHT",
    "ip-adapter_sdxl.bin"
)

# 경로 설정
PRESET_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "presets"))
GENERATED_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "generated"))

# 공개 URL prefix (FastAPI 정적 서빙 기준)
PUBLIC_URL_PREFIX = os.getenv("GENERATED_URL_PREFIX", "/static/generated")


def get_sdxl_size(format_type: str) -> tuple[int, int]:
    """
    [Step 0] 포맷을 SDXL 권장 해상도로 매핑
    """
    if format_type == "스토리":
        return (1024, 1792)
    elif format_type == "웹 배너":
        return (1792, 1024)
    else:
        return (1024, 1024)


def resolve_reference_image(
    user_reference_path: Optional[str],
    preset_key: Optional[str],
    preset_filename: Optional[str],
) -> str:
    """
    [Step 1] 레퍼런스 이미지 경로 결정
    - user_reference_path가 있으면 우선 사용
    - 없으면 preset_key에서 이미지 선택
    """
    if user_reference_path:
        if not os.path.exists(user_reference_path):
            raise FileNotFoundError(f"레퍼런스 이미지가 없습니다: {user_reference_path}")
        return user_reference_path

    if not preset_key:
        raise ValueError("preset_key 또는 user_reference_path 중 하나는 필요합니다.")

    preset_dir = os.path.join(PRESET_ROOT, preset_key)
    if not os.path.isdir(preset_dir):
        raise FileNotFoundError(f"프리셋 폴더가 없습니다: {preset_dir}")

    if preset_filename:
        candidate = os.path.join(preset_dir, preset_filename)
        if not os.path.exists(candidate):
            raise FileNotFoundError(f"프리셋 파일이 없습니다: {candidate}")
        return candidate

    candidates = [
        f for f in os.listdir(preset_dir)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    ]
    if not candidates:
        raise FileNotFoundError(f"프리셋 폴더에 이미지가 없습니다: {preset_dir}")

    if "sample_1.png" in candidates:
        filename = "sample_1.png"
    else:
        filename = sorted(candidates)[0]

    return os.path.join(preset_dir, filename)


def generate_image_case2_ip_adapter(
    user_prompt: str,
    mood_key: str | None = None,
    format_type: str = "피드",
    user_reference_path: Optional[str] = None,
    preset_key: Optional[str] = None,
    preset_filename: Optional[str] = None,
    ip_adapter_scale: float = 0.6,
    steps: int = 30,
    guidance: float = 7.0,
    seed: Optional[int] = None,
) -> dict:
    """
    [Step 2] SDXL + IP-Adapter 기반 Case2 스타일 전이
    - 레퍼런스 이미지를 '스타일'로 사용 (구조 보존은 덜 강함)
    """
    # Step 2-1) 레퍼런스 이미지 결정
    ref_path = resolve_reference_image(user_reference_path, preset_key, preset_filename)

    # Step 2-2) 사용자 프롬프트 사용 (무드가 있으면 뒤에 추가)
    prompt = user_prompt.strip()
    if mood_key:
        prompt = f"{prompt}, {mood_key}"

    # Step 2-3) 해상도 결정
    width, height = get_sdxl_size(format_type)

    # Step 2-4) 레퍼런스 이미지 로드/리사이즈
    ref_image = Image.open(ref_path).convert("RGB").resize((width, height), Image.BICUBIC)

    # Step 2-5) 장치 및 dtype
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    # Step 3) SDXL T2I 파이프라인 로딩 (IP-Adapter 권장 방식)
    pipe = AutoPipelineForText2Image.from_pretrained(
        SDXL_BASE_ID,
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if device == "cuda" else None,
    ).to(device)

    # Step 4) IP-Adapter 로딩 및 스케일 적용
    try:
        pipe.load_ip_adapter(
            IP_ADAPTER_REPO,
            subfolder=IP_ADAPTER_SUBFOLDER,
            weight_name=IP_ADAPTER_WEIGHT,
        )
        pipe.set_ip_adapter_scale(ip_adapter_scale)
    except Exception as e:
        raise RuntimeError(
            "IP-Adapter 로딩에 실패했습니다. "
            "IP_ADAPTER_* 환경변수 또는 weight 이름을 확인하세요."
        ) from e

    # Step 5) 시드 고정 (재현성 필요 시)
    generator = torch.Generator(device=device).manual_seed(seed) if seed else None

    # Step 6) 이미지 생성
    image = pipe(
        prompt=prompt,
        ip_adapter_image=ref_image,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=generator,
    ).images[0]

    # Step 7) 저장 및 반환
    os.makedirs(GENERATED_ROOT, exist_ok=True)
    filename = f"sdxl_case2_ip_{int(time.time())}.png"
    out_path = os.path.join(GENERATED_ROOT, filename)
    image.save(out_path)

    return {
        "path": out_path,
        "url": f"{PUBLIC_URL_PREFIX}/{filename}",
        "reference_path": ref_path,
    }


if __name__ == "__main__":
    # 테스트: 프리셋(clean) 사용
    test_prompt = '이미지에 "신메뉴 출시"라는 광고 문구를 추가해줘.'
    test_mood = "깔끔한 상품 홍보"
    result = generate_image_case2_ip_adapter(
        user_prompt=test_prompt,
        mood_key=test_mood,
        format_type="피드",
        preset_key="clean",
        preset_filename="sample_1.png",
        ip_adapter_scale=0.6,
    )
    print("✅ 생성 완료:")
    print(" - path:", result["path"])
    print(" - url :", result["url"])
    print(" - ref :", result["reference_path"])
