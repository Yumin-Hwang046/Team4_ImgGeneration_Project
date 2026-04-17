import json
import os
import re
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI

from backend.text_generator.prompt_templates import get_full_prompt

load_dotenv()


def _build_client() -> Optional[OpenAI]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model_name = os.getenv("TEXT_MODEL_NAME", "").strip()

    # 모델명을 억지로 추정하지 않고, 둘 다 있을 때만 실제 호출
    if not api_key or not model_name:
        return None

    return OpenAI(api_key=api_key)


def _get_model_name() -> Optional[str]:
    model_name = os.getenv("TEXT_MODEL_NAME", "").strip()
    return model_name or None


def _clean_text(value: Optional[str]) -> str:
    return (value or "").strip()


def _normalize_hashtags(raw: Any) -> list[str]:
    """
    프론트는 #{tag} 형태로 렌더링하므로
    백엔드는 ['맛집', '카페']처럼 # 없는 배열로 맞춘다.
    """
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

        if not token:
            continue

        if token not in seen:
            seen.add(token)
            result.append(token)

    return result[:10]


def _extract_location_keywords(location: str) -> list[str]:
    location = _clean_text(location)
    if not location:
        return []

    compact = re.sub(r"\s+", "", location)
    parts = [p for p in re.split(r"\s+", location) if p]

    result = []
    if compact:
        result.append(compact)

    if parts:
        result.append(parts[-1])

    if len(parts) >= 2:
        result.append("".join(parts[-2:]))

    return _normalize_hashtags(result)


def _extract_business_category_keywords(business_category: str) -> list[str]:
    business_category = _clean_text(business_category)
    if not business_category:
        return []

    compact = re.sub(r"\s+", "", business_category)
    split_parts = [p.strip() for p in re.split(r"[&/,·]|and", business_category) if p.strip()]

    candidates = [compact]
    candidates.extend(split_parts)

    if "카페" in business_category and "베이커리" in business_category:
        candidates.extend(["카페", "베이커리"])

    return _normalize_hashtags(candidates)


def _infer_time_phrase(recommended_concept: str) -> str:
    text = _clean_text(recommended_concept)

    if "저녁 시간대" in text:
        return "오늘 저녁"
    if "점심 시간대" in text:
        return "오늘 점심"
    return "오늘"


def _infer_weather_phrase(weather_summary: str, season_context: str) -> str:
    weather_text = _clean_text(weather_summary)
    season_text = _clean_text(season_context)

    if "비" in weather_text:
        return "비 오는 날에도 생각나는"
    if "맑음" in weather_text or "대체로 맑음" in weather_text:
        return "기분 좋은 날 더 잘 어울리는"
    if "봄" in weather_text or "봄" in season_text:
        return "포근한 분위기에 잘 어울리는"
    if "여름" in weather_text or "여름" in season_text:
        return "산뜻하게 즐기기 좋은"
    if "가을" in weather_text or "가을" in season_text:
        return "감성적인 무드와 잘 맞는"
    if "겨울" in weather_text or "겨울" in season_text:
        return "따뜻하게 즐기기 좋은"
    return "지금 분위기와 잘 어울리는"


