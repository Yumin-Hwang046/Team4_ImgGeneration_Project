import json
import os
import re
import uuid
from datetime import datetime, date
from typing import Optional, List
from pathlib import Path
from urllib.parse import quote, unquote
import shutil

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

try:
    import wandb
except Exception:
    wandb = None

# backend/.env 읽기
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

from db import get_db, SessionLocal
from models import Generation, GeneratedImage, User, UserProfile, WeatherDaily
from schemas import (
    GenerationCreate,
    GenerationUpdate,
    GenerationResponse,
    GenerationDetailResponse,
    GenerationListItem,
    GeneratedImageItem,
    RegenerateImageResponse,
)
from auth import get_current_user
from ai_adapter import normalize_image_result, normalize_text_result
from ai_clients import call_image_generator, call_text_generator


router = APIRouter(prefix="/generations", tags=["generations"])

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
GENERATED_DIR = BASE_DIR / "generated"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

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
            wandb.init(project=project, entity=entity, job_type="generation-flow")
        else:
            wandb.init(project=project, job_type="generation-flow")
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


def to_public_media_url(path_str: Optional[str]) -> Optional[str]:
    if not path_str:
        return None

    path = Path(path_str)

    try:
        resolved = path.resolve()
    except Exception:
        return path_str

    try:
        rel = resolved.relative_to(GENERATED_DIR.resolve())
        return f"/media/generated/{quote(rel.as_posix())}"
    except Exception:
        pass

    try:
        rel = resolved.relative_to(UPLOAD_DIR.resolve())
        return f"/media/uploads/{quote(rel.as_posix())}"
    except Exception:
        pass

    return path_str


def parse_target_datetime(date_str: str, time_str: Optional[str]) -> datetime:
    if time_str:
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return datetime.strptime(f"{date_str} 12:00", "%Y-%m-%d %H:%M")


def get_season_context(target_dt: datetime) -> str:
    month = target_dt.month

    if month in [3, 4, 5]:
        return "봄 시즌, 야외활동 증가, 산뜻한 분위기 선호"
    if month in [6, 7, 8]:
        return "여름 시즌, 시원함/청량감/더위 회피 니즈 증가"
    if month in [9, 10, 11]:
        return "가을 시즌, 따뜻함/감성/저녁 방문 유도에 적합"
    return "겨울 시즌, 온기/포근함/실내 체류 강조에 적합"


def weather_code_to_text(code: int) -> str:
    weather_map = {
        0: "맑음",
        1: "대체로 맑음",
        2: "부분적으로 흐림",
        3: "흐림",
        45: "안개",
        48: "짙은 안개",
        51: "약한 이슬비",
        53: "보통 이슬비",
        55: "강한 이슬비",
        61: "약한 비",
        63: "비",
        65: "강한 비",
        71: "약한 눈",
        73: "눈",
        75: "강한 눈",
        80: "소나기",
        81: "강한 소나기",
        82: "매우 강한 소나기",
        95: "뇌우",
    }
    return weather_map.get(code, "날씨 정보 없음")


