import argparse
import base64
import io
import sys
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from image_generator.merge_with_sdxl_base_구도보완 import load_pipeline, run_job
from text_generator.generator import generate_marketing_copy

import torch

app = FastAPI()


_compose_pipe = None
_rembg_session = None


@app.on_event("startup")
def startup_event():
    global _compose_pipe, _rembg_session
    print("[Startup] Loading compose pipeline (ControlNet + IP-Adapter)...")
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    try:
        _compose_pipe = load_pipeline()
        print("[Startup] Compose pipeline ready.")
    except Exception as e:
        import traceback
        print(f"[Startup] FAILED to load pipeline: {e}")
        traceback.print_exc()
        _compose_pipe = None
        print("[Startup] Server will run without image generation pipeline.")

    try:
        from rembg import new_session
        _rembg_session = new_session(providers=["CPUExecutionProvider"])
        print("[Startup] rembg session ready (CPU).")
    except Exception as e:
        print(f"[Startup] rembg session failed: {e}")


class ImageRequest(BaseModel):
    prompt: str
    negative_prompt: str = (
        "egg, mushroom, strange food, mixed dishes, "
        "deformed, unrealistic, weird texture, blurry, low quality"
    )
    num_inference_steps: int = 20
    guidance_scale: float = 6.5
    product_image_base64: str
    reference_image_base64: str
    background_id: str = "1_dish_bg"  # LAYOUT_PRESETS 키
    strength: float = 0.35
    ip_scale: float = 0.5
    control_scale: float = 0.7
    shadow_darkness: float = 0.35
    shadow_opacity: float = 0.8


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
    from fastapi import HTTPException
    from PIL import Image as PilImage
    from rembg import remove as rembg_remove

    if _compose_pipe is None:
        raise HTTPException(status_code=503, detail="Image generation pipeline not loaded")

    product_bytes = base64.b64decode(req.product_image_base64)
    reference_bytes = base64.b64decode(req.reference_image_base64)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        product_img = PilImage.open(io.BytesIO(product_bytes)).convert("RGBA")
        print("[Compose] Removing background...")
        no_bg_img = rembg_remove(product_img, session=_rembg_session)
        no_bg_path = tmpdir_path / "product_no_bg.png"
        no_bg_img.save(no_bg_path)

        # 파일명 stem이 LAYOUT_PRESETS 키와 일치해야 좌표 프리셋이 적용됨
        reference_path = tmpdir_path / f"{req.background_id}.png"
        PilImage.open(io.BytesIO(reference_bytes)).convert("RGB").save(reference_path)

        args = argparse.Namespace(
            steps=req.num_inference_steps,
            guidance=req.guidance_scale,
            strength=req.strength,
            ip_scale=req.ip_scale,
            control_scale=req.control_scale,
            shadow_darkness=req.shadow_darkness,
            shadow_opacity=req.shadow_opacity,
        )
        job = {
            "name": "compose",
            "object": str(no_bg_path),
            "background": str(reference_path),
            "prompt": req.prompt,
        }
        output_dir = tmpdir_path / "output"

        print("[Compose] Running run_job...")
        output_path = run_job(_compose_pipe, job, output_dir, args)
        result_bytes = Path(output_path).read_bytes()

    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass

    encoded = base64.b64encode(result_bytes).decode()
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
