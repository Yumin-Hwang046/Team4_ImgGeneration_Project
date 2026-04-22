from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import safetensors.torch as sf
import torch
from PIL import Image
from diffusers import (
    AutoencoderKL,
    DPMSolverMultistepScheduler,
    StableDiffusionImg2ImgPipeline,
    StableDiffusionPipeline,
    UNet2DConditionModel,
)
from huggingface_hub import hf_hub_download
from transformers import CLIPTextModel, CLIPTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observability import build_langfuse_media_list, log_langfuse_trace, to_langfuse_media

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FG = PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "exp1_rembg" / "input_음료_no_bg.png"
DEFAULT_BG = PROJECT_ROOT / "assets" / "presets" / "warm" / "3_bg.webp"
DEFAULT_OUT = PROJECT_ROOT / "generated" / "merged" / "ic_light_exp1" / "drink_on_3_bg.png"
DEFAULT_BATCH_OUT_DIR = PROJECT_ROOT / "generated" / "merged" / "exp11"

BASE_MODEL = "stablediffusionapi/realistic-vision-v51"
IC_LIGHT_REPO = "lllyasviel/ic-light"
IC_LIGHT_MODEL = "iclight_sd15_fbc.safetensors"


@dataclass(frozen=True)
class Case:
    foreground: Path
    background: Path
    output_name: str
    prompt: str