def normalize_location_for_weather(location: str) -> str:
    value = (location or "").strip()
    if not value:
        return "서울"

    value = re.sub(r"\s+", " ", value).strip()

    noisy_tokens = [
        "대한민국", "한국", "매장", "가게", "본점", "지점",
        "인스타", "홍보", "감성", "따뜻한", "트렌디", "프리미엄", "깔끔한",
    ]
    for token in noisy_tokens:
        value = value.replace(token, "").strip()

    value = re.sub(r"\s+", " ", value).strip()

    parts = value.split()
    if len(parts) >= 3:
        value = " ".join(parts[:3])
    elif len(parts) >= 2:
        value = " ".join(parts[:2])

    replacements = {
        "서울특별시": "서울",
        "부산광역시": "부산",
        "대구광역시": "대구",
        "인천광역시": "인천",
        "광주광역시": "광주",
        "대전광역시": "대전",
        "울산광역시": "울산",
        "세종특별자치시": "세종",
        "경기도": "경기",
        "강원특별자치도": "강원",
        "충청북도": "충북",
        "충청남도": "충남",
        "전북특별자치도": "전북",
        "전라북도": "전북",
        "전라남도": "전남",
        "경상북도": "경북",
        "경상남도": "경남",
        "제주특별자치도": "제주",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(r"\s+", " ", value).strip()
    return value or "서울"


def geocode_location(location: str) -> tuple[float, float]:
    normalized = normalize_location_for_weather(location)

    candidates = [normalized]
    parts = normalized.split()
    if len(parts) >= 2:
        candidates.append(" ".join(parts[:2]))
    if len(parts) >= 1:
        candidates.append(parts[0])

    seen = set()
    deduped_candidates = []
    for c in candidates:
        c = c.strip()
        if c and c not in seen:
            seen.add(c)
            deduped_candidates.append(c)

    last_error = None

    for candidate in deduped_candidates:
        try:
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {
                "name": candidate,
                "count": 1,
                "language": "ko",
                "format": "json",
            }

            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results")
            if results:
                lat = results[0]["latitude"]
                lon = results[0]["longitude"]
                return lat, lon
        except Exception as e:
            last_error = e
            continue

    raise HTTPException(status_code=404, detail=f"지역을 찾을 수 없습니다: {normalized}") from last_error


def get_seasonal_weather_fallback(target_dt: datetime) -> str:
    month = target_dt.month
    hour = target_dt.hour

    time_context = (
        "점심 이후 외출 수요가 있는 시간대" if 11 <= hour <= 15
        else "저녁 분위기가 살아나는 시간대" if 17 <= hour <= 21
        else "일반 시간대"
    )

    if month in [3, 4, 5]:
        return f"봄 시즌, 온화한 날씨 / 산뜻한 외출 무드 / {time_context}"
    if month in [6, 7, 8]:
        return f"여름 시즌, 더운 날씨 / 시원한 실내·청량한 메뉴 선호 / {time_context}"
    if month in [9, 10, 11]:
        return f"가을 시즌, 선선한 날씨 / 감성적인 방문 유도에 적합 / {time_context}"
    return f"겨울 시즌, 추운 날씨 / 따뜻하고 포근한 분위기 강조 / {time_context}"


def get_profile_region_text(profile: Optional[UserProfile]) -> Optional[str]:
    if not profile:
        return None

    road = (profile.road_address or "").strip()
    if road:
        return road

    parts = [
        (profile.sido or "").strip(),
        (profile.sigungu or "").strip(),
        (profile.emd or "").strip(),
    ]
    region = " ".join([p for p in parts if p])
    return region or None


def looks_like_invalid_location(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True

    bad_keywords = [
        "감성", "분위기", "따뜻한", "트렌디", "프리미엄", "홍보",
        "이벤트", "메뉴", "카페", "베이커리", "한식", "디저트"
    ]
    return any(k in t for k in bad_keywords) and len(t.split()) <= 3


def resolve_generation_location(
    db: Session,
    user_id: int,
    requested_location: str,
) -> str:
    requested = (requested_location or "").strip()

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    profile_region = get_profile_region_text(profile)

    if not requested:
        return profile_region or "서울특별시"

    if looks_like_invalid_location(requested) and profile_region:
        return profile_region

    return requested


def get_weather_summary_from_storage_for_generation(
    db: Session,
    user_id: int,
    target_dt: datetime,
) -> Optional[str]:
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .first()
    )
    if not profile:
        return None

    row = (
        db.query(WeatherDaily)
        .filter(
            WeatherDaily.user_profile_id == profile.id,
            WeatherDaily.weather_date == target_dt.date(),
        )
        .first()
    )

    if row and row.weather_summary:
        return row.weather_summary

    return None


def classify_weather_flags(weather_text: str, temperature, precipitation_probability) -> dict:
    temp = None
    pop = None

    try:
        temp = float(temperature)
    except Exception:
        pass

    try:
        pop = int(float(precipitation_probability))
    except Exception:
        pass

    is_rainy = any(keyword in weather_text for keyword in ["비", "소나기", "이슬비", "뇌우"])
    is_snowy = "눈" in weather_text
    is_clear = any(keyword in weather_text for keyword in ["맑음", "대체로 맑음"])
    is_cloudy = any(keyword in weather_text for keyword in ["흐림", "안개"])

    is_hot = temp is not None and temp >= 26
    is_warm = temp is not None and 18 <= temp < 26
    is_cold = temp is not None and temp <= 9

    high_precip = pop is not None and pop >= 50

    return {
        "temp": temp,
        "pop": pop,
        "is_rainy": is_rainy,
        "is_snowy": is_snowy,
        "is_clear": is_clear,
        "is_cloudy": is_cloudy,
        "is_hot": is_hot,
        "is_warm": is_warm,
        "is_cold": is_cold,
        "high_precip": high_precip,
    }


def build_weather_summary(weather_text: str, temperature, precipitation_probability) -> str:
    flags = classify_weather_flags(weather_text, temperature, precipitation_probability)

    temp_text = f"{int(flags['temp'])}°C" if flags["temp"] is not None else "기온 정보 없음"
    pop_text = f"강수확률 {flags['pop']}%" if flags["pop"] is not None else "강수확률 정보 없음"

    extra_context = ""
    if flags["is_rainy"] or flags["high_precip"]:
        extra_context = "실내 머무르기 좋은 분위기"
    elif flags["is_clear"] and flags["is_warm"]:
        extra_context = "산뜻하게 외출하기 좋은 분위기"
    elif flags["is_clear"]:
        extra_context = "밝은 자연광이 잘 어울리는 분위기"
    elif flags["is_hot"]:
        extra_context = "시원한 메뉴와 실내 선호도가 높아지는 날씨"
    elif flags["is_cold"]:
        extra_context = "따뜻한 메뉴와 포근한 무드가 잘 어울리는 날씨"
    elif flags["is_cloudy"]:
        extra_context = "차분한 무드 연출에 어울리는 날씨"

    if extra_context:
        return f"{weather_text}, {temp_text}, {pop_text} / {extra_context}"
    return f"{weather_text}, {temp_text}, {pop_text}"


def get_weather_summary_for_generation(
    db: Session,
    user_id: int,
    location: str,
    target_dt: datetime,
) -> str:
    stored_summary = get_weather_summary_from_storage_for_generation(
        db=db,
        user_id=user_id,
        target_dt=target_dt,
    )
    if stored_summary:
        return stored_summary

    live_summary = get_weather_summary(location, target_dt)
    if "날씨 조회 실패" not in live_summary:
        return live_summary

    return get_seasonal_weather_fallback(target_dt)


def get_weather_summary(location: str, target_dt: datetime) -> str:
    try:
        lat, lon = geocode_location(location)

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,weather_code,precipitation_probability",
            "timezone": "Asia/Seoul",
        }

        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        codes = hourly.get("weather_code", [])
        pops = hourly.get("precipitation_probability", [])

        if not times:
            return "날씨 조회 실패(기본 추천 로직으로 진행)"

        target_hour = target_dt.strftime("%Y-%m-%dT%H:00")

        if target_hour in times:
            idx = times.index(target_hour)
        else:
            target_date_prefix = target_dt.strftime("%Y-%m-%dT")
            same_day_indices = [i for i, t in enumerate(times) if t.startswith(target_date_prefix)]
            idx = same_day_indices[0] if same_day_indices else 0

        weather_text = weather_code_to_text(codes[idx]) if idx < len(codes) else "정보 없음"
        temp = temps[idx] if idx < len(temps) else None
        pop = pops[idx] if idx < len(pops) else None

        return build_weather_summary(weather_text, temp, pop)

    except Exception:
        return "날씨 조회 실패(기본 추천 로직으로 진행)"


