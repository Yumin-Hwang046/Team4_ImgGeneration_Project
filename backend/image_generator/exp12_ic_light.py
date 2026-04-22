from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import safetensors.torch as sf
import torch
from diffusers import (
    AutoencoderKL,
    DPMSolverMultistepScheduler,
    StableDiffusionImg2ImgPipeline,
    StableDiffusionPipeline,
    UNet2DConditionModel,
)
from huggingface_hub import hf_hub_download
from PIL import Image, ImageFilter
from transformers import CLIPTextModel, CLIPTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observability import build_langfuse_media_list, log_langfuse_trace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp12"
BASE_MODEL = "stablediffusionapi/realistic-vision-v51"
IC_LIGHT_REPO = "lllyasviel/ic-light"
IC_LIGHT_MODEL = "iclight_sd15_fbc.safetensors"
FRAME_SIZE = 768

JOBS = [
    {
        "name": "waffle_on_1_dish_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "1_dish_bg.png",
        "object_scale": 1.46,
        "anchor_x": 0.50,
        "anchor_y": 0.47,
        "bg_scale": 1.22,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.48,
        "prompt": (
            "A realistic waffle dessert centered on the plate in the middle of the frame, "
            "preserve the waffle exactly, natural centered plating, grounded on the dish surface, "
            "soft natural shadow, premium bakery advertising, photorealistic."
        ),
    },
    {
        "name": "waffle_on_2_dish_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_와플_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "2_dish_bg.png",
        "object_scale": 1.34,
        "anchor_x": 0.50,
        "anchor_y": 0.78,
        "bg_scale": 1.40,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.68,
        "prompt": (
            "A realistic waffle dessert placed on the lower dish area, preserve the waffle exactly, "
            "slightly smaller than a poster crop, clearly resting on the plate, "
            "rich bakery mood, realistic tabletop contact, photorealistic."
        ),
    },
    {
        "name": "drink_on_3_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_음료_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "3_bg.webp",
        "object_scale": 1.08,
        "anchor_x": 0.50,
        "anchor_y": 0.56,
        "bg_scale": 1.18,
        "bg_focus_x": 0.50,
        "bg_focus_y": 0.50,
        "prompt": (
            "A realistic drink shown fully in frame, preserve the drink exactly, "
            "slightly smaller subject so the whole cup is visible, front-facing eye-level beverage shot, "
            "not top-down, natural cafe perspective, premium beverage advertising, photorealistic."
        ),
    },
    {
        "name": "cake_on_4_bg",
        "object": PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "input_케이크_no_bg.png",
        "background": PROJECT_ROOT / "assets" / "presets" / "warm" / "4_bg.webp",
        "object_scale": 0.68,
        "anchor_x": 0.73,
        "anchor_y": 0.76,
        "bg_scale": 1.34,
        "bg_focus_x": 0.60,
        "bg_focus_y": 0.62,
        "prompt": (
            "A realistic cake placed in the lower right of the frame, preserve the cake exactly, "
            "intentional asymmetrical composition, grounded on the tabletop plane, "
            "soft directional shadow, premium dessert photography, photorealistic."
        ),
    },
]

