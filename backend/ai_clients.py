import os
import json
import re
from pathlib import Path
from typing import Dict, Optional, Any

import requests
from dotenv import load_dotenv
from openai import OpenAI
from observability import trace_model_call

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

TEXT_GENERATOR_URL = os.getenv("TEXT_GENERATOR_URL", "http://model:8001/generate-text").strip()
IMAGE_GENERATOR_URL = os.getenv("IMAGE_GENERATOR_URL", "http://model:8001/generate-image").strip()
TEXT_MODEL_NAME = (os.getenv("TEXT_MODEL_NAME", "").strip() or "gpt-5-mini")
IMAGE_GENERATOR_TIMEOUT = int(os.getenv("IMAGE_GENERATOR_TIMEOUT", "600"))

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


def _extract_json_object(text: str) -> Optional[dict]:
    cleaned = (text or "").strip()
    if not cleaned:
        return None

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        snippet = cleaned[start : end + 1]
        try:
            parsed = json.loads(snippet)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    return None


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


def _resolve_reference_preset_path(
    mood: Optional[str],
    reference_preset: Optional[str] = None,
) -> tuple[Path, str]:
    """배경 파일 경로와 LAYOUT_PRESETS 키(background_id)를 반환합니다.

    프론트에서 넘어오는 fc_ 파일명 → 배경만 있는 bg 파일로 매핑합니다.
    UI 순서: position1=1_dish_bg, position2=2_dish_bg, position3=4_bg, position4=3_bg
    """
    # fc 파일명 → (bg 파일명, LAYOUT_PRESETS 키)
    FC_TO_BG: dict[str, tuple[str, str]] = {
        "fc_205.png": ("1_bg.webp", "1_dish_bg"),
        "fc_206.png": ("2_bg.png",  "2_dish_bg"),
        "fc_211.png": ("4_bg.webp", "4_bg"),
        "fc_217.png": ("3_bg.webp", "3_bg"),
    }

    preset_key = _clean_text(reference_preset).lower() if reference_preset else ""
    bg_filename, background_id = FC_TO_BG.get(preset_key, ("1_bg.webp", "1_dish_bg"))

    candidate = REFERENCE_PRESET_DIR / bg_filename
    if candidate.is_file():
        return candidate, background_id

    # 폴백: 찾을 수 있는 첫 번째 bg 파일
    for fname, bid in FC_TO_BG.values():
        p = REFERENCE_PRESET_DIR / fname
        if p.is_file():
            return p, bid

    return REFERENCE_PRESET_DIR / "1_bg.webp", "1_dish_bg"


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
    display_name = _clean_text(menu_name) or "이곳"

    if purpose == "방문 유도":
        copy = f"{location}에서 {display_name}를 찾고 있었다면 지금이 딱 좋아요."
    elif purpose == "신메뉴 홍보":
        copy = f"{display_name}, 이번에 새롭게 준비했어요."
    elif purpose == "이벤트 홍보":
        copy = f"{display_name}와 함께 지금 분위기 좋게 즐겨보세요."
    else:
        copy = f"{display_name}의 매력을 지금 경험해보세요."

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
def _encode_image_base64(image_path: str) -> Optional[str]:
    try:
        import base64
        return base64.b64encode(Path(image_path).read_bytes()).decode()
    except Exception:
        return None


