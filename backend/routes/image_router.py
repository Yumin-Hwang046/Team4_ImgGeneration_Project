import time
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from image_generator.case1_sdxl import generate_image_sdxl_quality
from image_generator.case2_sdxl import generate_image_case2
from image_generator.case3_controlnet import generate_image_case3_controlnet
from image_generator.case4_ip_adapter import generate_image_case4_ip_adapter
from observability import log_langfuse_trace, log_wandb

router = APIRouter(prefix="/image", tags=["image"])


class Case1Request(BaseModel):
    image_analysis_text: str
    mood_key: str
    format_type: str = "피드"


class Case2Request(BaseModel):
    user_prompt: str
    mood_key: Optional[str] = None
    format_type: str = "피드"
    user_reference_path: Optional[str] = None
    preset_key: Optional[str] = None
    strength: float = 0.6


class Case3Request(BaseModel):
    user_image_path: str
    user_prompt: str
    format_type: str = "피드"
    controlnet_scale: float = 0.8
    use_rembg: bool = True


class Case4Request(BaseModel):
    user_image_path: str
    reference_image_path: str
    user_prompt: str
    format_type: str = "피드"
    ip_adapter_scale: float = 0.7
    strength: float = 0.6
    output_name: Optional[str] = None
    output_subdir: Optional[str] = None


@router.post("/case1")
def case1(req: Case1Request):
    return generate_image_sdxl_quality(
        image_analysis_text=req.image_analysis_text,
        mood_key=req.mood_key,
        format_type=req.format_type,
    )


@router.post("/case2")
def case2(req: Case2Request):
    if not req.user_reference_path and not req.preset_key:
        raise HTTPException(status_code=400, detail="user_reference_path 또는 preset_key가 필요합니다.")
    return generate_image_case2(
        user_prompt=req.user_prompt,
        mood_key=req.mood_key,
        format_type=req.format_type,
        user_reference_path=req.user_reference_path,
        preset_key=req.preset_key,
        strength=req.strength,
    )


@router.post("/case3")
def case3(req: Case3Request):
    return generate_image_case3_controlnet(
        user_image_path=req.user_image_path,
        user_prompt=req.user_prompt,
        format_type=req.format_type,
        controlnet_scale=req.controlnet_scale,
        use_rembg=req.use_rembg,
    )


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
        log_wandb("case4.router", log_payload)
        log_langfuse_trace(
            name="case4.router",
            input=inputs,
            output=result,
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
        log_wandb("case4.router.error", err_payload)
        log_langfuse_trace(
            name="case4.router.error",
            input=inputs,
            output={"error_type": type(e).__name__, "error_message": str(e)},
            metadata={"duration_sec": duration},
            tags=["router", "case4", "error"],
        )
        raise