def recommend_concept(
    business_category: str,
    menu_name: str,
    purpose: str,
    mood: Optional[str],
    weather_summary: str,
    season_context: str,
    target_dt: datetime,
) -> str:
    hour = target_dt.hour

    time_context = (
        "점심 시간대" if 11 <= hour <= 14
        else "오후 시간대" if 15 <= hour <= 16
        else "저녁 시간대" if 17 <= hour <= 21
        else "일반 시간대"
    )

    business_text = (business_category or "").strip()
    menu_text = (menu_name or "").strip()

    is_rainy = any(keyword in weather_summary for keyword in ["비", "소나기", "이슬비", "뇌우"])
    is_snowy = "눈" in weather_summary
    is_clear = any(keyword in weather_summary for keyword in ["맑음", "대체로 맑음"])
    is_cloudy = any(keyword in weather_summary for keyword in ["흐림", "안개"])
    is_hot = any(keyword in weather_summary for keyword in ["시원한 메뉴", "더운 날씨"])
    is_cold = any(keyword in weather_summary for keyword in ["따뜻한 메뉴", "추운 날씨"])

    if "카페" in business_text or "디저트" in business_text or "베이커리" in business_text:
        if is_rainy:
            base = "비 오는 날에도 머물고 싶어지는 실내 감성, 따뜻한 음료·디저트 중심"
        elif is_snowy:
            base = "포근한 계절감이 드러나는 겨울 디저트·음료 무드 중심"
        elif is_clear and hour < 17:
            base = "햇살과 자연광이 잘 어울리는 밝은 디저트·음료 중심"
        elif is_clear and hour >= 17:
            base = "맑은 날 마무리에 어울리는 편안한 카페 무드 중심"
        elif is_hot:
            base = "시원한 음료와 가벼운 디저트가 잘 어울리는 청량한 무드 중심"
        elif is_cold:
            base = "따뜻한 메뉴와 포근한 실내 분위기가 잘 살아나는 무드 중심"
        elif is_cloudy:
            base = "차분한 분위기와 감성적인 톤이 잘 어울리는 카페 무드 중심"
        else:
            base = "계절감과 공간 무드를 함께 살리는 카페·디저트 중심"

    elif "한식" in business_text or "분식" in business_text or "식당" in business_text:
        if is_rainy:
            base = "날씨 영향으로 실내 식사 선호도가 높아지는 날, 든든한 한 끼 중심"
        elif is_cold:
            base = "따뜻하고 든든한 메뉴 만족감을 강조하는 한 끼 중심"
        elif is_hot:
            base = "부담 없이 즐기기 좋은 식사와 편안한 실내 중심"
        else:
            base = "한 끼 만족감과 메뉴 매력을 강조하는 실사용 유입형 홍보"

    elif "주점" in business_text or "이자카야" in business_text or "술집" in business_text:
        if hour >= 18:
            if is_rainy or is_cloudy:
                base = "저녁 모임과 분위기 있는 실내 컷에 어울리는 감성 중심"
            else:
                base = "퇴근 후 가볍게 찾기 좋은 저녁 모임 무드 중심"
        else:
            base = "캐주얼한 술자리 예고형 콘텐츠"

    else:
        if is_rainy:
            base = "날씨 영향을 반영한 실내 방문 유도형 콘텐츠"
        elif is_clear:
            base = "밝고 산뜻한 분위기의 메뉴 중심 홍보 이미지"
        else:
            base = "메뉴 중심의 실사용 유입형 홍보 이미지"

    purpose_hint = {
        "방문 유도": "지금 들르기 좋은 이유 강조",
        "신메뉴 홍보": "새로운 포인트 강조",
        "이벤트 홍보": "지금 확인할 이유 강조",
        "매장 홍보": "공간 분위기와 메뉴 매력 균형 강조",
    }.get(purpose, "목적에 맞는 매력 포인트 강조")

    mood_part = f"무드 반영: {mood}" if mood else season_context

    return (
        f"{base} / {time_context} / {purpose_hint} / "
        f"{mood_part} / 대표 메뉴 강조: {menu_text}"
    )


