import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

try:
    from langfuse.openai import OpenAI
except Exception:
    from openai import OpenAI

try:
    import wandb
except Exception:
    wandb = None

from text_generator.prompt_templates import get_full_prompt

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

_WANDB_INITIALIZED = False


PURPOSE_VARIANTS = {
    "방문 유도": ["지금 들르기 좋은", "가볍게 찾기 좋은", "오늘 생각나는"],
    "신메뉴 홍보": ["이번에 새롭게 준비한", "새로 선보이는", "눈여겨볼 만한"],
    "이벤트 홍보": ["지금 확인해두기 좋은", "놓치기 아쉬운", "가볍게 참여하기 좋은"],
    "매장 홍보": ["분위기까지 함께 즐기기 좋은", "한 번쯤 들러보기 좋은", "편하게 찾기 좋은"],
}

BUSINESS_TAG_MAP = {
    "카페": ["카페", "카페추천"],
    "베이커리": ["베이커리", "베이커리추천"],
    "디저트": ["디저트", "디저트맛집"],
    "한식": ["한식", "한식맛집"],
    "양식": ["양식", "레스토랑"],
}

SEASON_TAG_MAP = {
    "봄": ["봄디저트", "봄카페"],
    "여름": ["여름디저트", "여름카페"],
    "가을": ["가을감성", "가을카페"],
    "겨울": ["겨울디저트", "겨울카페"],
}

MOOD_TAG_MAP = {
    "따뜻한": ["감성카페", "포근한분위기"],
    "포근": ["감성카페", "포근한분위기"],
    "깔끔": ["깔끔한무드", "정갈한분위기"],
    "트렌디": ["트렌디카페", "요즘감성"],
    "힙": ["힙한분위기", "감각적인공간"],
    "프리미엄": ["프리미엄디저트", "고급스러운무드"],
}



def _init_wandb_if_needed() -> None:
    global _WANDB_INITIALIZED

    if wandb is None or _WANDB_INITIALIZED:
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
            wandb.init(project=project, entity=entity, job_type="text-generator")
        else:
            wandb.init(project=project, job_type="text-generator")
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



def _build_client() -> Optional[OpenAI]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model_name = os.getenv("TEXT_MODEL_NAME", "").strip()
    if not api_key or not model_name:
        return None
    return OpenAI(api_key=api_key)



def _get_model_name() -> Optional[str]:
    model_name = os.getenv("TEXT_MODEL_NAME", "").strip()
    return model_name or None



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
        token = re.sub(r"\s+", "", token)
        token = re.sub(r"[^\w가-힣]", "", token)
        if len(token) < 2:
            continue
        if token not in seen:
            seen.add(token)
            result.append(token)

    return result[:10]



def _extract_location_keywords(location: str) -> list[str]:
    location = _clean_text(location)
    if not location:
        return []

    parts = [p for p in re.split(r"\s+", location) if p]
    compact = re.sub(r"\s+", "", location)

    result = []
    if parts:
        result.append(parts[-1])
    if len(parts) >= 2:
        result.append("".join(parts[-2:]))
        result.append(f"{parts[-1]}맛집")
        result.append(f"{parts[-1]}카페")
    if compact:
        result.append(compact)

    return _normalize_hashtags(result)



def _extract_business_category_keywords(business_category: str) -> list[str]:
    business_category = _clean_text(business_category)
    if not business_category:
        return []

    candidates = []
    compact = re.sub(r"\s+", "", business_category)
    split_parts = [p.strip() for p in re.split(r"[&/,·]|and", business_category) if p.strip()]
    candidates.append(compact)
    candidates.extend(split_parts)

    for key, tags in BUSINESS_TAG_MAP.items():
        if key in business_category:
            candidates.extend(tags)

    return _normalize_hashtags(candidates)



