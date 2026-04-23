import base64
import io
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

from image_generator.inference_base import SDXLBaseGenerator
from text_generator.generator import generate_marketing_copy

app = FastAPI()

_generator: Optional[SDXLBaseGenerator] = None


def _get_generator() -> SDXLBaseGenerator:
    global _generator
    if _generator is None:
        _generator = SDXLBaseGenerator()
        _generator.load()
    return _generator


class ImageRequest(BaseModel):
    prompt: str
    negative_prompt: str = (
        "egg, mushroom, strange food, mixed dishes, "
        "deformed, unrealistic, weird texture, blurry, low quality"
    )
    num_inference_steps: int = 25
    guidance_scale: float = 7.5
    height: int = 768
    width: int = 768


class TextRequest(BaseModel):
    purpose: str
    business_category: str
    menu_name: str
    location: str
    mood: Optional[str] = None
    weather_summary: str = ""
    season_context: str = ""
    recommended_concept: str = ""
    extra_prompt: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate-image")
def generate_image(req: ImageRequest):
    generator = _get_generator()
    images = generator.generate(
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        num_inference_steps=req.num_inference_steps,
        guidance_scale=req.guidance_scale,
        height=req.height,
        width=req.width,
    )
    buf = io.BytesIO()
    images[0].save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode()
    return {"image_base64": encoded, "prompt_used": req.prompt}


@app.post("/generate-text")
def generate_text(req: TextRequest):
    return generate_marketing_copy(
        purpose=req.purpose,
        business_category=req.business_category,
        menu_name=req.menu_name,
        location=req.location,
        mood=req.mood,
        weather_summary=req.weather_summary,
        season_context=req.season_context,
        recommended_concept=req.recommended_concept,
        extra_prompt=req.extra_prompt,
    )
