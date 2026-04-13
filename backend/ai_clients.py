"""
AI 연동 인터페이스 파일

⚠️ 중요
이 파일은 실제 AI 모델과 연결되는 지점입니다.

현재는 mock / placeholder 상태이며,
실제 모델이 준비되면 아래 함수들만 교체하면 됩니다.

전체 백엔드는 이 반환 형식을 기준으로 동작합니다.
"""


from typing import Dict


# =========================
# IMAGE GENERATOR
# =========================
def call_image_generator(prompt: str) -> Dict:
    """
    이미지 생성 API 연결 함수

    🔧 팀원 작업 영역
    실제 이미지 생성 모델 API를 여기서 호출하면 됩니다.

    예:
    - Stable Diffusion
    - SDXL
    - 자체 inference 서버

    반환 형식 (반드시 유지):
    {
        "success": True,
        "image_url": "...",
        "prompt_used": "...",
        "error": None
    }
    """

    # ===== 현재는 mock =====
    return {
        "success": True,
        "image_url": "https://example.com/mock-image.jpg",
        "prompt_used": prompt,
        "error": None,
    }


# =========================
# TEXT GENERATOR
# =========================
def call_text_generator(prompt: str) -> Dict:
    """
    문구 생성 API 연결 함수

    🔧 팀원 작업 영역
    실제 텍스트 생성 모델 API를 여기서 호출하면 됩니다.

    예:
    - GPT
    - 자체 LLM
    - 프롬프트 엔진

    반환 형식 (반드시 유지):
    {
        "success": True,
        "copy": "...",
        "hashtags": ["#..."],
        "error": None
    }
    """

    # ===== 현재는 mock =====
    return {
        "success": True,
        "copy": "오늘의 추천 메뉴! 지금 방문해보세요.",
        "hashtags": ["#맛집", "#추천", "#오늘의메뉴"],
        "error": None,
    }