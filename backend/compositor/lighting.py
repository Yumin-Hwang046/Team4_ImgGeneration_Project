"""
IC-Light 간소화 구현 (Pillow/NumPy 기반 경량 버전)
실제 IC-Light(lllyasviel) 대비 GPU 없이 동작하는 조명 조화:
- 배경 조명 방향 + 색온도 분석 (4분할 휘도 비교)
- 제품 알파 마스크 기반 방향성 조명 그라디언트 오버레이
- 광원 방향을 고려한 소프트 드롭 섀도우 합성
"""

import numpy as np
from PIL import Image, ImageFilter, ImageChops


def analyze_background_lighting(
    background: Image.Image,
) -> tuple[tuple[int, int, int], str]:
    """
    배경 이미지를 4분할해 가장 밝은 방향을 광원으로 결정.

    Returns:
        (light_color_rgb, light_direction)
        light_direction: "left" | "right" | "top" | "bottom"
    """
    bg_array = np.array(background.convert("RGB"), dtype=np.float32)
    return _analyze_lighting(bg_array)


def harmonize_lighting(
    product_rgba: Image.Image,
    background: Image.Image,
) -> Image.Image:
    """
    배경 조명 색온도에 맞춰 제품 엣지에 방향성 조명 그라디언트 적용.

    Args:
        product_rgba: RGBA 제품 이미지 (배경 제거 완료)
        background: RGB 배경 이미지
    Returns:
        RGBA 제품 이미지 (조명 조화 적용)
    """
    bg_array = np.array(background.convert("RGB"), dtype=np.float32)
    light_color, light_direction = _analyze_lighting(bg_array)
    return _apply_light_gradient(product_rgba, light_color, light_direction)


def render_shadow(
    canvas: Image.Image,
    product_rgba: Image.Image,
    position: tuple[int, int],
    light_direction: str,
    shadow_opacity: int = 100,
    blur_radius: int = 20,
) -> Image.Image:
    """
    제품 붙여넣기 전에 캔버스에 방향성 드롭 섀도우를 렌더링.

    Args:
        canvas: RGBA 캔버스
        product_rgba: RGBA 제품 이미지
        position: 제품 붙여넣기 좌표 (x, y)
        light_direction: "left" | "right" | "top" | "bottom"
        shadow_opacity: 그림자 불투명도 (0-255)
        blur_radius: 그림자 블러 반경 (px)
    Returns:
        그림자가 추가된 RGBA 캔버스
    """
    SHADOW_OFFSETS: dict[str, tuple[int, int]] = {
        "left":   (16, 12),
        "right":  (-16, 12),
        "top":    (0, 18),
        "bottom": (0, -12),
    }
    sx, sy = SHADOW_OFFSETS.get(light_direction, (10, 10))
    shadow_pos = (position[0] + sx, position[1] + sy)

    alpha = product_rgba.getchannel("A")
    shadow_img = Image.new("RGBA", product_rgba.size, (0, 0, 0, shadow_opacity))
    shadow_img.putalpha(alpha)
    shadow_blurred = shadow_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_layer.paste(shadow_blurred, shadow_pos, mask=shadow_blurred)

    return Image.alpha_composite(canvas, shadow_layer)


def _analyze_lighting(
    bg_array: np.ndarray,
) -> tuple[tuple[int, int, int], str]:
    """배경 4분할 휘도 비교 → 광원 방향 및 색상 추출."""
    h, w = bg_array.shape[:2]
    half_h, half_w = h // 2, w // 2

    lum = (
        0.299 * bg_array[:, :, 0]
        + 0.587 * bg_array[:, :, 1]
        + 0.114 * bg_array[:, :, 2]
    )

    quadrant_lum = {
        "left":   lum[:, :half_w].mean(),
        "right":  lum[:, half_w:].mean(),
        "top":    lum[:half_h, :].mean(),
        "bottom": lum[half_h:, :].mean(),
    }
    light_direction = max(quadrant_lum, key=quadrant_lum.get)

    region_map: dict[str, np.ndarray] = {
        "left":   bg_array[:, :half_w],
        "right":  bg_array[:, half_w:],
        "top":    bg_array[:half_h, :],
        "bottom": bg_array[half_h:, :],
    }
    avg = region_map[light_direction].mean(axis=(0, 1)).astype(int)
    light_color = (int(avg[0]), int(avg[1]), int(avg[2]))

    return light_color, light_direction