def safe_load_hashtags(value) -> list:
    if not value:
        return []

    if isinstance(value, list):
        return value

    try:
        return json.loads(value)
    except Exception:
        return []


def get_next_version_no(db: Session, generation_id: int) -> int:
    latest = (
        db.query(GeneratedImage)
        .filter(GeneratedImage.generation_id == generation_id)
        .order_by(GeneratedImage.version_no.desc())
        .first()
    )
    return 1 if not latest else latest.version_no + 1


def process_generation_task(
    generation_id: int,
    purpose: str,
    business_category: str,
    menu_name: str,
    location: str,
    target_date: str,
    target_time: Optional[str],
    mood: Optional[str],
    extra_prompt: Optional[str],
    uploaded_filename: Optional[str] = None,
):
    db = SessionLocal()

    try:
        generation = db.query(Generation).filter(Generation.id == generation_id).first()
        if not generation:
            return

        _wandb_log_safe({
            "trace_stage": "generation_task_start",
            "generation_id": generation_id,
            "purpose": purpose,
            "business_category": business_category,
            "menu_name": menu_name,
            "raw_location": location,
            "has_uploaded_image": bool(uploaded_filename),
        })

        target_dt = parse_target_datetime(target_date, target_time)

        resolved_location = resolve_generation_location(
            db=db,
            user_id=generation.user_id,
            requested_location=location,
        )

        weather_summary = get_weather_summary_for_generation(
            db=db,
            user_id=generation.user_id,
            location=resolved_location,
            target_dt=target_dt,
        )

        season_context = get_season_context(target_dt)

        recommended_concept = recommend_concept(
            business_category=business_category,
            menu_name=menu_name,
            purpose=purpose,
            mood=mood,
            weather_summary=weather_summary,
            season_context=season_context,
            target_dt=target_dt,
        )

        _wandb_log_safe({
            "trace_stage": "generation_context_ready",
            "generation_id": generation_id,
            "resolved_location": resolved_location,
            "weather_summary": weather_summary,
            "recommended_concept": recommended_concept,
        })

        original_image_url = None
        source_image_path = None

        if uploaded_filename:
            original_image_url = to_public_media_url(uploaded_filename)
            source_image_path = uploaded_filename
            extra_info = f"[IMAGE_ANALYSIS] 업로드 이미지 분석 완료: {uploaded_filename}\n[USER_PROMPT] {extra_prompt or ''}"
        else:
            extra_info = f"[NO_UPLOAD_IMAGE]\n[USER_PROMPT] {extra_prompt or ''}"

        raw_image_result = call_image_generator(
            business_category=business_category,
            menu_name=menu_name,
            location=resolved_location,
            mood=mood,
            recommended_concept=recommended_concept,
            extra_prompt=extra_prompt,
            image_path=source_image_path,
        )
        image_result = normalize_image_result(raw_image_result)

        if not image_result["success"]:
            _wandb_log_safe({
                "trace_stage": "generation_image_fail",
                "generation_id": generation_id,
                "error": image_result.get("error"),
            })

            generation.generation_status = "FAILED"
            generation.extra_info = (
                (generation.extra_info or "")
                + "\n[ERROR] 이미지 처리 실패"
                + f"\n[DETAIL] {image_result.get('error')}"
            )
            print("[GENERATION][IMAGE][FAIL]", image_result)
            db.commit()
            return

        generated_image_url = to_public_media_url(image_result["image_url"])

        raw_text_result = call_text_generator(
            purpose=purpose,
            business_category=business_category,
            menu_name=menu_name,
            location=resolved_location,
            mood=mood,
            weather_summary=weather_summary,
            season_context=season_context,
            recommended_concept=recommended_concept,
            extra_prompt=extra_prompt,
        )
        text_result = normalize_text_result(raw_text_result)

        if not text_result["success"]:
            _wandb_log_safe({
                "trace_stage": "generation_text_fail",
                "generation_id": generation_id,
                "error": text_result.get("error"),
            })

            generation.generation_status = "FAILED"
            generation.extra_info = (
                (generation.extra_info or "")
                + "\n[ERROR] 문구 생성 실패"
                + f"\n[DETAIL] {text_result.get('error')}"
            )
            print("[GENERATION][TEXT][FAIL]", text_result)
            db.commit()
            return

        generated_copy = text_result["copy"]
        hashtags = text_result["hashtags"]

        final_image_url = None

        generation.purpose = purpose
        generation.business_category = business_category
        generation.menu_name = menu_name
        generation.mood = mood
        generation.location = resolved_location
        generation.target_datetime = target_dt
        generation.extra_info = extra_info
        generation.generated_copy = generated_copy
        generation.hashtags = json.dumps(hashtags, ensure_ascii=False)
        generation.weather_summary = weather_summary
        generation.recommended_concept = recommended_concept
        generation.original_image_url = original_image_url
        generation.generated_image_url = generated_image_url
        generation.generation_status = "SUCCESS"

        version_no = get_next_version_no(db, generation.id)

        generated_image = GeneratedImage(
            generation_id=generation.id,
            image_url=generated_image_url,
            final_image_url=final_image_url,
            prompt_used=image_result.get("prompt_used") or recommended_concept,
            version_no=version_no,
            image_type="generated",
            status="SUCCESS",
        )

        db.add(generated_image)

        _wandb_log_safe({
            "trace_stage": "generation_task_success",
            "generation_id": generation_id,
            "copy_length": len(generated_copy or ""),
            "hashtags_count": len(hashtags or []),
            "generated_image_url": generated_image_url,
        })

        db.commit()

    except Exception as e:
        _wandb_log_safe({
            "trace_stage": "generation_task_exception",
            "generation_id": generation_id,
            "error": str(e),
        })

        generation = db.query(Generation).filter(Generation.id == generation_id).first()
        if generation:
            generation.generation_status = "FAILED"
            generation.extra_info = (generation.extra_info or "") + f"\n[ERROR] {str(e)}"
            db.commit()
    finally:
        db.close()


