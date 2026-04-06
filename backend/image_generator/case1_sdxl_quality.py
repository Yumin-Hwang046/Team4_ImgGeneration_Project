import os
import time
import torch
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline

from image_generator.prompt_builder import build_sdxl_prompt

# SDXL 모델 ID (Base + Refiner 조합)
SDXL_BASE_ID = "stabilityai/stable-diffusion-xl-base-1.0"
SDXL_REFINER_ID = "stabilityai/stable-diffusion-xl-refiner-1.0"
# 공개 URL prefix (FastAPI에서 정적 서빙할 때 사용)
PUBLIC_URL_PREFIX = os.getenv("GENERATED_URL_PREFIX", "/static/generated")


def get_sdxl_size(format_type: str) -> tuple[int, int]:
    """
    [Step 0] 사용자가 요청한 포맷을 SDXL 권장 해상도로 매핑합니다.
    """
    if format_type == "스토리":
        return (1024, 1792)
    elif format_type == "웹 배너":
        return (1792, 1024)
    else:
        return (1024, 1024)


def generate_image_sdxl_quality(
    image_analysis_text: str,
    mood_key: str,
    format_type: str = "피드",
    base_steps: int = 30,
    refiner_steps: int = 15,
    guidance: float = 7.0,
    high_noise_frac: float = 0.8,
    seed: int | None = None,
) -> dict:
    """
    [Step 1] SDXL Base + Refiner로 고품질 이미지를 생성합니다.
    GCP L4 GPU 기준으로 fp16 사용, 1024 해상도 권장.
    """
    # Step 1-1) 한글 분석 텍스트 + 무드를 영어 프롬프트로 변환
    prompt = build_sdxl_prompt(image_analysis_text, mood_key)

    # Step 1-2) 해상도 결정
    width, height = get_sdxl_size(format_type)

    # Step 1-3) 장치 및 dtype 결정 (L4 GPU 기준 fp16)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    # Step 2) SDXL Base 로딩
    base = StableDiffusionXLPipeline.from_pretrained(
        SDXL_BASE_ID,
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if device == "cuda" else None,
    ).to(device)

    # Step 3) SDXL Refiner 로딩
    refiner = StableDiffusionXLImg2ImgPipeline.from_pretrained(
        SDXL_REFINER_ID,
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if device == "cuda" else None,
    ).to(device)

    # Step 4) 시드 고정 (재현성 필요 시)
    generator = torch.Generator(device=device).manual_seed(seed) if seed else None

    # Step 5) Base로 1차 생성 (latent)
    base_result = base(
        prompt=prompt,
        width=width,
        height=height,
        num_inference_steps=base_steps,
        guidance_scale=guidance,
        output_type="latent",
        denoising_end=high_noise_frac,
        generator=generator,
    )

    # Step 6) Refiner로 품질 보정
    image = refiner(
        prompt=prompt,
        image=base_result.images,
        num_inference_steps=refiner_steps,
        guidance_scale=guidance,
        denoising_start=high_noise_frac,
        generator=generator,
    ).images[0]

    # Step 7) 결과 저장
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "generated"))
    os.makedirs(out_dir, exist_ok=True)

    filename = f"sdxl_{int(time.time())}.png"
    out_path = os.path.join(out_dir, filename)
    image.save(out_path)

    return {
        "path": out_path,
        "url": f"{PUBLIC_URL_PREFIX}/{filename}",
    }


if __name__ == "__main__":
    # 테스트용 더미 입력
    test_analysis = "하얀 탁자 위에 커피 한 잔과 초코 마카롱이 놓여 있습니다. 카페 조명이 은은합니다."
    test_mood = "프리미엄 매장·상품"
    test_format = "스토리"

    result = generate_image_sdxl_quality(test_analysis, test_mood, test_format)
    print("✅ 생성 완료:")
    print(" - path:", result["path"])
    print(" - url :", result["url"])
