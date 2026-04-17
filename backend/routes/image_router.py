from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

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


@router.post("/case4")
def case4(req: Case4Request):
    try:
        from image_generator.case4_ip_adapter import generate_image_case4_ip_adapter
    except ImportError as e:
        missing = getattr(e, "name", "dependency")
        raise HTTPException(
            status_code=503,
            detail=f"Case4 dependency is missing: {missing}. Install model dependencies first.",
        )

    return generate_image_case4_ip_adapter(
        user_image_path=req.user_image_path,
        reference_image_path=req.reference_image_path,
        user_prompt=req.user_prompt,
        format_type=req.format_type,
        ip_adapter_scale=req.ip_adapter_scale,
        strength=req.strength,
        output_name=req.output_name,
        output_subdir=req.output_subdir,
    )