def apply_light_wrap(
    composited: Image.Image,
    background: Image.Image,
    product_mask: Image.Image,
    intensity: float = 0.12,
    blur_radius: int = 8,
) -> Image.Image:
    """
    배경의 빛이 제품 경계를 안쪽으로 감싸는 효과 (Light Wrap).
    composited: RGB 합성 이미지
    background: RGB 원본 배경
    product_mask: L 모드 알파 마스크
    """
    bg = np.array(background.resize(composited.size).convert("RGB"), dtype=np.float32)
    comp = np.array(composited.convert("RGB"), dtype=np.float32)
    alpha = np.array(product_mask, dtype=np.float32) / 255.0

    # 알파를 블러해 경계 안쪽 그라디언트 생성
    alpha_pil = Image.fromarray((alpha * 255).astype(np.uint8), "L")
    blurred_alpha = np.array(
        alpha_pil.filter(ImageFilter.GaussianBlur(radius=blur_radius)),
        dtype=np.float32,
    ) / 255.0

    # 경계 가중치: 경계 안쪽에서만 배경색 혼합
    edge_weight = np.clip(blurred_alpha - alpha * 0.55, 0, 1) * alpha
    wrap = (edge_weight * intensity)[:, :, np.newaxis]

    result = comp * (1.0 - wrap) + bg * wrap
    return Image.fromarray(result.clip(0, 255).astype(np.uint8), "RGB")


def apply_color_match(
    composited: Image.Image,
    background: Image.Image,
    product_mask: Image.Image,
    strength: float = 0.22,
) -> Image.Image:
    """
    제품의 RGB 색 통계를 배경에 맞춰 자연스러운 색 조화 (Reinhard-style).
    composited: RGB 합성 이미지
    background: RGB 원본 배경
    product_mask: L 모드 알파 마스크
    """
    comp = np.array(composited.convert("RGB"), dtype=np.float32)
    bg   = np.array(background.resize(composited.size).convert("RGB"), dtype=np.float32)
    alpha = (np.array(product_mask, dtype=np.float32) / 255.0) > 0.5  # 제품 영역 마스크

    if not alpha.any():
        return composited

    result = comp.copy()
    for c in range(3):
        prod_pixels = comp[:, :, c][alpha]
        bg_pixels   = bg[:, :, c]

        prod_mean = prod_pixels.mean()
        prod_std  = max(prod_pixels.std(), 1e-6)
        bg_mean   = bg_pixels.mean()
        bg_std    = max(bg_pixels.std(), 1e-6)

        # Reinhard transfer: 분포를 배경에 맞게 이동
        transferred = (comp[:, :, c] - prod_mean) * (bg_std / prod_std) + bg_mean

        # strength 비율로 블렌딩 (제품 영역에만 적용)
        blended = comp[:, :, c].copy()
        blended[alpha] = (
            comp[:, :, c][alpha] * (1 - strength)
            + transferred[alpha] * strength
        )
        result[:, :, c] = blended

    return Image.fromarray(result.clip(0, 255).astype(np.uint8), "RGB")


def _apply_light_gradient(
    product: Image.Image,
    light_color: tuple[int, int, int],
    light_direction: str,
    max_intensity: float = 0.30,
) -> Image.Image:
    """제품 알파 마스크 기반 방향성 조명 그라디언트 합성."""
    result = product.copy().convert("RGBA")
    w, h = result.size
    r, g, b = light_color

    if light_direction == "left":
        grad_1d = np.linspace(max_intensity, 0.0, w, dtype=np.float32)
        gradient = np.tile(grad_1d, (h, 1))
    elif light_direction == "right":
        grad_1d = np.linspace(0.0, max_intensity, w, dtype=np.float32)
        gradient = np.tile(grad_1d, (h, 1))
    elif light_direction == "top":
        grad_1d = np.linspace(max_intensity, 0.0, h, dtype=np.float32)
        gradient = np.tile(grad_1d.reshape(-1, 1), (1, w))
    else:
        grad_1d = np.linspace(0.0, max_intensity, h, dtype=np.float32)
        gradient = np.tile(grad_1d.reshape(-1, 1), (1, w))

    product_alpha = np.array(result.getchannel("A"), dtype=np.float32) / 255.0
    alpha_map = (gradient * product_alpha * 255).clip(0, 255).astype(np.uint8)

    overlay = Image.new("RGBA", (w, h), (r, g, b, 0))
    overlay.putalpha(Image.fromarray(alpha_map))

    return Image.alpha_composite(result, overlay)
