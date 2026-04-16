import time
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from image_generator.case4_ip_adapter import generate_image_case4_ip_adapter
from image_generator.case5_inpaint_ip_adapter import generate_image_case5_inpaint_ip_adapter
from observability import log_langfuse_trace, log_wandb, to_langfuse_media, to_wandb_image

router = APIRouter(prefix="/image", tags=["image"])


class Case4Request(BaseModel):
    user_image_path: str
    reference_image_path: str
    user_prompt: str
    format_type: str = "피드"
    ip_adapter_scale: float = 0.7
    strength: float = 0.6
    output_name: Optional[str] = None
    output_subdir: Optional[str] = None


class Case5Request(BaseModel):
    user_image_path: str
    reference_image_path: str
    mask_image_path: str
    user_prompt: str
    format_type: str = "피드"
    ip_adapter_scale: float = 0.6
    strength: float = 0.35
    mask_invert: bool = False
    output_name: Optional[str] = None
    output_subdir: Optional[str] = None


@router.post("/case4")
def case4(req: Case4Request):
    request_id = uuid4().hex
    start_time = time.time()
    inputs = {
        "request_id": request_id,
        "case": "case4",
        "user_image_path": req.user_image_path,
        "reference_image_path": req.reference_image_path,
        "user_prompt": req.user_prompt,
        "format_type": req.format_type,
        "ip_adapter_scale": req.ip_adapter_scale,
        "strength": req.strength,
        "output_name": req.output_name,
        "output_subdir": req.output_subdir,
    }

    try:
        result = generate_image_case4_ip_adapter(
            user_image_path=req.user_image_path,
            reference_image_path=req.reference_image_path,
            user_prompt=req.user_prompt,
            format_type=req.format_type,
            ip_adapter_scale=req.ip_adapter_scale,
            strength=req.strength,
            output_name=req.output_name,
            output_subdir=req.output_subdir,
            request_id=request_id,
        )
        duration = time.time() - start_time
        log_payload = {
            **inputs,
            "duration_sec": duration,
            "output_path": result.get("path"),
            "output_url": result.get("url"),
        }
        wandb_images = {
            "input_user_image": to_wandb_image(req.user_image_path, "case4.input.user"),
            "input_reference_image": to_wandb_image(req.reference_image_path, "case4.input.reference"),
            "output_image": to_wandb_image(result.get("path", ""), "case4.output"),
        }
        log_wandb(
            "case4.router",
            {**log_payload, **{k: v for k, v in wandb_images.items() if v is not None}},
        )
        log_langfuse_trace(
            name="case4.router",
            input={
                **inputs,
                "user_image": to_langfuse_media(req.user_image_path),
                "reference_image": to_langfuse_media(req.reference_image_path),
            },
            output={
                **result,
                "output_image": to_langfuse_media(result.get("path", "")),
            },
            metadata={"duration_sec": duration},
            tags=["router", "case4"],
        )
        return result
    except Exception as e:
        duration = time.time() - start_time
        err_payload = {
            **inputs,
            "duration_sec": duration,
            "error_type": type(e).__name__,
            "error_message": str(e),
        }
        wandb_images = {
            "input_user_image": to_wandb_image(req.user_image_path, "case4.error.input.user"),
            "input_reference_image": to_wandb_image(req.reference_image_path, "case4.error.input.reference"),
        }
        log_wandb(
            "case4.router.error",
            {**err_payload, **{k: v for k, v in wandb_images.items() if v is not None}},
        )
        log_langfuse_trace(
            name="case4.router.error",
            input={
                **inputs,
                "user_image": to_langfuse_media(req.user_image_path),
                "reference_image": to_langfuse_media(req.reference_image_path),
            },
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": duration},
            tags=["router", "case4", "error"],
        )
        raise


@router.post("/case5")
def case5(req: Case5Request):
    request_id = uuid4().hex
    start_time = time.time()
    inputs = {
        "request_id": request_id,
        "case": "case5",
        "user_image_path": req.user_image_path,
        "reference_image_path": req.reference_image_path,
        "mask_image_path": req.mask_image_path,
        "user_prompt": req.user_prompt,
        "format_type": req.format_type,
        "ip_adapter_scale": req.ip_adapter_scale,
        "strength": req.strength,
        "mask_invert": req.mask_invert,
        "output_name": req.output_name,
        "output_subdir": req.output_subdir,
    }

    try:
        result = generate_image_case5_inpaint_ip_adapter(
            user_image_path=req.user_image_path,
            reference_image_path=req.reference_image_path,
            mask_image_path=req.mask_image_path,
            user_prompt=req.user_prompt,
            format_type=req.format_type,
            ip_adapter_scale=req.ip_adapter_scale,
            strength=req.strength,
            mask_invert=req.mask_invert,
            output_name=req.output_name,
            output_subdir=req.output_subdir,
            request_id=request_id,
        )
        duration = time.time() - start_time
        log_payload = {
            **inputs,
            "duration_sec": duration,
            "output_path": result.get("path"),
            "output_url": result.get("url"),
        }
        wandb_images = {
            "input_user_image": to_wandb_image(req.user_image_path, "case5.input.user"),
            "input_reference_image": to_wandb_image(req.reference_image_path, "case5.input.reference"),
            "input_mask_image": to_wandb_image(req.mask_image_path, "case5.input.mask"),
            "output_image": to_wandb_image(result.get("path", ""), "case5.output"),
        }
        log_wandb(
            "case5.router",
            {**log_payload, **{k: v for k, v in wandb_images.items() if v is not None}},
        )
        log_langfuse_trace(
            name="case5.router",
            input={
                **inputs,
                "user_image": to_langfuse_media(req.user_image_path),
                "reference_image": to_langfuse_media(req.reference_image_path),
                "mask_image": to_langfuse_media(req.mask_image_path),
            },
            output={
                **result,
                "output_image": to_langfuse_media(result.get("path", "")),
            },
            metadata={"duration_sec": duration},
            tags=["router", "case5"],
        )
        return result
    except Exception as e:
        duration = time.time() - start_time
        err_payload = {
            **inputs,
            "duration_sec": duration,
            "error_type": type(e).__name__,
            "error_message": str(e),
        }
        wandb_images = {
            "input_user_image": to_wandb_image(req.user_image_path, "case5.error.input.user"),
            "input_reference_image": to_wandb_image(req.reference_image_path, "case5.error.input.reference"),
            "input_mask_image": to_wandb_image(req.mask_image_path, "case5.error.input.mask"),
        }
        log_wandb(
            "case5.router.error",
            {**err_payload, **{k: v for k, v in wandb_images.items() if v is not None}},
        )
        log_langfuse_trace(
            name="case5.router.error",
            input={
                **inputs,
                "user_image": to_langfuse_media(req.user_image_path),
                "reference_image": to_langfuse_media(req.reference_image_path),
                "mask_image": to_langfuse_media(req.mask_image_path),
            },
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": duration},
            tags=["router", "case5", "error"],
        )
        raise
