import os
import time
from typing import Optional

import torch
from PIL import Image
from diffusers import StableDiffusionXLImg2ImgPipeline

from image_generator.prompt_builder import build_sdxl_prompt

# SDXL Base 모델 (Case2 baseline: Img2Img)
SDXL_BASE_ID = "stabilityai/stable-diffusion-xl-base-1.0"

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


def resolve_reference_image(user_reference_path: Optional[str], preset_key: Optional[str]) -> str:
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

    candidates = [
        f for f in os.listdir(preset_dir)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    ]
    if not candidates:
        raise FileNotFoundError(f"프리셋 폴더에 이미지가 없습니다: {preset_dir}")

    # sample_1.png가 있으면 우선, 없으면 정렬 후 첫 번째
    if "sample_1.png" in candidates:
        filename = "sample_1.png"
    else:
        filename = sorted(candidates)[0]

    return os.path.join(preset_dir, filename)


def generate_image_case2(
    image_analysis_text: str,
    mood_key: str,
    format_type: str = "피드",
    user_reference_path: Optional[str] = None,
    preset_key: Optional[str] = None,
    strength: float = 0.6,
    steps: int = 30,
    guidance: float = 7.0,
    seed: Optional[int] = None,
) -> dict:
    """
    [Step 2] SDXL Img2Img 기반 Case2 스타일 전이 (baseline)
    - 레퍼런스 이미지를 스타일 힌트로 사용
    - IP-Adapter 없이 최소 코드로 구현
    """
    # Step 2-1) 레퍼런스 이미지 결정
    ref_path = resolve_reference_image(user_reference_path, preset_key)

    # Step 2-2) 프롬프트 생성
    prompt = build_sdxl_prompt(image_analysis_text, mood_key)

    # Step 2-3) 해상도 결정
    width, height = get_sdxl_size(format_type)

    # Step 2-4) 레퍼런스 이미지 로드/리사이즈
    init_image = Image.open(ref_path).convert("RGB").resize((width, height), Image.BICUBIC)

    # Step 2-5) 장치 및 dtype
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    # Step 3) SDXL Img2Img 파이프라인 로딩
    pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
        SDXL_BASE_ID,
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if device == "cuda" else None,
    ).to(device)

    # Step 4) 시드 고정 (재현성 필요 시)
    generator = torch.Generator(device=device).manual_seed(seed) if seed else None

    # Step 5) Img2Img 생성
    image = pipe(
        prompt=prompt,
        image=init_image,
        strength=strength,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=generator,
    ).images[0]

    # Step 6) 저장 및 반환
    os.makedirs(GENERATED_ROOT, exist_ok=True)
    filename = f"sdxl_case2_{int(time.time())}.png"
    out_path = os.path.join(GENERATED_ROOT, filename)
    image.save(out_path)

    return {
        "path": out_path,
        "url": f"{PUBLIC_URL_PREFIX}/{filename}",
        "reference_path": ref_path,
    }


if __name__ == "__main__":
    # 테스트: 프리셋(clean) 사용
    test_analysis = "하얀 배경 위에 커피 한 잔이 놓여 있습니다. 조명이 부드럽습니다."
    test_mood = "깔끔한 상품 홍보"
    result = generate_image_case2(
        image_analysis_text=test_analysis,
        mood_key=test_mood,
        format_type="피드",
        preset_key="clean",
        strength=0.6,
    )
    print("✅ 생성 완료:")
    print(" - path:", result["path"])
    print(" - url :", result["url"])
    print(" - ref :", result["reference_path"])
