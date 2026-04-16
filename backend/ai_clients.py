"""
AI 연동 인터페이스 파일

⚠️ 중요
이 파일은 실제 AI 모델과 연결되는 지점입니다.

현재는 mock / placeholder 상태이며,
실제 모델이 준비되면 아래 함수들만 교체하면 됩니다.

전체 백엔드는 이 반환 형식을 기준으로 동작합니다.
"""

from typing import Dict, Optional


def call_image_generator(
    business_category: str,
    menu_name: str,
    location: str,
    mood: Optional[str],
    recommended_concept: str,
    extra_prompt: Optional[str] = None,
    image_path: Optional[str] = None,
) -> Dict:
    return {
        "success": True,
        "image_url": "https://picsum.photos/1080/1080",
        "prompt_used": recommended_concept,
        "error": None,
    }


def call_text_generator(
    purpose: str,
    business_category: str,
    menu_name: str,
    location: str,
    mood: Optional[str],
    weather_summary: str,
    season_context: str,
    recommended_concept: str,
    extra_prompt: Optional[str] = None,
) -> Dict:
    return {
        "success": True,
        "copy": f"{menu_name}의 특별한 맛을 지금 경험해보세요.",
        "hashtags": ["#맛집", "#추천", "#오늘의메뉴"],
        "error": None,
    }
