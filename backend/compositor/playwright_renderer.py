"""
Playwright 기반 광고 이미지 렌더러

Jinja2 HTML 템플릿 → Playwright 스크린샷 → JPEG bytes 반환

브라우저는 서버 시작 시 1회만 실행, 요청마다 탭(page)만 열고 닫음.
Windows asyncio 호환을 위해 sync API + ThreadPoolExecutor 사용.
"""

import asyncio
import base64
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"

SIZE_MAP: dict[str, tuple[int, int]] = {
    "square":    (1024, 1024),
    "portrait":  (1024, 1792),
    "landscape": (1792, 1024),
    "naver":     (860,  1200),
}

_MOOD_TEMPLATE: dict[str, str] = {
    "깔끔한 상품 홍보":   "clean.html",
    "따뜻한 매장 분위기": "warm.html",
    "트렌디한 메뉴 홍보": "trendy.html",
    "프리미엄 매장·상품": "premium.html",
}

_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
_executor = ThreadPoolExecutor(max_workers=4)

# 브라우저 싱글톤 — 서버 생애주기 동안 1개만 유지
_browser = None
_playwright_ctx = None
_browser_lock = threading.Lock()


def _get_browser():
    """브라우저가 없으면 1회 생성, 이후엔 재사용."""
    global _browser, _playwright_ctx
    if _browser is not None:
        return _browser
    with _browser_lock:
        if _browser is None:
            from playwright.sync_api import sync_playwright
            _playwright_ctx = sync_playwright().start()
            _browser = _playwright_ctx.chromium.launch()
    return _browser


def shutdown_browser():
    """서버 종료 시 브라우저 정리 (lifespan에서 호출).
    hot-reload 시 greenlet 스레드 불일치 오류는 무시하고 레퍼런스만 제거.
    """
    global _browser, _playwright_ctx
    if _browser:
        try:
            _browser.close()
        except Exception:
            pass
        _browser = None
    if _playwright_ctx:
        try:
            _playwright_ctx.stop()
        except Exception:
            pass
        _playwright_ctx = None


def _compute_sizes(width: int, height: int) -> dict:
    scale = min(width, height) / 1024
    return {
        "width":          width,
        "height":         height,
        "headline_size":  int(68 * scale),
        "tagline_size":   int(30 * scale),
        "detail_size":    int(22 * scale),
        "padding":        int(60 * scale),
        "bottom_padding": int(72 * scale),
    }


def _render_sync(html: str, width: int, height: int) -> bytes:
    """브라우저 재사용 — 탭만 열고 캡처 후 닫음."""
    browser = _get_browser()
    page = browser.new_page(viewport={"width": width, "height": height})
    try:
        page.set_content(html, wait_until="networkidle")
        return page.screenshot(type="jpeg", quality=92)
    finally:
        page.close()


async def render_ad_image(
    image_bytes: bytes,
    headline: str,
    tagline: str,
    details: list[str],
    mood: str,
    size: str = "square",
) -> bytes:
    """HTML 템플릿을 렌더링하고 Playwright로 스크린샷하여 JPEG bytes 반환."""
    width, height = SIZE_MAP.get(size, (1024, 1024))
    image_b64 = base64.b64encode(image_bytes).decode()

    template_name = _MOOD_TEMPLATE.get(mood, "clean.html")
    template = _env.get_template(template_name)
    html = template.render(
        image_b64=image_b64,
        headline=headline,
        tagline=tagline,
        details=details[:4],
        **_compute_sizes(width, height),
    )

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _render_sync, html, width, height)