def process_regenerate_task(generation_id: int):
    db = SessionLocal()

    try:
        generation = db.query(Generation).filter(Generation.id == generation_id).first()
        if not generation:
            return

        _wandb_log_safe({
            "trace_stage": "regenerate_task_start",
            "generation_id": generation_id,
        })

        generation.generation_status = "PENDING"
        db.commit()

        recommended_concept = generation.recommended_concept or "기본 추천 컨셉"

        source_image_path = None
        if generation.original_image_url and generation.original_image_url.startswith("/media/uploads/"):
            relative_path = unquote(generation.original_image_url.replace("/media/uploads/", "", 1))
            candidate_path = UPLOAD_DIR / relative_path
            if candidate_path.exists():
                source_image_path = str(candidate_path)

        if not source_image_path:
            _wandb_log_safe({
                "trace_stage": "regenerate_task_missing_source",
                "generation_id": generation_id,
            })

            generation.generation_status = "FAILED"
            generation.extra_info = (
                (generation.extra_info or "")
                + "\n[ERROR] 재생성 실패: 원본 업로드 이미지를 찾을 수 없습니다."
            )
            db.commit()
            return

        raw_image_result = call_image_generator(
            business_category=generation.business_category or "기타",
            menu_name=generation.menu_name or "메뉴",
            location=generation.location or "지역",
            mood=generation.mood,
            recommended_concept=recommended_concept,
            extra_prompt=None,
            image_path=source_image_path,
        )
        image_result = normalize_image_result(raw_image_result)

        if not image_result["success"]:
            generation.generation_status = "FAILED"
            generation.extra_info = (generation.extra_info or "") + "\n[ERROR] 재생성 실패"
            db.commit()
            return

        version_no = get_next_version_no(db, generation.id)
        public_image_url = to_public_media_url(image_result["image_url"])

        new_image = GeneratedImage(
            generation_id=generation.id,
            image_url=public_image_url,
            final_image_url=None,
            prompt_used=image_result.get("prompt_used") or recommended_concept,
            version_no=version_no,
            image_type="generated",
            status="SUCCESS",
        )

        generation.generated_image_url = public_image_url
        generation.generation_status = "SUCCESS"

        db.add(new_image)

        _wandb_log_safe({
            "trace_stage": "regenerate_task_success",
            "generation_id": generation_id,
            "public_image_url": public_image_url,
        })

        db.commit()

    except Exception as e:
        _wandb_log_safe({
            "trace_stage": "regenerate_task_exception",
            "generation_id": generation_id,
            "error": str(e),
        })

        generation = db.query(Generation).filter(Generation.id == generation_id).first()
        if generation:
            generation.generation_status = "FAILED"
            generation.extra_info = (generation.extra_info or "") + f"\n[ERROR] {str(e)}"
            db.commit()
    finally:
        db.close()


