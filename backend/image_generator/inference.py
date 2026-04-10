from diffusers import StableDiffusionPipeline
import torch
from pathlib import Path


def get_device():
    return "cuda" if torch.cuda.is_available() else "cpu"


def generate_image(
    prompt: str,
    negative_prompt: str,
    output_dir: str = "backend/image_generator"
):
    device = get_device()

    print(f"Using device: {device}")

    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    )

    pipe = pipe.to(device)
    pipe.enable_attention_slicing()

    images = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=40,
        guidance_scale=8.5,
        num_images_per_prompt=4
    ).images

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for i, image in enumerate(images):
        save_path = output_path / f"output_{i}.png"
        image.save(save_path)
        print(f"Saved to {save_path}")


if __name__ == "__main__":
    prompt = """
Japanese tonkatsu pork cutlet,
crispy golden panko crust,
served on a white plate with shredded cabbage,
close-up food photography,
soft natural lighting,
high quality, realistic
"""

    negative_prompt = """
egg, mushroom, strange food, mixed dishes,
deformed, unrealistic, weird texture,
blurry, low quality
"""

    generate_image(prompt, negative_prompt)