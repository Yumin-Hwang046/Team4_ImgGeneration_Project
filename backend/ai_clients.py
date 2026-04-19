import os
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# -----------------------------
# ENV
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.getenv("MODEL_PROJECT_ROOT", str(BASE_DIR.parent)))
IMAGE_PIPELINE_SCRIPT = Path(
    os.getenv(
        "IMAGE_PIPELINE_SCRIPT",
        str(PROJECT_ROOT / "backend" / "image_generator" / "run_pipeline.py"),
    )
)
MODEL_VENV_PYTHON = os.getenv(
    "MODEL_VENV_PYTHON",
    str(PROJECT_ROOT / ".venv" / "bin" / "python"),
)
_generated_dir_raw = Path(os.getenv("GENERATED_IMAGE_DIR", "backend/generated"))
GENERATED_DIR = (
    _generated_dir_raw if _generated_dir_raw.is_absolute() else PROJECT_ROOT / _generated_dir_raw
)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

TEXT_GENERATOR_URL = os.getenv("TEXT_GENERATOR_URL", "").strip()

# 모델 미연결 시 사용할 더미 이미지 (직접 서빙 JPEG)
DUMMY_IMAGE_URL = "https://dummyimage.com/1080x1080/6BA4B8/FFFFFF.jpg"


# -----------------------------
# Helpers
# -----------------------------
def _safe_slug(text: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in text)[:50]


def _clean_text(value: Optional[str]) -> str:
    return (value or "").strip()


def _normalize_hashtags(raw: Any) -> list[str]:
    if raw is None:
        return []

    if isinstance(raw, str):
        raw = raw.replace(",", " ")
        tokens = raw.split()
    elif isinstance(raw, (list, tuple, set)):
        tokens = [str(x).strip() for x in raw if str(x).strip()]
    else:
        tokens = [str(raw).strip()]

    result = []
    seen = set()

    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if token.startswith("#"):
            token = token[1:].strip()
        token = token.replace(" ", "")
        if not token:
            continue
        if token not in seen:
            seen.add(token)
            result.append(token)

    return result[:10]


def _build_image_prompt(
    business_category: str,
    menu_name: str,
    location: str,
    mood: Optional[str],
    recommended_concept: str,
    extra_prompt: Optional[str] = None,
) -> str:
    parts = [
        f"업종: {business_category}",
        f"메뉴: {menu_name}",
        f"지역: {location}",
        f"추천 컨셉: {recommended_concept}",
    ]
    if mood:
        parts.append(f"무드: {mood}")
    if extra_prompt:
        parts.append(f"추가 요청: {extra_prompt}")
    return " | ".join(parts)


def _find_output_image(output_dir: Path) -> Optional[Path]:
    if not output_dir.exists():
        return None

    candidates = []
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        candidates.extend(output_dir.glob(ext))

    if not candidates:
        return None

    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def _fallback_text_result(
    purpose: str,
    business_category: str,
    menu_name: str,
    location: str,
    mood: Optional[str],
    weather_summary: str,
    season_context: str,
    recommended_concept: str,
    extra_prompt: Optional[str] = None,
    error: Optional[str] = None,
) -> Dict:
    if purpose == "방문 유도":
        copy = f"{location}에서 {menu_name} 찾고 있었다면 지금이 딱 좋아요."
    elif purpose == "신메뉴 홍보":
        copy = f"{menu_name}, 이번에 새롭게 준비했어요."
    elif purpose == "이벤트 홍보":
        copy = f"{menu_name}와 함께 지금 분위기 좋게 즐겨보세요."
    else:
        copy = f"{menu_name}의 매력을 지금 경험해보세요."

    details = []
    if weather_summary and "날씨 조회 실패" not in weather_summary:
        details.append(weather_summary)
    if season_context:
        details.append(season_context)
    if mood:
        details.append(f"무드: {mood}")
    if recommended_concept:
        details.append(f"컨셉: {recommended_concept}")
    if extra_prompt:
        details.append(f"추가요청: {extra_prompt}")

    if details:
        copy = f"{copy} ({' / '.join(details)})"

    hashtags = _normalize_hashtags([
        business_category,
        menu_name,
        location.replace(" ", ""),
        purpose.replace(" ", ""),
        mood or "",
    ])

    return {
        "success": True,
        "copy": copy,
        "hashtags": hashtags,
        "error": error,
    }


