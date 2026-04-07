import os
import time
from typing import Optional

import torch
from PIL import Image
from diffusers import AutoPipelineForImage2Image

# SDXL Base 모델
SDXL_BASE_ID = "stabilityai/stable-diffusion-xl-base-1.0"

# IP-Adapter 설정
IP_ADAPTER_REPO = os.getenv("IP_ADAPTER_REPO", "h94/IP-Adapter")
IP_ADAPTER_SUBFOLDER = os.getenv("IP_ADAPTER_SUBFOLDER", "sdxl_models")
IP_ADAPTER_WEIGHT = os.getenv("IP_ADAPTER_WEIGHT", "ip-adapter_sdxl.bin")

# 경로 설정
GENERATED_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "generated"))
PUBLIC_URL_PREFIX = os.getenv("GENERATED_URL_PREFIX", "/static/generated")


def get_sdxl_size(format_type: str) -> tuple[int, int]:
    if format_type == "스토리":
        return (1024, 1792)
    elif format_type == "웹 배너":
        return (1792, 1024)
    else:
        return (1024, 1024)


def generate_image_case4_ip_adapter(
    user_image_path: str,
    reference_image_path: str,
    user_prompt: str,
    format_type: str = "피드",
    ip_adapter_scale: float = 0.7,
    strength: float = 0.6,
    steps: int = 30,
    guidance: float = 7.0,
    seed: Optional[int] = None,
) -> dict:
    """
    Case4: 사용자 이미지(내용) + 레퍼런스 이미지(스타일) 동시 사용
    - image = 사용자 이미지
    - ip_adapter_image = 레퍼런스 이미지
    """
    if not os.path.exists(user_image_path):
        raise FileNotFoundError(f"사용자 이미지가 없습니다: {user_image_path}")
    if not os.path.exists(reference_image_path):
        raise FileNotFoundError(f"레퍼런스 이미지가 없습니다: {reference_image_path}")

    width, height = get_sdxl_size(format_type)

    init_image = Image.open(user_image_path).convert("RGB").resize((width, height), Image.BICUBIC)
    ref_image = Image.open(reference_image_path).convert("RGB").resize((width, height), Image.BICUBIC)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    pipe = AutoPipelineForImage2Image.from_pretrained(
        SDXL_BASE_ID,
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if device == "cuda" else None,
    ).to(device)

    pipe.load_ip_adapter(
        IP_ADAPTER_REPO,
        subfolder=IP_ADAPTER_SUBFOLDER,
        weight_name=IP_ADAPTER_WEIGHT,
    )
    pipe.set_ip_adapter_scale(ip_adapter_scale)

    generator = torch.Generator(device=device).manual_seed(seed) if seed else None

    final_prompt = build_case4_prompt(user_prompt)
    image = pipe(
        prompt=final_prompt,
        image=init_image,
        ip_adapter_image=ref_image,
        strength=strength,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=generator,
    ).images[0]

    os.makedirs(GENERATED_ROOT, exist_ok=True)
    filename = f"sdxl_case4_ip_{int(time.time())}.png"
    out_path = os.path.join(GENERATED_ROOT, filename)
    image.save(out_path)

    return {
        "path": out_path,
        "url": f"{PUBLIC_URL_PREFIX}/{filename}",
        "user_image_path": user_image_path,
        "reference_image_path": reference_image_path,
    }


def build_case4_prompt(user_prompt: str) -> str:
    base = (
        "Use the food from the user image exactly. "
        "Replace ONLY the background and table setting with the reference image style. "
        "Keep the food size, shape, texture, and position unchanged. "
        "Photorealistic product photo, studio lighting, sharp focus."
    )
    return f"{base} {user_prompt.strip()}"


if __name__ == "__main__":
    test_user = "/path/to/user_image.png"
    test_ref = "/path/to/reference.png"
    test_prompt = "Replace ONLY the background with a warm cafe interior. Keep the food unchanged."

    result = generate_image_case4_ip_adapter(
        user_image_path=test_user,
        reference_image_path=test_ref,
        user_prompt=test_prompt,
    )
    print(result)