def _call_remote_image_generator(
    prompt: str,
    run_name: str,
    image_path: Optional[str] = None,
    reference_path: Optional[str] = None,
    background_id: Optional[str] = None,
) -> Optional[Dict]:
    if not IMAGE_GENERATOR_URL:
        return None
    try:
        payload: Dict[str, Any] = {"prompt": prompt}

        if image_path and reference_path:
            product_b64 = _encode_image_base64(image_path)
            reference_b64 = _encode_image_base64(reference_path)
            if product_b64 and reference_b64:
                payload["product_image_base64"] = product_b64
                payload["reference_image_base64"] = reference_b64
                if background_id:
                    payload["background_id"] = background_id

        resp = requests.post(IMAGE_GENERATOR_URL, json=payload, timeout=IMAGE_GENERATOR_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        image_b64 = data.get("image_base64")
        if not image_b64:
            return None

        import base64, time
        ts = int(time.time() * 1000)
        output_dir = GENERATED_DIR / f"{run_name}_{ts}"
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
    recommended_concept: str,
    reference_preset: Optional[str] = None,
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

        reference_path: Optional[str] = None
        background_id: Optional[str] = None
        if image_path:
            ref, background_id = _resolve_reference_preset_path(mood, reference_preset)
            if ref.exists():
                reference_path = str(ref)

        remote = _call_remote_image_generator(
            prompt=prompt,
            run_name=run_name,
            image_path=image_path,
            reference_path=reference_path,
            background_id=background_id,
        )
        if remote:
            if remote.get("success"):
                _wandb_log_safe({
                    "trace_stage": "call_image_generator_success",
                    "menu_name": menu_name,
                    "has_input_image": bool(image_path),
                })
                return remote
            return {
                "success": False,
                "image_url": None,
                "prompt_used": prompt,
                "error": remote.get("error"),
            }

        return {
            "success": False,
            "image_url": None,
            "prompt_used": prompt,
            "error": "이미지 생성 실패",
        }

    except Exception as e:
        _wandb_log_safe({
            "trace_stage": "call_image_generator_exception",
            "menu_name": menu_name,
            "error": str(e),
        })
        return {
            "success": False,
            "image_url": None,
            "prompt_used": prompt if 'prompt' in locals() else recommended_concept,
            "error": str(e),
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
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return {"success": False, "copy": "", "hashtags": [], "error": "OPENAI_API_KEY not configured"}
        client = OpenAI(api_key=api_key)

        trace_model_call(
            name="text_generator.openai",
            provider="openai",
            model=TEXT_MODEL_NAME,
            input={
                "purpose": purpose,
                "business_category": business_category,
                "menu_name": menu_name,
                "location": location,
                "mood": mood,
                "weather_summary": weather_summary,
                "season_context": season_context,
                "recommended_concept": recommended_concept,
                "extra_prompt": extra_prompt,
            },
            metadata={"mode": "openai"},
            tags=["model", "text-generator"],
        )
        prompt = (
            "너는 상권/브랜드 마케팅 문구 작성기다. "
            "반드시 JSON만 출력한다. "
            '형식은 {"copy":"문구","hashtags":["태그1","태그2"]} 이다. '
            "copy는 한국어로 자연스럽고 짧게 1문장으로 작성한다. "
            "hashtags는 최대 10개, # 없이 순수 단어 배열로 작성한다. "
            "아래 정보를 반영한다.\n"
            f"- 목적: {purpose}\n"
            f"- 업종: {business_category}\n"
            f"- 메뉴/대상: {menu_name or '이곳'}\n"
            f"- 지역: {location}\n"
            f"- 무드: {mood or ''}\n"
            f"- 날씨: {weather_summary}\n"
            f"- 시즌 맥락: {season_context}\n"
            f"- 추천 컨셉: {recommended_concept}\n"
            f"- 추가 요청: {extra_prompt or ''}\n"
            "문구에는 괄호 설명을 붙이지 말고, 해시태그는 문구와 중복되더라도 자연스럽게 선택한다."
        )

        response = client.chat.completions.create(
            model=TEXT_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        output_text = (response.choices[0].message.content or "") if response.choices else ""
        parsed = _extract_json_object(output_text)
        if not parsed:
            return {
                "success": False,
                "copy": "",
                "hashtags": [],
                "error": f"invalid json output: {output_text[:500]}",
            }

        copy = _clean_text(parsed.get("copy"))
        hashtags = _normalize_hashtags(parsed.get("hashtags", []))
        if not copy:
            return {"success": False, "copy": "", "hashtags": [], "error": "empty copy from openai"}

        trace_model_call(
            name="text_generator.openai",
            provider="openai",
            model=TEXT_MODEL_NAME,
            input={"menu_name": menu_name, "purpose": purpose},
            output={
                "success": True,
                "copy_preview": copy[:300],
                "hashtags": hashtags,
            },
            metadata={"mode": "openai"},
            tags=["model", "text-generator"],
        )
        return {
            "success": True,
            "copy": copy,
            "hashtags": hashtags,
            "error": None,
        }

    except Exception as e:
        trace_model_call(
            name="text_generator.openai",
            provider="openai",
            model=TEXT_MODEL_NAME,
            input={"menu_name": menu_name, "purpose": purpose},
            error=str(e),
            metadata={"mode": "openai"},
            tags=["model", "text-generator"],
        )
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
