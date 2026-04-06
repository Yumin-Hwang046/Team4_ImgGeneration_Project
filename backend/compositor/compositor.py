"""
이미지 합성 모듈 (Playwright 아키텍처 대응 버전)
1. rembg로 제품 배경 제거 (원본 형태 100% 보존)
2. IC-Light 간소화: 배경 조명 분석 → 제품 조명 조화 + 방향성 섀도우
3. 생성된 배경에 제품 합성 후 순수 이미지(Image.Image) 반환
※ 텍스트 오버레이는 이 모듈에서 제외 (Playwright가 담당)
"""

import io
from PIL import Image, ImageDraw, ImageFilter
from rembg import new_session, remove

from .lighting import (
    analyze_background_lighting,
    harmonize_lighting,
    render_shadow,
    apply_light_wrap,
    apply_color_match,
)

OUTPUT_SIZE = (1024, 1024)
TEXT_PANEL_RATIO = 0.34  # 하단 텍스트 패널 비율 (템플릿과 동일하게 유지)

_rembg_session = None


def _get_rembg_session():
    global _rembg_session
    if _rembg_session is None:
        _rembg_session = new_session("birefnet-general")
    return _rembg_session


def remove_background(image_bytes: bytes) -> Image.Image:
    """
    rembg로 배경 제거, RGBA PIL Image 반환.
    세션은 프로세스당 한 번만 로드해 재사용.
    """
    try:
        session = _get_rembg_session()
        result_bytes = remove(
            image_bytes,
            session=session,
            alpha_matting=False,
        )
        return Image.open(io.BytesIO(result_bytes)).convert("RGBA")
    except Exception as e:
        raise RuntimeError(f"배경 제거 실패: {e}") from e


def composite_images(
    product_rgba: Image.Image,
    background_bytes: bytes,
    output_size: tuple[int, int] = OUTPUT_SIZE,
    product_scale: float | None = None,
    enable_lighting: bool = False,
    enable_post: bool = True,
) -> Image.Image:
    """
    배경 위에 배경 제거된 제품을 합성.
    enable_post: light wrap + color match 후처리 적용 여부
    """
    background = Image.open(io.BytesIO(background_bytes)).convert("RGB")
    background = background.resize(output_size, Image.LANCZOS)

    scale, vertical_offset = _compute_product_layout(product_rgba, product_scale)
    product_resized = _scale_product(product_rgba, output_size, scale)
    product_resized = _clean_alpha(product_resized)
    position = _center_position(product_resized.size, output_size, vertical_offset)

    light_direction = "top"
    if enable_lighting:
        light_direction = _get_light_direction(background)
        product_resized = harmonize_lighting(product_resized, background)

    canvas = background.convert("RGBA")

    if enable_lighting:
        canvas = render_shadow(canvas, product_resized, position, light_direction)

    canvas = _render_contact_shadow(canvas, product_resized, position)
    canvas.paste(product_resized, position, mask=product_resized)

    result = canvas.convert("RGB")

    if enable_post:
        # 제품 마스크를 output_size로 맞춰 후처리에 사용
        product_mask = Image.new("L", output_size, 0)
        product_mask.paste(product_resized.getchannel("A"), position)
        result = apply_color_match(result, background, product_mask)
        result = apply_light_wrap(result, background, product_mask)

    return result


def get_product_mask(
    product_rgba: Image.Image,
    output_size: tuple[int, int],
    product_scale: float | None = None,
) -> Image.Image:
    """composite_images와 동일한 레이아웃으로 제품 위치 마스크(L) 반환."""
    scale, vertical_offset = _compute_product_layout(product_rgba, product_scale)
    product_resized = _scale_product(product_rgba.copy(), output_size, scale)
    product_resized = _clean_alpha(product_resized)
    position = _center_position(product_resized.size, output_size, vertical_offset)

    mask = Image.new("L", output_size, 0)
    mask.paste(product_resized.getchannel("A"), position)
    return mask


# ─── 내부 헬퍼 함수들 ──────────────────────────────────────────

def _get_light_direction(background: Image.Image) -> str:
    _, direction = analyze_background_lighting(background)
    return direction


def _compute_product_layout(
    product: Image.Image,
    override_scale: float | None,
) -> tuple[float, float]:
    """제품 가로세로 비율에 따라 최적 scale과 vertical_offset 반환.

    vertical_offset은 텍스트 패널(하단 TEXT_PANEL_RATIO)을 피해
    제품 중심이 상단 영역 중앙에 위치하도록 계산.
    """
    available = 1.0 - TEXT_PANEL_RATIO  # 0.66
    center = available * 0.50           # 상단 영역 중앙 = 전체의 33%

    if override_scale is not None:
        return override_scale, center

    prod_w, prod_h = product.size
    aspect = prod_w / max(prod_h, 1)

    if aspect > 1.4:      # 가로형 (와이드)
        return 0.62, center
    elif aspect < 0.65:   # 세로형 (키가 큰 음료/병 등)
        return 0.45, center
    else:                 # 정방형
        return 0.52, center


def _clean_alpha(product_rgba: Image.Image, threshold: int = 10) -> Image.Image:
    """
    반투명 픽셀을 정리해 배경이 제품 영역에 비치는 현상 방지.
    threshold 미만은 완전 투명, 이상은 원래 알파 유지.
    """
    alpha = product_rgba.getchannel("A")
    cleaned = alpha.point(lambda x: 0 if x < threshold else x)
    result = product_rgba.copy()
    result.putalpha(cleaned)
    return result


def _render_contact_shadow(
    canvas: Image.Image,
    product: Image.Image,
    position: tuple[int, int],
) -> Image.Image:
    """제품 하단에 타원형 접지 그림자를 추가해 공중에 뜬 느낌을 제거."""
    prod_w, prod_h = product.size
    pos_x, pos_y = position

    shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow_layer)

    sw = int(prod_w * 0.80)
    sh = int(prod_h * 0.12)
    sx = pos_x + (prod_w - sw) // 2
    sy = pos_y + prod_h - sh // 2

    draw.ellipse([(sx, sy), (sx + sw, sy + sh)], fill=(0, 0, 0, 60))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=12))

    return Image.alpha_composite(canvas, shadow_layer)


def _scale_product(
    product: Image.Image,
    canvas_size: tuple[int, int],
    scale: float,
) -> Image.Image:
    canvas_w, canvas_h = canvas_size
    max_w = int(canvas_w * scale)
    max_h = int(canvas_h * scale)
    product.thumbnail((max_w, max_h), Image.LANCZOS)
    return product


def _center_position(
    product_size: tuple[int, int],
    canvas_size: tuple[int, int],
    vertical_offset: float,
) -> tuple[int, int]:
    prod_w, prod_h = product_size
    canvas_w, canvas_h = canvas_size
    x = (canvas_w - prod_w) // 2
    y = int(canvas_h * vertical_offset) - prod_h // 2
    text_start_y = int(canvas_h * (1.0 - TEXT_PANEL_RATIO))
    y = max(0, min(y, text_start_y - prod_h))
    return x, y
