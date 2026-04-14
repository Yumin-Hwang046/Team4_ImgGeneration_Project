"""
AI 연동 인터페이스 파일

현재는 mock / placeholder 상태이며,
실제 모델이 준비되면 아래 함수들만 교체하면 됩니다.
"""

from typing import Dict, Optional


def _safe_join(*parts: Optional[str]) -> str:
    values = [str(part).strip() for part in parts if part]
    return " | ".join(values)


def call_image_generator(
    *,
    business_category: str,
    menu_name: str,
    location: str,
    mood: Optional[str] = None,
    recommended_concept: Optional[str] = None,
    extra_prompt: Optional[str] = None,
    image_path: Optional[str] = None,
) -> Dict:
    prompt = _safe_join(
        f"업종: {business_category}",
        f"메뉴: {menu_name}",
        f"지역: {location}",
        f"무드: {mood}" if mood else None,
        f"추천 컨셉: {recommended_concept}" if recommended_concept else None,
        f"추가 요청: {extra_prompt}" if extra_prompt else None,
        f"참고 이미지: {image_path}" if image_path else None,
    )

    return {
        "success": True,
        "image_url": "https://example.com/mock-image.jpg",
        "prompt_used": prompt,
        "error": None,
    }


def call_text_generator(
    *,
    purpose: str,
    business_category: str,
    menu_name: str,
    location: str,
    mood: Optional[str] = None,
    weather_summary: Optional[str] = None,
    season_context: Optional[str] = None,
    recommended_concept: Optional[str] = None,
    extra_prompt: Optional[str] = None,
) -> Dict:
    copy = (
        f"{location}에서 {menu_name} 어떠세요? "
        f"{weather_summary or '오늘 분위기'}에 어울리는 {business_category} 추천 콘텐츠입니다."
    )

    hashtags = [
        f"#{menu_name.replace(' ', '')}",
        f"#{business_category.replace(' ', '')}",
        "#오늘의추천",
    ]

    if mood:
        hashtags.append(f"#{mood.replace(' ', '')}")

    return {
        "success": True,
        "copy": copy,
        "hashtags": hashtags,
        "error": None,
    }
