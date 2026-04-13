from fastapi import APIRouter
from pydantic import BaseModel

from text_generator.generator import generate_ad_copy

router = APIRouter(prefix="/text", tags=["text"])


class TextRequest(BaseModel):
    image_analysis_text: str
    mood_key: str


@router.post("/generate")
def generate_text(req: TextRequest):
    return generate_ad_copy(
        image_analysis_text=req.image_analysis_text,
        mood_key=req.mood_key,
    )
