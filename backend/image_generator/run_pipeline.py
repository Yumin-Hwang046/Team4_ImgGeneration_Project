import sys
import time
from pathlib import Path

from inference_base import SDXLBaseGenerator, save_images as save_base_images

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observability import build_langfuse_media_list, log_langfuse_trace


def run_pipeline() -> None:
    start_time = time.time()
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

    output_dir = "outputs"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    base_generator = SDXLBaseGenerator()
    base_images = base_generator.generate(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_images_per_prompt=1,
        num_inference_steps=25,
        guidance_scale=7.5,
        height=768,
        width=768,
    )
    save_base_images(base_images, output_dir, "base")
    output_paths = [str(path) for path in sorted(Path(output_dir).glob("base*.png"))]

    log_langfuse_trace(
        name="image_generator.run_pipeline",
        input={"prompt": prompt, "negative_prompt": negative_prompt, "output_dir": output_dir},
        output={"saved_paths": output_paths, "output_images": build_langfuse_media_list(output_paths)},
        metadata={"duration_sec": time.time() - start_time},
        tags=["image_generator", "experiment", "pipeline"],
    )

    print("\n[Pipeline] Base generation done.")
    print("[Pipeline] Check outputs in backend/image_generator/outputs/")


if __name__ == "__main__":
    run_pipeline()