NEGATIVE_PROMPT = (
    "deformed food, extra food, duplicate object, floating object, disconnected shadow, "
    "cartoon, illustration, blurry, low quality, bad crop, distorted perspective, "
    "top-down shot, overhead angle, cropped cup, clipped drink"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose exp12 images with exp9 layout and IC-Light background conditioning.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--steps", type=int, default=18)
    parser.add_argument("--guidance", type=float, default=6.5)
    parser.add_argument("--width", type=int, default=384)
    parser.add_argument("--height", type=int, default=384)
    parser.add_argument("--highres-scale", type=float, default=1.25)
    parser.add_argument("--highres-denoise", type=float, default=0.5)
    return parser.parse_args()


def prepare_background(image: Image.Image, bg_scale: float, focus_x: float, focus_y: float) -> Image.Image:
    width, height = image.size
    scale = max((FRAME_SIZE / width), (FRAME_SIZE / height)) * bg_scale
    resized = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
    rw, rh = resized.size
    center_x = int(rw * focus_x)
    center_y = int(rh * focus_y)
    left = max(0, min(rw - FRAME_SIZE, center_x - FRAME_SIZE // 2))
    top = max(0, min(rh - FRAME_SIZE, center_y - FRAME_SIZE // 2))
    return resized.crop((left, top, left + FRAME_SIZE, top + FRAME_SIZE))


def resolve_existing_path(path: Path) -> Path:
    if path.exists():
        return path
    nested_candidate = path.parent / "exp1_rembg" / path.name
    if nested_candidate.exists():
        return nested_candidate
    raise FileNotFoundError(path)


def fit_object(obj: Image.Image, frame_size: int, object_scale: float) -> Image.Image:
    ow, oh = obj.size
    ratio = min((frame_size * object_scale) / ow, (frame_size * object_scale) / oh)
    return obj.resize((max(1, int(ow * ratio)), max(1, int(oh * ratio))), Image.Resampling.LANCZOS)


def build_initial_composite(job: dict[str, object]) -> Image.Image:
    bg = prepare_background(
        Image.open(Path(job["background"])).convert("RGB"),
        float(job["bg_scale"]),
        float(job["bg_focus_x"]),
        float(job["bg_focus_y"]),
    )
    obj = fit_object(
        Image.open(Path(job["object"])).convert("RGBA"),
        FRAME_SIZE,
        float(job["object_scale"]),
    )

    frame = bg.convert("RGBA")
    ow, oh = obj.size
    cx = int(FRAME_SIZE * float(job["anchor_x"]))
    cy = int(FRAME_SIZE * float(job["anchor_y"]))
    x = max(0, min(FRAME_SIZE - ow, cx - ow // 2))
    y = max(0, min(FRAME_SIZE - oh, cy - oh // 2))

    alpha = obj.getchannel("A")
    shadow = alpha.filter(ImageFilter.GaussianBlur(radius=max(18, oh // 18)))
    shadow_layer = Image.new("RGBA", obj.size, (0, 0, 0, 0))
    shadow_layer.putalpha(shadow.point(lambda v: int(v * 0.25)))
    frame.alpha_composite(shadow_layer, (x, min(FRAME_SIZE - oh, y + max(10, oh // 20))))
    frame.alpha_composite(obj, (x, y))
    return frame.convert("RGB")


def load_foreground_as_rgb(path: Path) -> Image.Image:
    rgba = np.array(Image.open(path).convert("RGBA"))
    alpha = rgba[..., 3:4].astype(np.float32) / 255.0
    rgb = rgba[..., :3].astype(np.float32)
    neutral = np.full_like(rgb, 127.0)
    merged = neutral + (rgb - neutral) * alpha
    return Image.fromarray(merged.clip(0, 255).astype(np.uint8))


def resize_and_center_crop(image: np.ndarray, target_width: int, target_height: int) -> np.ndarray:
    pil_image = Image.fromarray(image)
    original_width, original_height = pil_image.size
    scale_factor = max(target_width / original_width, target_height / original_height)
    resized_width = int(round(original_width * scale_factor))
    resized_height = int(round(original_height * scale_factor))
    resized_image = pil_image.resize((resized_width, resized_height), Image.LANCZOS)
    left = (resized_width - target_width) / 2
    top = (resized_height - target_height) / 2
    right = (resized_width + target_width) / 2
    bottom = (resized_height + target_height) / 2
    return np.array(resized_image.crop((left, top, right, bottom)))


def resize_without_crop(image: np.ndarray, target_width: int, target_height: int) -> np.ndarray:
    return np.array(Image.fromarray(image).resize((target_width, target_height), Image.LANCZOS))


def numpy2pytorch(imgs: list[np.ndarray], device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    tensor = torch.from_numpy(np.stack(imgs, axis=0)).float() / 127.0 - 1.0
    tensor = tensor.movedim(-1, 1)
    return tensor.to(device=device, dtype=dtype)


def pytorch2numpy(imgs: torch.Tensor) -> list[np.ndarray]:
    results: list[np.ndarray] = []
    for image in imgs:
        array = image.movedim(0, -1)
        array = array * 127.5 + 127.5
        results.append(array.detach().float().cpu().numpy().clip(0, 255).astype(np.uint8))
    return results


def encode_prompt_inner(text: str, tokenizer: CLIPTokenizer, text_encoder: CLIPTextModel, device: torch.device) -> torch.Tensor:
    max_length = tokenizer.model_max_length
    chunk_length = max_length - 2
    id_start = tokenizer.bos_token_id
    id_end = tokenizer.eos_token_id
    id_pad = id_end

    def pad(tokens: list[int], token_id: int, size: int) -> list[int]:
        return tokens[:size] if len(tokens) >= size else tokens + [token_id] * (size - len(tokens))

    tokens = tokenizer(text, truncation=False, add_special_tokens=False)["input_ids"]
    chunks = [[id_start] + tokens[i:i + chunk_length] + [id_end] for i in range(0, len(tokens), chunk_length)]
    chunks = [pad(chunk, id_pad, max_length) for chunk in chunks]
    token_ids = torch.tensor(chunks).to(device=device, dtype=torch.int64)
    return text_encoder(token_ids).last_hidden_state


def encode_prompt_pair(
    positive_prompt: str,
    negative_prompt: str,
    tokenizer: CLIPTokenizer,
    text_encoder: CLIPTextModel,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    cond = encode_prompt_inner(positive_prompt, tokenizer, text_encoder, device)
    uncond = encode_prompt_inner(negative_prompt, tokenizer, text_encoder, device)
    max_chunk = max(len(cond), len(uncond))
    cond = torch.cat([cond] * int(np.ceil(max_chunk / len(cond))), dim=0)[:max_chunk]
    uncond = torch.cat([uncond] * int(np.ceil(max_chunk / len(uncond))), dim=0)[:max_chunk]
    cond = torch.cat([part[None, ...] for part in cond], dim=1)
    uncond = torch.cat([part[None, ...] for part in uncond], dim=1)
    return cond, uncond


def build_pipelines():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.float16 if device.type == "cuda" else torch.float32

    tokenizer = CLIPTokenizer.from_pretrained(BASE_MODEL, subfolder="tokenizer")
    text_encoder = CLIPTextModel.from_pretrained(BASE_MODEL, subfolder="text_encoder", torch_dtype=dtype)
    vae = AutoencoderKL.from_pretrained(BASE_MODEL, subfolder="vae", torch_dtype=dtype)
    unet = UNet2DConditionModel.from_pretrained(BASE_MODEL, subfolder="unet", torch_dtype=dtype)

    with torch.no_grad():
        new_conv_in = torch.nn.Conv2d(
            12,
            unet.conv_in.out_channels,
            unet.conv_in.kernel_size,
            unet.conv_in.stride,
            unet.conv_in.padding,
        )
        new_conv_in.weight.zero_()
        new_conv_in.weight[:, :4, :, :].copy_(unet.conv_in.weight)
        new_conv_in.bias = unet.conv_in.bias
        unet.conv_in = new_conv_in

    unet_original_forward = unet.forward

    def hooked_unet_forward(sample, timestep, encoder_hidden_states, **kwargs):
        cross_attention_kwargs = kwargs.get("cross_attention_kwargs") or {}
        concat_conds = cross_attention_kwargs["concat_conds"].to(sample)
        concat_conds = torch.cat([concat_conds] * (sample.shape[0] // concat_conds.shape[0]), dim=0)
        kwargs["cross_attention_kwargs"] = {}
        return unet_original_forward(
            torch.cat([sample, concat_conds], dim=1),
            timestep,
            encoder_hidden_states,
            **kwargs,
        )

    unet.forward = hooked_unet_forward

    offset_path = hf_hub_download(repo_id=IC_LIGHT_REPO, filename=IC_LIGHT_MODEL)
    offset_state = sf.load_file(offset_path)
    origin_state = unet.state_dict()
    merged_state = {key: origin_state[key] + offset_state[key] for key in origin_state.keys()}
    unet.load_state_dict(merged_state, strict=True)

    scheduler = DPMSolverMultistepScheduler(
        num_train_timesteps=1000,
        beta_start=0.00085,
        beta_end=0.012,
        algorithm_type="sde-dpmsolver++",
        use_karras_sigmas=True,
        steps_offset=1,
    )

    text_encoder = text_encoder.to(device=device, dtype=dtype)
    vae = vae.to(device=device, dtype=dtype)
    unet = unet.to(device=device, dtype=dtype)

    t2i_pipe = StableDiffusionPipeline(
        vae=vae,
        text_encoder=text_encoder,
        tokenizer=tokenizer,
        unet=unet,
        scheduler=scheduler,
        safety_checker=None,
        requires_safety_checker=False,
        feature_extractor=None,
        image_encoder=None,
    )
    i2i_pipe = StableDiffusionImg2ImgPipeline(
        vae=vae,
        text_encoder=text_encoder,
        tokenizer=tokenizer,
        unet=unet,
        scheduler=scheduler,
        safety_checker=None,
        requires_safety_checker=False,
        feature_extractor=None,
        image_encoder=None,
    )
    t2i_pipe.enable_attention_slicing()
    i2i_pipe.enable_attention_slicing()
    t2i_pipe.set_progress_bar_config(disable=False)
    i2i_pipe.set_progress_bar_config(disable=False)
    return device, tokenizer, text_encoder, vae, unet, t2i_pipe, i2i_pipe


def run_job(
    *,
    job: dict[str, object],
    output_dir: Path,
    steps: int,
    guidance: float,
    width: int,
    height: int,
    highres_scale: float,
    highres_denoise: float,
    seed: int,
    device: torch.device,
    tokenizer: CLIPTokenizer,
    text_encoder: CLIPTextModel,
    vae: AutoencoderKL,
    unet: UNet2DConditionModel,
    t2i_pipe: StableDiffusionPipeline,
    i2i_pipe: StableDiffusionImg2ImgPipeline,
) -> Path:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    foreground = np.array(load_foreground_as_rgb(resolve_existing_path(Path(job["object"]))).convert("RGB"))
    background = np.array(prepare_background(
        Image.open(resolve_existing_path(Path(job["background"]))).convert("RGB"),
        float(job["bg_scale"]),
        float(job["bg_focus_x"]),
        float(job["bg_focus_y"]),
    ))

    prompt = f"{job['prompt']}, best quality"
    conds, unconds = encode_prompt_pair(prompt, NEGATIVE_PROMPT, tokenizer, text_encoder, device)

    fg_small = resize_and_center_crop(foreground, width, height)
    bg_small = resize_and_center_crop(background, width, height)
    concat_conds = numpy2pytorch([fg_small, bg_small], device=vae.device, dtype=vae.dtype)
    concat_conds = vae.encode(concat_conds).latent_dist.mode() * vae.config.scaling_factor
    concat_conds = torch.cat([part[None, ...] for part in concat_conds], dim=1)

    generator = torch.Generator(device=device.type).manual_seed(seed)
    latents = t2i_pipe(
        prompt_embeds=conds,
        negative_prompt_embeds=unconds,
        width=width,
        height=height,
        num_inference_steps=steps,
        num_images_per_prompt=1,
        generator=generator,
        output_type="latent",
        guidance_scale=guidance,
        cross_attention_kwargs={"concat_conds": concat_conds},
    ).images.to(vae.dtype) / vae.config.scaling_factor

    pixels = vae.decode(latents).sample
    pixels = pytorch2numpy(pixels)
    upscale_w = int(round(width * highres_scale / 64.0) * 64)
    upscale_h = int(round(height * highres_scale / 64.0) * 64)
    pixels = [resize_without_crop(image, upscale_w, upscale_h) for image in pixels]

    pixels_t = numpy2pytorch(pixels, device=vae.device, dtype=vae.dtype)
    latents = vae.encode(pixels_t).latent_dist.mode() * vae.config.scaling_factor
    latents = latents.to(device=unet.device, dtype=unet.dtype)

    fg_hr = resize_and_center_crop(foreground, upscale_w, upscale_h)
    bg_hr = resize_and_center_crop(background, upscale_w, upscale_h)
    concat_conds = numpy2pytorch([fg_hr, bg_hr], device=vae.device, dtype=vae.dtype)
    concat_conds = vae.encode(concat_conds).latent_dist.mode() * vae.config.scaling_factor
    concat_conds = torch.cat([part[None, ...] for part in concat_conds], dim=1)

    latents = i2i_pipe(
        image=latents,
        strength=highres_denoise,
        prompt_embeds=conds,
        negative_prompt_embeds=unconds,
        width=upscale_w,
        height=upscale_h,
        num_inference_steps=max(steps, int(round(steps / highres_denoise))),
        num_images_per_prompt=1,
        generator=generator,
        output_type="latent",
        guidance_scale=guidance,
        cross_attention_kwargs={"concat_conds": concat_conds},
    ).images.to(vae.dtype) / vae.config.scaling_factor

    result = vae.decode(latents).sample
    image = Image.fromarray(pytorch2numpy(result)[0]).resize((FRAME_SIZE, FRAME_SIZE), Image.Resampling.LANCZOS)

    del foreground, background, fg_small, bg_small, fg_hr, bg_hr, concat_conds, conds, unconds, latents, result, pixels, pixels_t
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{job['name']}.png"
    image.save(output_path)
    print(f"saved {output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    start_time = time.time()
    try:
        device, tokenizer, text_encoder, vae, unet, t2i_pipe, i2i_pipe = build_pipelines()
        print(f"device={device}")
        outputs = []
        for idx, job in enumerate(JOBS):
            outputs.append(
                run_job(
                    job=job,
                    output_dir=args.output_dir,
                    steps=args.steps,
                    guidance=args.guidance,
                    width=args.width,
                    height=args.height,
                    highres_scale=args.highres_scale,
                    highres_denoise=args.highres_denoise,
                    seed=900 + idx,
                    device=device,
                    tokenizer=tokenizer,
                    text_encoder=text_encoder,
                    vae=vae,
                    unet=unet,
                    t2i_pipe=t2i_pipe,
                    i2i_pipe=i2i_pipe,
                )
            )
        log_langfuse_trace(
            name="image_generator.exp12_ic_light",
            input={"args": vars(args), "jobs": [{k: str(v) if isinstance(v, Path) else v for k, v in job.items()} for job in JOBS]},
            output={"saved_paths": [str(path) for path in outputs], "output_images": build_langfuse_media_list([str(path) for path in outputs])},
            metadata={"duration_sec": time.time() - start_time, "device": str(device)},
            tags=["image_generator", "experiment", "exp12", "ic-light"],
        )
    except Exception as e:
        log_langfuse_trace(
            name="image_generator.exp12_ic_light.error",
            input={"args": vars(args)},
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "exp12", "ic-light", "error"],
        )
        raise


if __name__ == "__main__":
    main()
