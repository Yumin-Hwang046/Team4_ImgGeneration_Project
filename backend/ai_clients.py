import os
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any

import requests
from dotenv import load_dotenv

try:
    import wandb
except Exception:
    wandb = None

# backend/.env 읽기
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

_WANDB_INITIALIZED = False


def _init_wandb_if_needed() -> None:
    global _WANDB_INITIALIZED

    if wandb is None:
        return

    if _WANDB_INITIALIZED:
        return

    try:
        if getattr(wandb, "run", None) is not None:
            _WANDB_INITIALIZED = True
            return
    except Exception:
        pass

    api_key = os.getenv("WANDB_API_KEY", "").strip()
    project = os.getenv("WANDB_PROJECT", "").strip()
    entity = os.getenv("WANDB_ENTITY", "").strip()

    if not api_key or not project:
        return

    try:
        os.environ["WANDB_API_KEY"] = api_key
        if entity:
            wandb.init(project=project, entity=entity, job_type="ai-clients")
        else:
            wandb.init(project=project, job_type="ai-clients")
        _WANDB_INITIALIZED = True
    except Exception:
        pass


def _wandb_log_safe(payload: dict) -> None:
    if wandb is None:
        return

    try:
        _init_wandb_if_needed()
        if _WANDB_INITIALIZED:
            wandb.log(payload)
    except Exception:
        pass


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
REFERENCE_PRESET_DIR = Path(
    os.getenv(
        "REFERENCE_PRESET_DIR",
        str(PROJECT_ROOT / "backend" / "image_generator" / "reference_presets"),
    )
)
_generated_dir_raw = Path(os.getenv("GENERATED_IMAGE_DIR", "backend/generated"))
GENERATED_DIR = (
    _generated_dir_raw if _generated_dir_raw.is_absolute() else PROJECT_ROOT / _generated_dir_raw
)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

TEXT_GENERATOR_URL = os.getenv("TEXT_GENERATOR_URL", "").strip()
IMAGE_GENERATOR_URL = os.getenv("IMAGE_GENERATOR_URL", "").strip()

# 모델 미연결 시 사용할 더미 이미지 (직접 서빙 JPEG)
DUMMY_IMAGE_URL = "https://dummyimage.com/1080x1080/6BA4B8/FFFFFF.jpg"


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


def _normalize_mood_key(mood: Optional[str]) -> str:
    mood_key = _clean_text(mood).lower()
    mood_map = {
        "warm": "warm",
        "clean": "clean",
        "trendy": "trendy",
        "premium": "premium",
        "따뜻한": "warm",
        "깔끔한": "clean",
        "트렌디": "trendy",
        "프리미엄": "premium",
    }
    return mood_map.get(mood_key, "warm")


def _resolve_reference_preset_path(mood: Optional[str], reference_preset: Optional[str]) -> Path:
    mood_key = _normalize_mood_key(mood)
    mood_dir = REFERENCE_PRESET_DIR / mood_key

    # 경로 탈출 방지: 파일명만 사용
    safe_filename = Path(reference_preset).name if reference_preset else "1.png"
    requested = mood_dir / safe_filename
    if requested.exists():
        return requested

    for fallback_name in ("1.png", "2.png", "3.png", "4.png"):
        fallback = mood_dir / fallback_name
        if fallback.exists():
            return fallback

    # 기존 단일 파일 구조와의 호환
    legacy = REFERENCE_PRESET_DIR / f"{mood_key}.png"
    if legacy.exists():
        return legacy

    return REFERENCE_PRESET_DIR / "default.png"


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
def _call_remote_image_generator(prompt: str, run_name: str) -> Optional[Dict]:
    if not IMAGE_GENERATOR_URL:
        return None
    try:
        resp = requests.post(
            IMAGE_GENERATOR_URL,
            json={"prompt": prompt},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        image_b64 = data.get("image_base64")
        if not image_b64:
            return None

        import base64
        output_dir = GENERATED_DIR / run_name
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "base_0.png"
        output_path.write_bytes(base64.b64decode(image_b64))
        return {
            "success": True,
            "image_url": str(output_path),
            "prompt_used": data.get("prompt_used", prompt),
            "error": None,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def call_image_generator(
    business_category: str,
    menu_name: str,
    location: str,
    mood: Optional[str],
    reference_preset: Optional[str],
    recommended_concept: str,
    extra_prompt: Optional[str] = None,
    image_path: Optional[str] = None,
) -> Dict:
    _wandb_log_safe({
        "trace_stage": "call_image_generator_start",
        "business_category": business_category,
        "menu_name": menu_name,
        "location": location,
        "has_input_image": bool(image_path),
    })

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

        remote = _call_remote_image_generator(prompt, run_name)
        if remote and remote.get("success"):
            return remote

        output_dir = GENERATED_DIR / run_name
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            MODEL_VENV_PYTHON,
            str(IMAGE_PIPELINE_SCRIPT),
            "--prompt", prompt,
            "--output_dir", str(output_dir),
            "--reference_image_path", str(_resolve_reference_preset_path(mood, reference_preset)),
        ]

        if image_path:
            cmd.extend(["--image_path", str(image_path)])

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            output_image = _find_output_image(output_dir)
            if output_image is not None:
                _wandb_log_safe({
                    "trace_stage": "call_image_generator_success",
                    "menu_name": menu_name,
                    "used_dummy": False,
                })
                return {
                    "success": True,
                    "image_url": str(output_image),
                    "prompt_used": prompt,
                    "error": None,
                }

        _wandb_log_safe({
            "trace_stage": "call_image_generator_dummy_fallback",
            "menu_name": menu_name,
            "used_dummy": True,
        })
        return {
            "success": True,
            "image_url": DUMMY_IMAGE_URL,
            "prompt_used": prompt,
            "error": None,
        }

    except Exception as e:
        _wandb_log_safe({
            "trace_stage": "call_image_generator_exception",
            "menu_name": menu_name,
            "error": str(e),
        })
        return {
            "success": True,
            "image_url": DUMMY_IMAGE_URL,
            "prompt_used": recommended_concept,
            "error": None,
        }


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
    _wandb_log_safe({
        "trace_stage": "call_text_generator_start",
        "purpose": purpose,
        "business_category": business_category,
        "menu_name": menu_name,
    })

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
        _wandb_log_safe({
            "trace_stage": "call_text_generator_local_success",
            "menu_name": menu_name,
        })
        return local_result

    remote_result = _call_remote_text_generator(payload)
    if remote_result["success"]:
        _wandb_log_safe({
            "trace_stage": "call_text_generator_remote_success",
            "menu_name": menu_name,
        })
        return remote_result

    _wandb_log_safe({
        "trace_stage": "call_text_generator_rule_fallback",
        "menu_name": menu_name,
        "purpose": purpose,
        "local_error": local_result.get("error"),
        "remote_error": remote_result.get("error"),
    })

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