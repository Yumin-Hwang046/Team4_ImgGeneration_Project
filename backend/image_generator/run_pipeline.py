from pathlib import Path

from inference_base import SDXLBaseGenerator, save_images as save_base_images


def run_pipeline() -> None:
    prompt = """
Korean tonkatsu pork cutlet, wide and flattened shape,
thick crispy panko crust, golden brown crunchy texture,
juicy pork meat visible inside, sliced cutlet,
tonkatsu sauce dripping on top, glossy sauce,

served on a clean white plate with shredded cabbage,

close-up shot, food filling the frame,
center composition, strong focus,

premium restaurant advertisement,
studio lighting, high contrast,
professional food photography, ultra realistic, 4k
"""

    negative_prompt = """
small pieces, round shape, croquette, fried balls,
dessert-like, snack, unrealistic shape,
blurry, low quality, flat lighting
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

    print("\n[Pipeline] Base generation done.")
    print("[Pipeline] Check outputs in backend/image_generator/outputs/")


if __name__ == "__main__":
    run_pipeline()