def _build_hashtags(
    purpose: str,
    business_category: str,
    menu_name: str,
    location: str,
    mood: Optional[str],
    season_context: str,
) -> list[str]:
    candidates = []

    candidates.extend(_extract_business_category_keywords(business_category))
    candidates.append(menu_name)
    candidates.extend(_extract_location_keywords(location))

    if purpose:
        candidates.append(purpose)

    if mood:
        candidates.append(mood)

    if "봄" in season_context:
        candidates.extend(["봄디저트", "봄카페"])
    elif "여름" in season_context:
        candidates.extend(["여름디저트", "여름카페"])
    elif "가을" in season_context:
        candidates.extend(["가을감성", "가을카페"])
    elif "겨울" in season_context:
        candidates.extend(["겨울디저트", "겨울카페"])

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
    """
    OPENAI_API_KEY / TEXT_MODEL_NAME이 없거나
    모델 호출 실패 시에도 바로 써먹을 수 있는 문구를 만든다.
    """
    location_keywords = _extract_location_keywords(location)
    location_short = location_keywords[1] if len(location_keywords) > 1 else _clean_text(location)
    time_phrase = _infer_time_phrase(recommended_concept)
    weather_phrase = _infer_weather_phrase(weather_summary, season_context)
    mood_text = _clean_text(mood)
    extra_text = _clean_text(extra_prompt)

    purpose_text = _clean_text(purpose)

    if purpose_text == "방문 유도":
        copy = f"{time_phrase}, {location_short}에서 {menu_name} 생각난다면 여기예요. {weather_phrase} 한 컷까지 챙기기 좋은 타이밍."
    elif purpose_text == "신메뉴 홍보":
        copy = f"이번에 새롭게 소개하는 {menu_name}. {weather_phrase} 지금 눈여겨보기 좋은 메뉴예요."
    elif purpose_text == "이벤트 홍보":
        copy = f"{menu_name}와 함께 즐기기 좋은 분위기, 지금 체크해둘 타이밍이에요."
    elif purpose_text == "매장 홍보":
        copy = f"{location_short}에서 분위기 좋은 {business_category} 찾는다면, {menu_name}부터 눈여겨봐 주세요."
    else:
        copy = f"{menu_name}, {weather_phrase} 지금 떠오르기 좋은 메뉴예요."

    # 무드/추가요청 반영은 문장을 과하게 늘리지 않는 선에서만 보정
    if mood_text:
        if "따뜻한" in mood_text or "포근" in mood_text:
            copy += " 따뜻한 감성 좋아하면 더 잘 맞아요."
        elif "힙" in mood_text or "트렌디" in mood_text:
            copy += " 요즘 감성으로 올리기에도 좋아요."
        elif "깔끔" in mood_text:
            copy += " 군더더기 없이 깔끔한 무드가 매력적이에요."

    if extra_text:
        if "인스타" in extra_text:
            copy += " 피드에 올렸을 때 분위기까지 챙기기 좋습니다."
        elif "릴스" in extra_text:
            copy += " 짧은 영상 컷으로도 잘 살아나요."

    # 너무 길어지면 잘라서 안정화
    copy = re.sub(r"\s+", " ", copy).strip()
    if len(copy) > 110:
        copy = copy[:107].rstrip() + "..."

    hashtags = _build_hashtags(
        purpose=purpose,
        business_category=business_category,
        menu_name=menu_name,
        location=location,
        mood=mood,
        season_context=season_context,
    )

    return {
        "copy": copy,
        "hashtags": hashtags,
        "error": None,
    }


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
    """
    generations.py -> ai_clients.py 에서 직접 사용할
    텍스트 생성 표준 함수.
    """
    client = _build_client()
    model_name = _get_model_name()

    # 현재 프로젝트에서는 이 분기가 실제로 자주 실행될 가능성이 높음
    if client is None or model_name is None:
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
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        data = json.loads(content)

        copy_text = _clean_text(data.get("copy"))
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
            )

        return {
            "copy": copy_text,
            "hashtags": hashtags,
            "error": None,
        }

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


def generate_ad_copy(image_analysis_text: str, mood_key: str) -> dict:
    """
    구형 text_router 호환용 래퍼.
    """
    return generate_marketing_copy(
        purpose="매장 홍보",
        business_category="일반 매장",
        menu_name=image_analysis_text[:30] or "대표 메뉴",
        location="지역 미지정",
        mood=mood_key,
        weather_summary="날씨 정보 없음",
        season_context="시즌 정보 없음",
        recommended_concept=image_analysis_text,
        extra_prompt=None,
    )


if __name__ == "__main__":
    result = generate_marketing_copy(
        purpose="방문 유도",
        business_category="카페 & 베이커리",
        menu_name="딸기 케이크",
        location="서울특별시 종로구",
        mood="따뜻한 감성",
        weather_summary="봄 예상 날씨, 온화함 / 야외활동 적합",
        season_context="봄 시즌, 야외활동 증가, 산뜻한 분위기 선호",
        recommended_concept="계절감이 드러나는 카페 무드 중심 / 저녁 시간대 / 무드 반영: 따뜻한 감성 / 대표 메뉴 강조: 딸기 케이크",
        extra_prompt="인스타 업로드용 봄 감성 디저트 홍보",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))