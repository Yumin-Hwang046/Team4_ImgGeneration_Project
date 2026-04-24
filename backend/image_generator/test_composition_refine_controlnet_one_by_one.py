import gc
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
food sitting firmly on the surface,
realistic contact shadow directly under the food,
consistent lighting direction,
seamless blending between food and background,
natural perspective,
appetizing food,
high detail,
professional restaurant advertisement photo,
soft realistic shadow,
no floating object
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
logo,
cartoon,
painting,
overprocessed
"""


def clear_memory():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()


def resize_to_768(image):
    return image.convert("RGB").resize((768, 768), Image.LANCZOS)


def make_canny(image, low=100, high=200):
    image_np = np.array(image)
    canny = cv2.Canny(image_np, low, high)
    canny = canny[:, :, None]
    canny = np.concatenate([canny, canny, canny], axis=2)
    return Image.fromarray(canny)


def load_pipe():
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
    return pipe


def refine_one_image(pipe, image_path):
    print(f"\nprocessing: {image_path.name}")

    image = resize_to_768(Image.open(image_path))
    control_image = make_canny(image)

    canny_path = CANNY_DIR / f"{image_path.stem}_canny_stronger.png"
    control_image.save(canny_path)

    result = pipe(
        prompt=PROMPT,
        negative_prompt=NEGATIVE_PROMPT,
        image=image,
        control_image=control_image,

        # 접촉감/자연스러움 조금 더 강화
        strength=0.36,
        controlnet_conditioning_scale=0.46,
        num_inference_steps=20,
        guidance_scale=6.0,

        height=768,
        width=768,
    ).images[0]

    out_path = OUT_DIR / f"{image_path.stem}__controlnet_refined_stronger.png"
    result.save(out_path)
    print(f"saved: {out_path}")

    del image, control_image, result
    clear_memory()


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
    print("setting: strength=0.36, controlnet=0.46, steps=20, 768px")

    clear_memory()
    pipe = load_pipe()

    for idx, image_path in enumerate(image_files, start=1):
        print(f"\n[{idx}/{len(image_files)}]")
        refine_one_image(pipe, image_path)

    del pipe
    clear_memory()
    print("\ndone")


if __name__ == "__main__":
    main()