def _extract_extra_keywords(extra_prompt: Optional[str]) -> list[str]:
    text = _clean_text(extra_prompt)
    if not text:
        return []

    candidates = []
    mappings = {
        "인스타": ["인스타감성", "피드맛집"],
        "릴스": ["릴스맛집", "영상무드"],
        "봄": ["봄무드", "봄감성"],
        "여름": ["여름무드", "청량한분위기"],
        "가을": ["가을무드", "가을감성"],
        "겨울": ["겨울무드", "포근한분위기"],
    }
    for key, values in mappings.items():
        if key in text:
            candidates.extend(values)
    return _normalize_hashtags(candidates)



def _infer_time_phrase(recommended_concept: str) -> str:
    text = _clean_text(recommended_concept)
    if "저녁" in text:
        return "오늘 저녁"
    if "점심" in text:
        return "오늘 점심"
    if "브런치" in text:
        return "이번 주말"
    return "오늘"



def _infer_weather_phrase(weather_summary: str, season_context: str) -> str:
    weather_text = _clean_text(weather_summary)
    season_text = _clean_text(season_context)
    if "비" in weather_text:
        return "비 오는 날에도 부담 없이 생각나는"
    if "맑음" in weather_text or "대체로 맑음" in weather_text:
        return "기분 좋은 날 더 잘 어울리는"
    if "여름" in weather_text or "여름" in season_text:
        return "산뜻하게 즐기기 좋은"
    if "가을" in weather_text or "가을" in season_text:
        return "차분한 무드와 잘 어울리는"
    if "겨울" in weather_text or "겨울" in season_text:
        return "따뜻하게 즐기기 좋은"
    if "봄" in weather_text or "봄" in season_text:
        return "가볍게 즐기기 좋은"
    return "지금 분위기와 잘 어울리는"



def _pick_location_short(location: str) -> str:
    keywords = _extract_location_keywords(location)
    if keywords:
        return keywords[0]
    return _clean_text(location) or "근처"



def _trim_copy(text: str, max_len: int = 110) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([.!?]){2,}", r"\1", text)
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rstrip()
    last_space = cut.rfind(" ")
    if last_space > 35:
        cut = cut[:last_space]
    return cut.rstrip(" ,") + "..."



def _build_hashtags(
    purpose: str,
    business_category: str,
    menu_name: str,
    location: str,
    mood: Optional[str],
    season_context: str,
    extra_prompt: Optional[str] = None,
) -> list[str]:
    candidates = []
    candidates.append(menu_name)
    candidates.extend(_extract_business_category_keywords(business_category))
    candidates.extend(_extract_location_keywords(location))
    candidates.extend(_extract_extra_keywords(extra_prompt))

    for season, tags in SEASON_TAG_MAP.items():
        if season in season_context:
            candidates.extend(tags)
            break

    mood_text = _clean_text(mood)
    for key, tags in MOOD_TAG_MAP.items():
        if key in mood_text:
            candidates.extend(tags)
            break

    if purpose:
        purpose_map = {
            "방문 유도": ["방문추천"],
            "신메뉴 홍보": ["신메뉴", "신메뉴추천"],
            "이벤트 홍보": ["이벤트소식"],
            "매장 홍보": ["공간추천"],
        }
        candidates.extend(purpose_map.get(purpose, []))

    return _normalize_hashtags(candidates)[:7]



