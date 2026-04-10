from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from image_generator.case4_ip_adapter import generate_image_case4_ip_adapter

router = APIRouter(prefix="/image", tags=["image"])


class Case4Request(BaseModel):
    user_image_path: str
    reference_image_path: str
    user_prompt: str
    format_type: str = "피드"
    ip_adapter_scale: float = 0.7
    strength: float = 0.6
    output_name: Optional[str] = None


@router.post("/case4")
def case4(req: Case4Request):
    return generate_image_case4_ip_adapter(
        user_image_path=req.user_image_path,
        reference_image_path=req.reference_image_path,
        user_prompt=req.user_prompt,
        format_type=req.format_type,
        ip_adapter_scale=req.ip_adapter_scale,
        strength=req.strength,
        output_name=req.output_name,
    )
