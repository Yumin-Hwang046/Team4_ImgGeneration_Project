from typing import Optional, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.text_generator.generator import generate_marketing_copy


router = APIRouter(prefix="/text", tags=["text"])


class TextGenerateRequest(BaseModel):
    purpose: str = Field(..., description="예: 방문 유도, 신메뉴 홍보, 이벤트 홍보")
    business_category: str = Field(..., description="예: 카페 & 베이커리")
    menu_name: str = Field(..., description="예: 딸기 케이크")
    location: str = Field(..., description="예: 서울특별시 종로구")
    mood: Optional[str] = Field(default=None, description="예: 따뜻한 감성")
    weather_summary: str = Field(..., description="예: 맑음, 18°C, 강수확률 10%")
    season_context: str = Field(..., description="예: 봄 시즌, 야외활동 증가, 산뜻한 분위기 선호")
    recommended_concept: str = Field(..., description="generation에서 추천된 컨셉 문장")
    extra_prompt: Optional[str] = Field(default=None, description="사용자 추가 요청")


class TextGenerateResponse(BaseModel):
    copy: str
    hashtags: List[str]
    error: Optional[str] = None


@router.post("/generate", response_model=TextGenerateResponse)
def generate_text(req: TextGenerateRequest):
    result = generate_marketing_copy(
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

    return TextGenerateResponse(
        copy=result.get("copy", ""),
        hashtags=result.get("hashtags", []),
        error=result.get("error"),
    )