"""
소상공인 AI 광고 생성 서비스 - FastAPI 백엔드
파이프라인: 이미지 업로드 → GPT 분석 → SD 1.5 배경 생성 → Playwright 렌더링 → 최종 이미지 반환
"""

import asyncio
import base64
import io
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pydantic import BaseModel

from image_analyzer import AnalysisResult, analyze_and_generate_prompts, resolve_mood, MOOD_CONFIGS
from image_generator import (
    generate_background_image,
    inpaint_boundary,
    SIZE_MAP,
)
from compositor import remove_background, composite_images, ensure_fonts, render_ad_image
from compositor.compositor import _get_rembg_session, get_product_mask
from compositor.playwright_renderer import shutdown_browser
from text_generator import generate_copy_from_image, generate_copy_from_text, CopyResult

load_dotenv()

MAX_IMAGE_SIZE_MB = 10


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_fonts()
    app.state.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    _get_rembg_session()  # 서버 시작 시 rembg 모델 미리 로드
    yield
    await app.state.openai_client.close()
    shutdown_browser()


app = FastAPI(
    title="소상공인 AI 광고 생성 API",
    description="사진 한 장으로 전문가 수준의 마케팅 콘텐츠 자동 생성",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateResponse(BaseModel):
    product_description: str
    hashtags: list[str]
    results: list[dict]  # [{ad_copy, image_b64}]


class TextToImageResponse(BaseModel):
    image_b64: str


class CopyResponse(BaseModel):
    product_description: str
    variants: list[dict]   # [{style, headline, tagline}]
    hashtags: list[str]


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "소상공인 AI 광고 생성"}


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_ads(
    image: UploadFile = File(..., description="제품/음식 사진 (JPG, PNG)"),
    ref_image: Optional[UploadFile] = File(default=None, description="참고 스타일 이미지 (선택)"),
    user_prompt: str = Form(default="", description="강조하고 싶은 내용 (선택)"),
    mood: str = Form(default="깔끔한 상품 홍보", description="광고 무드: 따뜻한 매장 분위기 | 깔끔한 상품 홍보 | 트렌디한 메뉴 홍보 | 프리미엄 매장·상품"),
    subject_type: str = Form(default="food", description="피사체 유형: food | product"),
    size: str = Form(default="square", description="출력 비율: square | portrait | landscape | naver"),
):
    _validate_image(image)
    image_bytes = await image.read()
    _validate_image_size(image_bytes)
    _validate_image_bytes(image_bytes)

    ref_image_bytes: bytes | None = None
    if ref_image and ref_image.filename:
        ext = (ref_image.filename or "").lower().rsplit(".", 1)[-1]
        if ext not in {"jpg", "jpeg", "png"}:
            raise HTTPException(status_code=415, detail="참고 이미지는 JPG, PNG만 가능합니다.")
        ref_image_bytes = await ref_image.read()
        magic = ref_image_bytes[:8]
        if not (magic[:3] == b"\xff\xd8\xff" or magic[:8] == b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(status_code=415, detail="참고 이미지는 JPG, PNG만 가능합니다.")

    client = app.state.openai_client

    try:
        analysis = await analyze_and_generate_prompts(
            image_bytes=image_bytes,
            user_prompt=user_prompt,
            mood=mood,
            client=client,
        )
    except RuntimeError as e:
        logging.error(f"[분석 실패] {e}")
        raise HTTPException(status_code=502, detail=str(e))

    try:
        if ref_image_bytes:
            # 레퍼런스 이미지 있음 → SDXL + IP-Adapter
            results = await _run_sdxl_pipeline(
                analysis, image_bytes, ref_image_bytes, size, mood, subject_type
            )
        elif subject_type == "food":
            results = await _run_food_pipeline(analysis, image_bytes, size, mood, client)
        else:
            results = await _run_product_pipeline(analysis, image_bytes, size, mood, client)
    except RuntimeError as e:
        logging.error(f"[파이프라인 실패] {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logging.error(f"[파이프라인 예외] {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"처리 중 오류: {e}")

    return GenerateResponse(
        product_description=analysis.product_description,
        hashtags=analysis.hashtags,
        results=results,
    )


@app.post("/api/generate/text", response_model=TextToImageResponse)
async def generate_from_text(
    ad_copy: str = Form(..., description="광고 문구 (사용자 직접 입력)"),
    user_prompt: str = Form(default="", description="추가 요청사항 (선택)"),
    mood: str = Form(default="깔끔한 상품 홍보", description="광고 무드: 따뜻한 매장 분위기 | 깔끔한 상품 홍보 | 트렌디한 메뉴 홍보 | 프리미엄 매장·상품"),
    size: str = Form(default="square", description="출력 비율: square | portrait | landscape | naver"),
):
    """Case 1 — 텍스트 입력만으로 광고 이미지 생성."""
    resolved = resolve_mood(mood)
    mood_cfg = MOOD_CONFIGS.get(resolved, MOOD_CONFIGS["깔끔한 상품 홍보"])

    base_desc = user_prompt if user_prompt else ad_copy
    bg_prompt = (
        f"Advertisement background scene for '{base_desc}', "
        f"{mood_cfg['visual']}, {mood_cfg['quality']}, "
        "no text, no letters, no watermark, photorealistic"
    )

    client = app.state.openai_client

    try:
        bg_bytes = await generate_background_image(prompt=bg_prompt, size=size, client=client)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    try:
        final_bytes = await render_ad_image(
            image_bytes=bg_bytes,
            headline=ad_copy,
            tagline=base_desc,
            details=[],
            mood=mood,
            size=size,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"렌더링 실패: {e}")

    image_b64 = base64.b64encode(final_bytes).decode()
    return TextToImageResponse(image_b64=image_b64)


@app.post("/api/copy", response_model=CopyResponse)
async def generate_copy(
    image: Optional[UploadFile] = File(default=None, description="제품/매장 사진 (선택 — 없으면 description 필수)"),
    description: str = Form(default="", description="제품/매장 텍스트 설명 (이미지 없을 때 필수)"),
    user_prompt: str = Form(default="", description="추가 요청사항 (선택)"),
    mood: str = Form(default="깔끔한 상품 홍보", description="광고 무드: 따뜻한 매장 분위기 | 깔끔한 상품 홍보 | 트렌디한 메뉴 홍보 | 프리미엄 매장·상품"),
):
    """문구 만들기 — 감성형·직접형·스토리형 3종 광고 카피 + 해시태그 반환."""
    has_image = image is not None and image.filename
    if not has_image and not description:
        raise HTTPException(status_code=422, detail="image 또는 description 중 하나는 필수입니다.")

    client = app.state.openai_client

    try:
        if has_image:
            image_bytes = await image.read()
            _validate_image_size(image_bytes)
            _validate_image_bytes(image_bytes)
            result = await generate_copy_from_image(
                image_bytes=image_bytes,
                mood=mood,
                user_prompt=user_prompt,
                client=client,
            )
        else:
            result = await generate_copy_from_text(
                description=description,
                mood=mood,
                user_prompt=user_prompt,
                client=client,
            )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return CopyResponse(
        product_description=result.product_description,
        variants=[v.model_dump() for v in result.variants],
        hashtags=result.hashtags,
    )


async def _run_sdxl_pipeline(
    analysis: AnalysisResult,
    image_bytes: bytes,
    ref_image_bytes: bytes,
    size: str,
    mood: str,
    subject_type: str,
) -> list[dict]:
    """레퍼런스 이미지 있을 때 — SDXL + IP-Adapter 파이프라인.

    food/product 공통: 레퍼런스 스타일로 배경 생성 → 원본 피사체 배경 제거 → 합성
    원본 이미지(음식/제품)는 변형하지 않고 그대로 사용.
    """
    if not analysis.bg_prompts or not analysis.ad_copies:
        raise RuntimeError("이미지 분석 결과에 필수 필드(bg_prompts/ad_copies)가 없습니다.")

    bg_bytes = await generate_background_image(
        prompt=analysis.bg_prompts[0],
        size=size,
        ip_adapter_image_bytes=ref_image_bytes,
    )

    _, out_w, out_h = SIZE_MAP.get(size, SIZE_MAP["square"])
    loop = asyncio.get_running_loop()
    subject_rgba = await loop.run_in_executor(None, remove_background, image_bytes)
    composited = await loop.run_in_executor(
        None, composite_images, subject_rgba.copy(), bg_bytes, (out_w, out_h)
    )
    buf = io.BytesIO()
    composited.save(buf, format="PNG")
    bg_bytes = buf.getvalue()

    try:
        final_bytes = await render_ad_image(
            image_bytes=bg_bytes,
            headline=analysis.ad_copies[0],
            tagline=analysis.product_description,
            details=analysis.details,
            mood=mood,
            size=size,
        )
    except Exception as e:
        raise RuntimeError(f"렌더링 실패: {e}")

    image_b64 = base64.b64encode(final_bytes).decode()
    return [{"ad_copy": analysis.ad_copies[0], "image_b64": image_b64}]


async def _run_food_pipeline(
    analysis: AnalysisResult,
    original_image_bytes: bytes,
    size: str,
    mood: str,
    client: AsyncOpenAI,
) -> list[dict]:
    """food 모드: SD 1.5 배경 생성 → 배경 제거 → 합성 → Playwright 렌더링."""
    if not analysis.bg_prompts or not analysis.ad_copies:
        raise RuntimeError("이미지 분석 결과에 필수 필드(bg_prompts/ad_copies)가 없습니다.")

    bg_bytes = await generate_background_image(
        prompt=analysis.bg_prompts[0],
        size=size,
        client=client,
    )

    _, out_w, out_h = SIZE_MAP.get(size, SIZE_MAP["square"])
    loop = asyncio.get_running_loop()
    food_rgba = await loop.run_in_executor(None, remove_background, original_image_bytes)
    food_mask = await loop.run_in_executor(
        None, get_product_mask, food_rgba.copy(), (out_w, out_h)
    )
    composited = await loop.run_in_executor(
        None, composite_images, food_rgba.copy(), bg_bytes, (out_w, out_h)
    )

    buf = io.BytesIO()
    composited.save(buf, format="PNG")
    composited_bytes = buf.getvalue()

    composited_bytes = await inpaint_boundary(
        composited_bytes, food_mask, analysis.bg_prompts[0]
    )

    try:
        final_bytes = await render_ad_image(
            image_bytes=composited_bytes,
            headline=analysis.ad_copies[0],
            tagline=analysis.product_description,
            details=analysis.details,
            mood=mood,
            size=size,
        )
    except Exception as e:
        raise RuntimeError(f"렌더링 실패: {e}")

    image_b64 = base64.b64encode(final_bytes).decode()
    return [{"ad_copy": analysis.ad_copies[0], "image_b64": image_b64}]


async def _run_product_pipeline(
    analysis: AnalysisResult,
    image_bytes: bytes,
    size: str,
    mood: str,
    client: AsyncOpenAI,
) -> list[dict]:
    """product 모드: 배경 제거 → DALL-E 3 배경 생성 → 합성 → Playwright 렌더링."""
    if not analysis.bg_prompts or not analysis.ad_copies:
        raise RuntimeError("이미지 분석 결과에 필수 필드(bg_prompts/ad_copies)가 없습니다.")

    bg_bytes = await generate_background_image(
        prompt=analysis.bg_prompts[0],
        size=size,
        client=client,
    )

    _, out_w, out_h = SIZE_MAP.get(size, SIZE_MAP["square"])
    loop = asyncio.get_running_loop()
    product_rgba = await loop.run_in_executor(None, remove_background, image_bytes)
    product_mask = await loop.run_in_executor(
        None, get_product_mask, product_rgba.copy(), (out_w, out_h)
    )
    composited = await loop.run_in_executor(
        None, composite_images, product_rgba.copy(), bg_bytes, (out_w, out_h)
    )

    buf = io.BytesIO()
    composited.save(buf, format="PNG")
    composited_bytes = buf.getvalue()

    composited_bytes = await inpaint_boundary(
        composited_bytes, product_mask, analysis.bg_prompts[0]
    )

    try:
        final_bytes = await render_ad_image(
            image_bytes=composited_bytes,
            headline=analysis.ad_copies[0],
            tagline=analysis.product_description,
            details=analysis.details,
            mood=mood,
            size=size,
        )
    except Exception as e:
        raise RuntimeError(f"렌더링 실패: {e}")

    image_b64 = base64.b64encode(final_bytes).decode()
    return [{"ad_copy": analysis.ad_copies[0], "image_b64": image_b64}]


def _validate_image(image: UploadFile) -> None:
    ext = (image.filename or "").lower().rsplit(".", 1)[-1]
    if ext not in {"jpg", "jpeg", "png", "webp", "jfif"}:
        raise HTTPException(status_code=415, detail="지원하지 않는 파일 형식입니다. JPG, PNG, WebP만 가능합니다.")


def _validate_image_bytes(image_bytes: bytes) -> None:
    """Magic bytes로 실제 이미지 포맷 검증."""
    magic = image_bytes[:12]
    is_jpeg = magic[:3] == b"\xff\xd8\xff"
    is_png  = magic[:8] == b"\x89PNG\r\n\x1a\n"
    is_webp = magic[:4] == b"RIFF" and magic[8:12] == b"WEBP"
    if not (is_jpeg or is_png or is_webp):
        raise HTTPException(
            status_code=415,
            detail="지원하지 않는 파일 형식입니다. JPG, PNG, WebP만 가능합니다.",
        )


def _validate_image_size(image_bytes: bytes) -> None:
    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > MAX_IMAGE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"이미지 크기가 너무 큽니다. 최대 {MAX_IMAGE_SIZE_MB}MB",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
