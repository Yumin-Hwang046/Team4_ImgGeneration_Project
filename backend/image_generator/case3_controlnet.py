import io
import os
import time
from typing import Optional

import torch
from PIL import Image
from rembg import remove
from transformers import DPTForDepthEstimation, DPTImageProcessor
from diffusers import ControlNetModel, StableDiffusionXLControlNetPipeline

# 모델 ID
SDXL_BASE_ID = "stabilityai/stable-diffusion-xl-base-1.0"
CONTROLNET_ID = os.getenv("CONTROLNET_DEPTH_ID", "diffusers/controlnet-depth-sdxl-1.0")
DPT_MODEL_ID = os.getenv("DPT_MODEL_ID", "Intel/dpt-hybrid-midas")

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


def make_depth_map(image: Image.Image, device: str) -> Image.Image:
    """
    [Step 1] 입력 이미지로부터 depth map 생성
    - 가까운 부분: 밝게
    - 먼 부분: 어둡게
    """
    processor = DPTImageProcessor.from_pretrained(DPT_MODEL_ID)
    model = DPTForDepthEstimation.from_pretrained(DPT_MODEL_ID).to(device)

    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)
        depth = outputs.predicted_depth[0]

    # Normalize to 0-255
    depth_min = depth.min()
    depth_max = depth.max()
    depth = (depth - depth_min) / (depth_max - depth_min + 1e-8)
    depth = (depth * 255.0).clamp(0, 255).byte().cpu().numpy()

    depth_image = Image.fromarray(depth)
    return depth_image


def generate_image_case3_controlnet(
    user_image_path: str,
    user_prompt: str,
    format_type: str = "피드",
    controlnet_scale: float = 0.8,
    steps: int = 30,
    guidance: float = 7.0,
    use_rembg: bool = True,
    seed: Optional[int] = None,
) -> dict:
    """
    [Step 2] ControlNet(Depth) 기반 배경 합성
    - 제품 구조 유지 + 배경/조명 변경
    """
    if not os.path.exists(user_image_path):
        raise FileNotFoundError(f"사용자 이미지가 없습니다: {user_image_path}")

    # Step 2-1) 해상도 결정
    width, height = get_sdxl_size(format_type)

    # Step 2-2) 입력 이미지 로드/리사이즈
    image = Image.open(user_image_path).convert("RGB").resize((width, height), Image.BICUBIC)

    # Step 2-2-1) 제품 분리 (rembg)
    if use_rembg:
        cutout = remove(image)
        if isinstance(cutout, Image.Image):
            cutout = cutout.convert("RGBA")
        else:
            cutout = Image.open(io.BytesIO(cutout)).convert("RGBA")
        cutout = cutout.resize((width, height), Image.LANCZOS)
    else:
        cutout = image.convert("RGBA")

    # Step 2-3) 장치 및 dtype
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    # Step 2-4) Depth map 생성
    depth_map = make_depth_map(image, device).resize((width, height), Image.BICUBIC)

    # Step 3) ControlNet + SDXL 파이프라인 로딩
    controlnet = ControlNetModel.from_pretrained(
        CONTROLNET_ID,
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if device == "cuda" else None,
    )
    pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
        SDXL_BASE_ID,
        controlnet=controlnet,
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if device == "cuda" else None,
    ).to(device)

    # Step 4) 시드 고정
    generator = torch.Generator(device=device).manual_seed(seed) if seed else None

    # Step 5) 생성
    result = pipe(
        prompt=user_prompt,
        image=depth_map,
        controlnet_conditioning_scale=controlnet_scale,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=generator,
    ).images[0]

    # Step 6) 제품 합성 (원본 제품을 배경 위에)
    if use_rembg:
        background = result.convert("RGBA")
        result = Image.alpha_composite(background, cutout).convert("RGB")

    # Step 7) 저장 및 반환
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
        controlnet_scale=0.8,
    )
    print("✅ 생성 완료:", output)