def _fallback_copy(
    purpose: str,
    business_category: str,
    menu_name: str,
    location: str,
    mood: Optional[str],
    weather_summary: str,
    season_context: str,
    recommended_concept: str,
    extra_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    location_short = _pick_location_short(location)
    time_phrase = _infer_time_phrase(recommended_concept)
    weather_phrase = _infer_weather_phrase(weather_summary, season_context)
    mood_text = _clean_text(mood)
    extra_text = _clean_text(extra_prompt)

    if purpose == "방문 유도":
        copy = f"{time_phrase}, {location_short}에서 {menu_name} 찾는다면 눈여겨봐 주세요. {weather_phrase} 가볍게 들르기 좋습니다."
    elif purpose == "신메뉴 홍보":
        copy = f"이번에 새롭게 준비한 {menu_name}. {weather_phrase} 지금 자연스럽게 찾게 되는 메뉴예요."
    elif purpose == "이벤트 홍보":
        copy = f"{menu_name}와 함께 분위기 좋게 즐기기 좋은 타이밍이에요. 이번 소식도 함께 확인해 보세요."
    elif purpose == "매장 홍보":
        copy = f"{location_short}에서 {business_category} 찾는다면, {menu_name}와 함께 공간 분위기까지 편하게 즐겨보세요."
    else:
        variants = PURPOSE_VARIANTS.get(purpose, ["지금 눈여겨볼 만한"])
        copy = f"{variants[0]} {menu_name}. {weather_phrase} 부담 없이 떠오르는 메뉴예요."

    if mood_text:
        if "따뜻한" in mood_text or "포근" in mood_text:
            copy += " 포근한 무드 좋아하는 분들께 특히 잘 어울려요."
        elif "트렌디" in mood_text or "힙" in mood_text:
            copy += " 피드에 올렸을 때도 분위기가 예쁘게 살아납니다."
        elif "깔끔" in mood_text:
            copy += " 군더더기 없는 분위기로 더 매력적이에요."
        elif "프리미엄" in mood_text:
            copy += " 차분하고 세련된 느낌으로 즐기기 좋습니다."

    if extra_text:
        if "인스타" in extra_text:
            copy += " 사진으로 남기기에도 좋아요."
        elif "릴스" in extra_text:
            copy += " 짧은 영상 컷에도 잘 어울립니다."
        elif "홍보" in extra_text and "봄" in extra_text:
            copy += " 계절감 있는 분위기까지 함께 전하기 좋습니다."

    copy = _trim_copy(copy)
    hashtags = _build_hashtags(
        purpose=purpose,
        business_category=business_category,
        menu_name=menu_name,
        location=location,
        mood=mood,
        season_context=season_context,
        extra_prompt=extra_prompt,
    )
    return {"copy": copy, "hashtags": hashtags, "error": None}



def generate_marketing_copy(
    purpose: str,
    business_category: str,
    menu_name: str,
    location: str,
    mood: Optional[str],
    weather_summary: str,
    season_context: str,
    recommended_concept: str,
    extra_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    _wandb_log_safe({
        "trace_stage": "text_generator_start",
        "purpose": purpose,
        "business_category": business_category,
        "menu_name": menu_name,
        "location": location,
        "has_mood": bool(mood),
        "has_extra_prompt": bool(extra_prompt),
    })

    client = _build_client()
    model_name = _get_model_name()

    if client is None or model_name is None:
        _wandb_log_safe({
            "trace_stage": "text_generator_fallback_no_model",
            "purpose": purpose,
            "menu_name": menu_name,
        })
        return _fallback_copy(
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

    system_prompt, user_prompt = get_full_prompt(
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

    try:
        request_kwargs = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        if not model_name.startswith("gpt-5"):
            request_kwargs["temperature"] = 0.9

        response = client.chat.completions.create(**request_kwargs)

        _wandb_log_safe({
            "trace_stage": "text_generator_model_called",
            "model_name": model_name,
            "purpose": purpose,
            "menu_name": menu_name,
        })

        content = response.choices[0].message.content or "{}"
        data = json.loads(content)

        copy_text = _trim_copy(_clean_text(data.get("copy")))
        hashtags = _normalize_hashtags(data.get("hashtags", []))

        if not copy_text:
            fallback = _fallback_copy(
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
            fallback["error"] = "model returned empty copy"
            return fallback

        if not hashtags:
            hashtags = _build_hashtags(
                purpose=purpose,
                business_category=business_category,
                menu_name=menu_name,
                location=location,
                mood=mood,
                season_context=season_context,
                extra_prompt=extra_prompt,
            )

        return {"copy": copy_text, "hashtags": hashtags[:7], "error": None}

    except Exception as e:
        fallback = _fallback_copy(
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
        fallback["error"] = str(e)
        return fallback
