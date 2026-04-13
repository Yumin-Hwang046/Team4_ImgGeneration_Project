from diffusers import DiffusionPipeline
import torch
from pathlib import Path


def get_device():
    return "cuda" if torch.cuda.is_available() else "cpu"


class FluxGenerator:
    def __init__(self):
        self.device = get_device()
        self.pipe = None

    def load(self):
        if self.pipe is not None:
            return

        print(f"[FLUX] Loading model on {self.device}")

        self.pipe = DiffusionPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-dev",
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
        )

        self.pipe = self.pipe.to(self.device)

        # VRAM 절약
        self.pipe.enable_attention_slicing()

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        output_path: str = "outputs/flux_output.png",
        height: int = 768,
        width: int = 768,
        guidance_scale: float = 5.0,
        num_inference_steps: int = 30,
    ):
        if self.pipe is None:
            self.load()

        print("[FLUX] Generating image...")

        if self.device == "cuda":
            torch.cuda.empty_cache()

        image = self.pipe(
            prompt=prompt,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
            height=height,
            width=width,
        ).images[0]

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)

        print(f"[FLUX] Saved to {output_path}")


if __name__ == "__main__":
    prompt = """
Japanese tonkatsu pork cutlet,
crispy golden panko crust,
served on a white plate with shredded cabbage,
close-up food photography,
soft natural lighting,
high quality, realistic
"""

    generator = FluxGenerator()
    generator.generate(prompt)