from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from image_generator.case1_sdxl import generate_image_sdxl_quality
from image_generator.case2_sdxl import generate_image_case2
from image_generator.case3_controlnet import generate_image_case3_controlnet

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
