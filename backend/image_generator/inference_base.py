from pathlib import Path
from typing import List

import torch
from diffusers import DiffusionPipeline
from PIL import Image


class SDXLBaseGenerator:
    def __init__(self, model_id: str = "stabilityai/stable-diffusion-xl-base-1.0"):
        self.model_id = model_id
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.pipe = None

    def load(self) -> None:
        if self.pipe is not None:
            return

        print(f"[Base] Loading model: {self.model_id}")
        print(f"[Base] Using device: {self.device}")

        load_kwargs = {
            "torch_dtype": self.dtype,
            "use_safetensors": True,
        }
        if self.device == "cuda":
            load_kwargs["variant"] = "fp16"

        self.pipe = DiffusionPipeline.from_pretrained(
            self.model_id,
            **load_kwargs,
        )

        self.pipe = self.pipe.to(self.device)
        self.pipe.enable_attention_slicing()

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        num_images_per_prompt: int = 1,
        num_inference_steps: int = 25,
        guidance_scale: float = 7.5,
        height: int = 768,
        width: int = 768,
    ) -> List[Image.Image]:
        if self.pipe is None:
            self.load()

        print("[Base] Generating base images...")

        if self.device == "cuda":
            torch.cuda.empty_cache()

        result = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_images_per_prompt=num_images_per_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            height=height,
            width=width,
        )

        return result.images


def save_images(images: List[Image.Image], output_dir: str, prefix: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for i, image in enumerate(images):
        save_path = output_path / f"{prefix}_{i}.png"
        image.save(save_path)
        print(f"[Base] Saved: {save_path}")