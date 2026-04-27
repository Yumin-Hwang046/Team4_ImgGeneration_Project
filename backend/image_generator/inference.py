from diffusers import StableDiffusionPipeline
import torch
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observability import build_langfuse_media_list, log_langfuse_trace

def get_device():
    return "cuda" if torch.cuda.is_available() else "cpu"


def generate_image(
    prompt: str,
    negative_prompt: str,
    output_dir: str = "backend/image_generator"
):
    start_time = time.time()
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

    saved_paths = [str(path) for path in sorted(output_path.glob("output_*.png"))]
    log_langfuse_trace(
        name="image_generator.inference",
        input={"prompt": prompt, "negative_prompt": negative_prompt, "output_dir": output_dir, "device": device},
        output={"saved_paths": saved_paths, "output_images": build_langfuse_media_list(saved_paths)},
        metadata={"duration_sec": time.time() - start_time},
        tags=["image_generator", "experiment", "sd15"],
    )


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
