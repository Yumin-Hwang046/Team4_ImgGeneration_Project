import io
import os
import time
from typing import Optional

import torch
from PIL import Image, ImageOps
from rembg import remove
from diffusers import StableDiffusionXLInpaintPipeline

# 모델 ID
SDXL_INPAINT_ID = "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"

# 경로 설정
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


def make_background_mask(image: Image.Image) -> Image.Image:
    """
    [Step 1] rembg로 배경 마스크 생성
    - 흰색(255): 바꿀 영역(배경)
    - 검정(0): 유지할 영역(제품)
    """
    cutout = remove(image)
    if isinstance(cutout, Image.Image):
        cutout = cutout.convert("RGBA")
    else:
        cutout = Image.open(io.BytesIO(cutout)).convert("RGBA")

    alpha = cutout.split()[-1]
    mask = ImageOps.invert(alpha)
    return mask


def build_background_prompt(user_prompt: str) -> str:
    base = (
        "Replace ONLY the background with the following description. "
        "Keep the product and plate unchanged. "
        "Do not alter product texture, size, or position."
    )
    return f"{base} Background description: {user_prompt.strip()}"


def generate_image_case3_controlnet(
    user_image_path: str,
    user_prompt: str,
    format_type: str = "피드",
    steps: int = 30,
    guidance: float = 7.0,
    use_rembg: bool = True,
    strength: float = 0.7,
    seed: Optional[int] = None,
) -> dict:
    """
    [Step 2] Inpainting 기반 배경 합성
    - 제품은 유지, 배경만 교체
    """
    if not os.path.exists(user_image_path):
        raise FileNotFoundError(f"사용자 이미지가 없습니다: {user_image_path}")

    # Step 2-1) 해상도 결정
    width, height = get_sdxl_size(format_type)

    # Step 2-2) 입력 이미지 로드/리사이즈
    image = Image.open(user_image_path).convert("RGB").resize((width, height), Image.BICUBIC)

    # Step 2-3) 장치 및 dtype
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    # Step 2-4) 마스크 생성 (배경만 흰색)
    if not use_rembg:
        raise ValueError("use_rembg=False는 아직 지원하지 않습니다. (마스크 필요)")
    mask = make_background_mask(image).resize((width, height), Image.NEAREST)

    # Step 3) SDXL Inpainting 파이프라인 로딩
    pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
        SDXL_INPAINT_ID,
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if device == "cuda" else None,
    ).to(device)

    # Step 4) 시드 고정
    generator = torch.Generator(device=device).manual_seed(seed) if seed else None

    # Step 5) 생성 (배경만 변경)
    final_prompt = build_background_prompt(user_prompt)
    result = pipe(
        prompt=final_prompt,
        image=image,
        mask_image=mask,
        num_inference_steps=steps,
        guidance_scale=guidance,
        strength=strength,
        generator=generator,
    ).images[0]

    # Step 6) 저장 및 반환
    os.makedirs(GENERATED_ROOT, exist_ok=True)
    filename = f"sdxl_case3_{int(time.time())}.png"
    out_path = os.path.join(GENERATED_ROOT, filename)
    result.save(out_path)

    return {
        "path": out_path,
        "url": f"{PUBLIC_URL_PREFIX}/{filename}",
        "source_image": user_image_path,
    }


if __name__ == "__main__":
    # 테스트용 더미 입력
    test_image = "/path/to/user_image.png"
    test_prompt = "따뜻한 카페 배경, 부드러운 조명, 프리미엄 제품 촬영"

    output = generate_image_case3_controlnet(
        user_image_path=test_image,
        user_prompt=test_prompt,
        format_type="피드",
    )
    print("✅ 생성 완료:", output)