@router.post("", response_model=GenerationResponse)
def create_generation(
    payload: GenerationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    generation = Generation(
        user_id=current_user.id,
        purpose=payload.purpose,
        mood=payload.mood,
        extra_info=payload.extra_info,
        generated_copy=payload.generated_copy,
        hashtags=json.dumps(payload.hashtags or [], ensure_ascii=False),
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)

    generation.hashtags = safe_load_hashtags(generation.hashtags)
    return generation


@router.get("", response_model=List[GenerationListItem])
def list_generations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(Generation)
        .filter(Generation.user_id == current_user.id)
        .order_by(Generation.created_at.desc())
        .all()
    )
    return rows


@router.get("/{generation_id}", response_model=GenerationDetailResponse)
def get_generation(
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(Generation)
        .filter(Generation.id == generation_id, Generation.user_id == current_user.id)
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Not found")

    row.hashtags = safe_load_hashtags(row.hashtags)
    return row


@router.get("/{generation_id}/images", response_model=List[GeneratedImageItem])
def get_generation_images(
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    generation = (
        db.query(Generation)
        .filter(Generation.id == generation_id, Generation.user_id == current_user.id)
        .first()
    )

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    rows = (
        db.query(GeneratedImage)
        .filter(GeneratedImage.generation_id == generation_id)
        .order_by(GeneratedImage.version_no.asc())
        .all()
    )
    return rows


@router.put("/{generation_id}", response_model=GenerationResponse)
def update_generation(
    generation_id: int,
    payload: GenerationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(Generation)
        .filter(Generation.id == generation_id, Generation.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Generation not found")

    if payload.purpose is not None:
        row.purpose = payload.purpose
    if payload.mood is not None:
        row.mood = payload.mood
    if payload.extra_info is not None:
        row.extra_info = payload.extra_info
    if payload.generated_copy is not None:
        row.generated_copy = payload.generated_copy
    if payload.hashtags is not None:
        row.hashtags = json.dumps(payload.hashtags, ensure_ascii=False)

    db.commit()
    db.refresh(row)

    row.hashtags = safe_load_hashtags(row.hashtags)
    return row


@router.delete("/{generation_id}", response_model=dict)
def delete_generation(
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(Generation)
        .filter(Generation.id == generation_id, Generation.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Generation not found")

    db.delete(row)
    db.commit()
    return {"message": "삭제되었습니다."}


@router.post("/run")
async def run_generation(
    background_tasks: BackgroundTasks,
    purpose: str = Form(...),
    business_category: str = Form(...),
    menu_name: str = Form(...),
    location: str = Form(...),
    target_date: str = Form(...),
    target_time: Optional[str] = Form(None),
    mood: Optional[str] = Form(None),
    extra_prompt: Optional[str] = Form(None),
    channel: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        parse_target_datetime(target_date, target_time)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_date 또는 target_time 형식이 올바르지 않습니다. 예: 2026-05-01 / 18:30",
        ) from exc

    if image_file is None or not getattr(image_file, "filename", ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 이미지 생성 모델(Case4)은 image_file 업로드가 필수입니다.",
        )

    orig_suffix = Path(image_file.filename).suffix.lower()
    allowed_ext = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
    ext = orig_suffix if orig_suffix in allowed_ext else ".png"

    safe_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = UPLOAD_DIR / safe_name
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(image_file.file, buffer)
    uploaded_filename = str(saved_path)

    post_channel = channel if channel in ("feed", "story") else "feed"

    generation = Generation(
        user_id=current_user.id,
        purpose=purpose,
        business_category=business_category,
        menu_name=menu_name,
        mood=mood,
        location=location,
        extra_info="[PENDING] 생성 작업 대기 중",
        generation_status="PENDING",
        image_mode=post_channel,
    )

    db.add(generation)
    db.commit()
    db.refresh(generation)

    background_tasks.add_task(
        process_generation_task,
        generation.id,
        purpose,
        business_category,
        menu_name,
        location,
        target_date,
        target_time,
        mood,
        extra_prompt,
        uploaded_filename,
    )

    return {
        "generation_id": generation.id,
        "user_id": current_user.id,
        "status": "PENDING",
        "message": "처리중입니다. 잠시 후 보관함 또는 상세조회에서 결과를 확인하세요.",
    }


@router.post("/{generation_id}/regenerate", response_model=RegenerateImageResponse)
async def regenerate_generation_image(
    generation_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    generation = (
        db.query(Generation)
        .filter(Generation.id == generation_id, Generation.user_id == current_user.id)
        .first()
    )

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    generation.generation_status = "PENDING"
    db.commit()

    background_tasks.add_task(
        process_regenerate_task,
        generation_id,
    )

    return RegenerateImageResponse(
        generation_id=generation_id,
        status="PENDING",
        message="다른 버전 이미지를 생성중입니다. 잠시 후 이미지 목록을 확인하세요.",
    )