DEFAULT_CASES = [
    Case(
        foreground=PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "exp1_rembg" / "input_와플_no_bg.png",
        background=PROJECT_ROOT / "assets" / "presets" / "warm" / "1_dish_bg.png",
        output_name="waffle_on_1_dish_bg.png",
        prompt="realistic waffle dessert plated at the center of a cafe table, natural perspective, soft cafe lighting, photorealistic food photography",
    ),
    Case(
        foreground=PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "exp1_rembg" / "input_음료_no_bg.png",
        background=PROJECT_ROOT / "assets" / "presets" / "warm" / "3_bg.webp",
        output_name="drink_on_3_bg.png",
        prompt="realistic iced cafe drink on a table, front-facing eye-level product photo, soft daylight, photorealistic",
    ),
    Case(
        foreground=PROJECT_ROOT / "generated" / "removed_bg" / "exp1_rembg" / "exp1_rembg" / "input_케이크_no_bg.png",
        background=PROJECT_ROOT / "assets" / "presets" / "warm" / "4_bg.webp",
        output_name="cake_on_4_bg.png",
        prompt="realistic slice of cake on a cafe table at the lower right, natural cafe lighting, photorealistic dessert photography",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IC-Light background-conditioned test with removed_bg inputs.")
    parser.add_argument("--foreground", type=Path, default=DEFAULT_FG)
    parser.add_argument("--background", type=Path, default=DEFAULT_BG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--prompt", default="iced cafe drink on a table, front-facing eye-level product photo, photorealistic, soft daylight")
    parser.add_argument("--negative-prompt", default="lowres, blurry, bad anatomy, duplicate object, deformed, worst quality")
    parser.add_argument("--width", type=int, default=384)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--steps", type=int, default=12)
    parser.add_argument("--cfg", type=float, default=7.0)
    parser.add_argument("--highres-scale", type=float, default=1.5)
    parser.add_argument("--highres-denoise", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--batch-defaults", action="store_true", help="Run the 3 predefined removed_bg cases into --output-dir.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_BATCH_OUT_DIR)
    return parser.parse_args()


def resolve_device() -> tuple[torch.device, torch.dtype]:
    if torch.cuda.is_available():
        return torch.device("cuda"), torch.float16
    return torch.device("cpu"), torch.float32


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
    cropped_image = resized_image.crop((left, top, right, bottom))
    return np.array(cropped_image)


def resize_without_crop(image: np.ndarray, target_width: int, target_height: int) -> np.ndarray:
    return np.array(Image.fromarray(image).resize((target_width, target_height), Image.LANCZOS))


def numpy2pytorch(imgs: list[np.ndarray], device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    tensor = torch.from_numpy(np.stack(imgs, axis=0)).float() / 127.0 - 1.0
    tensor = tensor.movedim(-1, 1)
    return tensor.to(device=device, dtype=dtype)


def pytorch2numpy(imgs: torch.Tensor, quant: bool = True) -> list[np.ndarray]:
    results: list[np.ndarray] = []
    for x in imgs:
        y = x.movedim(0, -1)
        if quant:
            y = y * 127.5 + 127.5
            y = y.detach().float().cpu().numpy().clip(0, 255).astype(np.uint8)
        else:
            y = y * 0.5 + 0.5
            y = y.detach().float().cpu().numpy().clip(0, 1).astype(np.float32)
        results.append(y)
    return results


def load_foreground_as_rgb(path: Path) -> np.ndarray:
    rgba = np.array(Image.open(path).convert("RGBA"))
    alpha = rgba[..., 3:4].astype(np.float32) / 255.0
    rgb = rgba[..., :3].astype(np.float32)
    neutral = np.full_like(rgb, 127.0)
    # IC-Light foreground conditioning expects removed areas to be neutral gray.
    merged = neutral + (rgb - neutral) * alpha
    return merged.clip(0, 255).astype(np.uint8)


def load_background(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"))


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


def build_pipelines(device: torch.device, dtype: torch.dtype):
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
    t2i_pipe.set_progress_bar_config(disable=False)
    i2i_pipe.set_progress_bar_config(disable=False)
    t2i_pipe.enable_attention_slicing()
    i2i_pipe.enable_attention_slicing()
    return tokenizer, text_encoder, vae, unet, t2i_pipe, i2i_pipe


@torch.inference_mode()
def run_single_case(
    *,
    foreground: Path,
    background: Path,
    output: Path,
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    steps: int,
    cfg: float,
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
    fg = load_foreground_as_rgb(foreground)
    bg = load_background(background)

    fg_small = resize_and_center_crop(fg, width, height)
    bg_small = resize_and_center_crop(bg, width, height)

    concat_conds = numpy2pytorch([fg_small, bg_small], device=vae.device, dtype=vae.dtype)
    concat_conds = vae.encode(concat_conds).latent_dist.mode() * vae.config.scaling_factor
    concat_conds = torch.cat([part[None, ...] for part in concat_conds], dim=1)

    conds, unconds = encode_prompt_pair(
        positive_prompt=f"{prompt}, best quality",
        negative_prompt=negative_prompt,
        tokenizer=tokenizer,
        text_encoder=text_encoder,
        device=device,
    )

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
        guidance_scale=cfg,
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

    fg_hr = resize_and_center_crop(fg, upscale_w, upscale_h)
    bg_hr = resize_and_center_crop(bg, upscale_w, upscale_h)
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
        guidance_scale=cfg,
        cross_attention_kwargs={"concat_conds": concat_conds},
    ).images.to(vae.dtype) / vae.config.scaling_factor

    result = vae.decode(latents).sample
    result_image = pytorch2numpy(result)[0]

    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(result_image).save(output)
    return output


@torch.inference_mode()
def run_ic_light(args: argparse.Namespace) -> list[Path]:
    device, dtype = resolve_device()
    print(f"device={device} dtype={dtype}")

    tokenizer, text_encoder, vae, unet, t2i_pipe, i2i_pipe = build_pipelines(device, dtype)

    if args.batch_defaults:
        outputs: list[Path] = []
        for index, case in enumerate(DEFAULT_CASES):
            output = args.output_dir / case.output_name
            print(f"running {case.foreground.name} -> {output.name}")
            outputs.append(
                run_single_case(
                    foreground=case.foreground,
                    background=case.background,
                    output=output,
                    prompt=case.prompt,
                    negative_prompt=args.negative_prompt,
                    width=args.width,
                    height=args.height,
                    steps=args.steps,
                    cfg=args.cfg,
                    highres_scale=args.highres_scale,
                    highres_denoise=args.highres_denoise,
                    seed=args.seed + index,
                    device=device,
                    tokenizer=tokenizer,
                    text_encoder=text_encoder,
                    vae=vae,
                    unet=unet,
                    t2i_pipe=t2i_pipe,
                    i2i_pipe=i2i_pipe,
                )
            )
        return outputs

    return [
        run_single_case(
            foreground=args.foreground,
            background=args.background,
            output=args.output,
            prompt=args.prompt,
            negative_prompt=args.negative_prompt,
            width=args.width,
            height=args.height,
            steps=args.steps,
            cfg=args.cfg,
            highres_scale=args.highres_scale,
            highres_denoise=args.highres_denoise,
            seed=args.seed,
            device=device,
            tokenizer=tokenizer,
            text_encoder=text_encoder,
            vae=vae,
            unet=unet,
            t2i_pipe=t2i_pipe,
            i2i_pipe=i2i_pipe,
        )
    ]


def main() -> None:
    args = parse_args()
    start_time = time.time()
    try:
        output_paths = run_ic_light(args)
        for output_path in output_paths:
            print(f"saved {output_path}")
        log_langfuse_trace(
            name="image_generator.ic_light_removed_bg_test",
            input={
                "args": vars(args),
                "foreground": to_langfuse_media(str(args.foreground)),
                "background": to_langfuse_media(str(args.background)),
            },
            output={"saved_paths": [str(path) for path in output_paths], "output_images": build_langfuse_media_list([str(path) for path in output_paths])},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "ic-light", "removed-bg"],
        )
    except Exception as e:
        log_langfuse_trace(
            name="image_generator.ic_light_removed_bg_test.error",
            input={"args": vars(args)},
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": time.time() - start_time},
            tags=["image_generator", "experiment", "ic-light", "removed-bg", "error"],
        )
        raise


if __name__ == "__main__":
    main()
