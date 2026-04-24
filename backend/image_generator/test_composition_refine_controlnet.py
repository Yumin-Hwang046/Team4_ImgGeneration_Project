import cv2
import torch
import numpy as np
from pathlib import Path
from PIL import Image
from diffusers import StableDiffusionXLControlNetImg2ImgPipeline, ControlNetModel

BASE_MODEL = "SG161222/RealVisXL_V5.0"
CONTROLNET_MODEL = "diffusers/controlnet-canny-sdxl-1.0"

INPUT_DIR = Path("image_generator/outputs/food_reference_blend/01_composite")
OUT_DIR = Path("image_generator/outputs/food_reference_blend/02_controlnet_refine")
CANNY_DIR = OUT_DIR / "_canny"

OUT_DIR.mkdir(parents=True, exist_ok=True)
CANNY_DIR.mkdir(parents=True, exist_ok=True)

PROMPT = """
realistic commercial food photography,
food naturally placed on the plate or table,
realistic contact shadow,
consistent lighting,
seamless blending between food and background,
natural perspective,
appetizing food,
high detail,
professional restaurant advertisement photo
"""

NEGATIVE_PROMPT = """
floating food,
unrealistic shadow,
bad perspective,
distorted food,
melted food,
duplicated food,
extra plate,
extra object,
deformed,
low quality,
blurry,
text,
watermark,
logo
"""


def resize_to_1024(image: Image.Image) -> Image.Image:
    return image.convert("RGB").resize((1024, 1024), Image.LANCZOS)


def make_canny(image: Image.Image, low: int = 80, high: int = 180) -> Image.Image:
    image_np = np.array(image)
    canny = cv2.Canny(image_np, low, high)
    canny = canny[:, :, None]
    canny = np.concatenate([canny, canny, canny], axis=2)
    return Image.fromarray(canny)


def refine_image(pipe, image_path: Path):
    image = resize_to_1024(Image.open(image_path))
    control_image = make_canny(image)

    control_image.save(CANNY_DIR / f"{image_path.stem}_canny.png")

    result = pipe(
        prompt=PROMPT,
        negative_prompt=NEGATIVE_PROMPT,
        image=image,
        control_image=control_image,
        strength=0.25,
        controlnet_conditioning_scale=0.45,
        num_inference_steps=30,
        guidance_scale=6.0,
        height=1024,
        width=1024,
    ).images[0]

    out_path = OUT_DIR / f"{image_path.stem}__controlnet_refined.png"
    result.save(out_path)
    print(f"saved: {out_path}")


def main():
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA 사용 불가. GPU/CUDA 확인 필요")

    image_files = sorted(
        list(INPUT_DIR.glob("*.png"))
        + list(INPUT_DIR.glob("*.jpg"))
        + list(INPUT_DIR.glob("*.jpeg"))
        + list(INPUT_DIR.glob("*.webp"))
    )

    if not image_files:
        raise FileNotFoundError(f"입력 이미지 없음: {INPUT_DIR}")

    print(f"input images: {len(image_files)}")

    controlnet = ControlNetModel.from_pretrained(
        CONTROLNET_MODEL,
        torch_dtype=torch.float16,
        use_safetensors=True,
    )

    pipe = StableDiffusionXLControlNetImg2ImgPipeline.from_pretrained(
        BASE_MODEL,
        controlnet=controlnet,
        torch_dtype=torch.float16,
        use_safetensors=True,
        variant="fp16",
    ).to("cuda")

    pipe.enable_attention_slicing()
    pipe.enable_vae_slicing()

    for image_path in image_files:
        print(f"processing: {image_path.name}")
        refine_image(pipe, image_path)

    print("done")


if __name__ == "__main__":
    main()