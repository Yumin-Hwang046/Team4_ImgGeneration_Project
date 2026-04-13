from pathlib import Path
from typing import List

import torch
from diffusers import DiffusionPipeline
from PIL import Image


class SDXLRefinerGenerator:
    def __init__(self, model_id: str = "stabilityai/stable-diffusion-xl-refiner-1.0"):
        self.model_id = model_id
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.pipe = None

    def load(self) -> None:
        if self.pipe is not None:
            return

        print(f"[Refiner] Loading model: {self.model_id}")
        print(f"[Refiner] Using device: {self.device}")

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

    def refine(
        self,
        prompt: str,
        negative_prompt: str,
        images: List[Image.Image],
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
        strength: float = 0.3,
    ) -> List[Image.Image]:
        if self.pipe is None:
            self.load()

        print("[Refiner] Refining images...")

        refined_images: List[Image.Image] = []

        for idx, image in enumerate(images):
            result = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                image=image,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                strength=strength,
            )
            refined_image = result.images[0]
            refined_images.append(refined_image)
            print(f"[Refiner] Refined image {idx}")

        return refined_images


def save_images(images: List[Image.Image], output_dir: str, prefix: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for i, image in enumerate(images):
        save_path = output_path / f"{prefix}_{i}.png"
        image.save(save_path)
        print(f"[Refiner] Saved: {save_path}")