# =========================
# IMAGE GENERATOR
# =========================
def call_image_generator(
    business_category: str,
    menu_name: str,
    location: str,
    mood: Optional[str],
    recommended_concept: str,
    extra_prompt: Optional[str] = None,
    image_path: Optional[str] = None,
) -> Dict:
    """
    실제 이미지 생성 파이프라인(run_pipeline.py) 호출.
    모델 미연결 시 더미 이미지로 폴백.
    """
    try:
        prompt = _build_image_prompt(
            business_category=business_category,
            menu_name=menu_name,
            location=location,
            mood=mood,
            recommended_concept=recommended_concept,
            extra_prompt=extra_prompt,
        )

        run_name = f"{_safe_slug(menu_name)}_{_safe_slug(business_category)}"
        output_dir = GENERATED_DIR / run_name
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            MODEL_VENV_PYTHON,
            str(IMAGE_PIPELINE_SCRIPT),
            "--prompt", prompt,
            "--output_dir", str(output_dir),
        ]

        if image_path:
            cmd.extend(["--image_path", str(image_path)])

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            output_image = _find_output_image(output_dir)
            if output_image is not None:
                return {
                    "success": True,
                    "image_url": str(output_image),
                    "prompt_used": prompt,
                    "error": None,
                }

        # 파이프라인 실패 → 더미 이미지 폴백
        return {
            "success": True,
            "image_url": DUMMY_IMAGE_URL,
            "prompt_used": prompt,
            "error": None,
        }

    except Exception:
        return {
            "success": True,
            "image_url": DUMMY_IMAGE_URL,
            "prompt_used": recommended_concept,
            "error": None,
        }


# =========================
# TEXT GENERATOR
# =========================
def _call_local_text_generator(
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
    try:
        from text_generator.generator import generate_marketing_copy

        result = generate_marketing_copy(
            purpose=purpose,
            business_category=business_category,
            menu_name=menu_name,
            location=location,
            mood=mood,
            weather_summary=weather_summary,
            season_context=season_context,
            recommended_concept=recommended_concept,
            extra_prompt=extra_prompt,
        )

        if not isinstance(result, dict):
            return {"success": False, "copy": "", "hashtags": [], "error": "non-dict result"}

        return {
            "success": bool(result.get("copy")),
            "copy": _clean_text(result.get("copy")),
            "hashtags": _normalize_hashtags(result.get("hashtags", [])),
            "error": result.get("error"),
        }

    except Exception as e:
        return {"success": False, "copy": "", "hashtags": [], "error": str(e)}


def _call_remote_text_generator(payload: Dict) -> Dict:
    if not TEXT_GENERATOR_URL:
        return {"success": False, "copy": "", "hashtags": [], "error": "TEXT_GENERATOR_URL not configured"}

    try:
        resp = requests.post(TEXT_GENERATOR_URL, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        return {
            "success": bool(data.get("copy")),
            "copy": _clean_text(data.get("copy")),
            "hashtags": _normalize_hashtags(data.get("hashtags", [])),
            "error": data.get("error"),
        }
    except Exception as e:
        return {"success": False, "copy": "", "hashtags": [], "error": str(e)}


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
    """
    우선순위: 로컬 text_generator → HTTP → 규칙 기반 fallback
    """
    payload = {
        "purpose": purpose,
        "business_category": business_category,
        "menu_name": menu_name,
        "location": location,
        "mood": mood,
        "weather_summary": weather_summary,
        "season_context": season_context,
        "recommended_concept": recommended_concept,
        "extra_prompt": extra_prompt,
    }

    local_result = _call_local_text_generator(**payload)
    if local_result["success"]:
        return local_result

    remote_result = _call_remote_text_generator(payload)
    if remote_result["success"]:
        return remote_result

    return _fallback_text_result(
        purpose=purpose,
        business_category=business_category,
        menu_name=menu_name,
        location=location,
        mood=mood,
        weather_summary=weather_summary,
        season_context=season_context,
        recommended_concept=recommended_concept,
        extra_prompt=extra_prompt,
        error=f"local={local_result.get('error')} | remote={remote_result.get('error')}",
    )
