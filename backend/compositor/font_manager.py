"""
폰트 관리 모듈 (레거시 PIL 렌더링용 — Playwright 전환 후 다운로드 불필요)

Playwright HTML 템플릿은 CDN에서 직접 Pretendard를 로드합니다.
"""

from PIL import ImageFont


def ensure_fonts() -> None:
    """서버 시작 시 호출 — Playwright 전환 후 다운로드 불필요."""
    pass


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """PIL 폴백용 — 시스템 기본 폰트 반환."""
    return ImageFont.load_default()
