import json
from datetime import datetime, date
from typing import Optional, List
from pathlib import Path
from urllib.parse import quote
import shutil

import requests
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

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


def geocode_location(location: str) -> tuple[float, float]:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": location,
        "count": 1,
        "language": "ko",
        "format": "json",
    }

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results")
    if not results:
        raise HTTPException(status_code=404, detail=f"지역을 찾을 수 없습니다: {location}")

    lat = results[0]["latitude"]
    lon = results[0]["longitude"]
    return lat, lon


def get_seasonal_weather_fallback(target_dt: datetime) -> str:
    month = target_dt.month

    if month in [3, 4, 5]:
        return "봄 예상 날씨, 온화함 / 야외활동 적합"
    if month in [6, 7, 8]:
        return "여름 예상 날씨, 더움 / 시원한 실내 수요 증가"
    if month in [9, 10, 11]:
        return "가을 예상 날씨, 선선함 / 감성 마케팅 적합"
    return "겨울 예상 날씨, 추움 / 따뜻한 실내 분위기 강조"


def get_profile_region_text(profile: UserProfile) -> str:
    return " ".join(
        [value for value in [profile.sido, profile.sigungu, profile.emd] if value]
    ).strip() or profile.road_address


def looks_like_invalid_location(location: Optional[str]) -> bool:
    value = (location or "").strip()
    if not value:
        return True

    mood_like_values = {
        "sunny", "cloudy", "rainy", "warm",
        "맑은 날씨", "흐린 날씨", "비 오는 배경", "따뜻한 조명", "따뜻한 감성",
    }
    return value in mood_like_values


def resolve_generation_location(db: Session, user_id: int, requested_location: Optional[str]) -> str:
    requested_location = (requested_location or "").strip()

    if requested_location and not looks_like_invalid_location(requested_location):
        return requested_location

    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .first()
    )
    if profile:
        return get_profile_region_text(profile)

    return requested_location or "서울"


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

        target_hour = target_dt.strftime("%Y-%m-%dT%H:00")

        idx = times.index(target_hour) if target_hour in times else 0

        weather_text = weather_code_to_text(codes[idx]) if idx < len(codes) else "정보 없음"
        temp = temps[idx] if idx < len(temps) else "?"
        pop = pops[idx] if idx < len(pops) else "?"

        return f"{weather_text}, {temp}°C, 강수확률 {pop}%"

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
        else "저녁 시간대" if 17 <= hour <= 21
        else "일반 시간대"
    )

    if "카페" in business_category:
        if "비" in weather_summary:
            base = "비 오는 날 감성 카페 분위기, 따뜻한 음료 중심"
        elif "맑음" in weather_summary:
            base = "햇살 좋은 날 감성 디저트/음료 중심"
        else:
            base = "계절감이 드러나는 카페 무드 중심"
    elif "주점" in business_category or "이자카야" in business_category:
        if hour >= 18:
            base = "퇴근 후/저녁 모임 유도, 분위기 있는 매장 컷 중심"
        else:
            base = "캐주얼한 술자리 예고형 콘텐츠"
    else:
        base = "메뉴 중심의 실사용 유입형 홍보 이미지"

    if mood:
        return f"{base} / {time_context} / 무드 반영: {mood} / 대표 메뉴 강조: {menu_name}"
    return f"{base} / {time_context} / {season_context} / 대표 메뉴 강조: {menu_name}"


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

        original_image_url = None
        source_image_path = None

        if uploaded_filename:
            original_image_url = to_public_media_url(uploaded_filename)
            source_image_path = uploaded_filename
            image_mode = "uploaded_and_analyzed"
            extra_info = f"[IMAGE_ANALYSIS] 업로드 이미지 분석 완료: {uploaded_filename}\n[USER_PROMPT] {extra_prompt or ''}"
        else:
            image_mode = "generated"
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
        generation.image_mode = image_mode
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
        db.commit()

    except Exception as e:
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

        generation.generation_status = "PENDING"
        db.commit()

        recommended_concept = generation.recommended_concept or "기본 추천 컨셉"

        raw_image_result = call_image_generator(
            business_category=generation.business_category or "기타",
            menu_name=generation.menu_name or "메뉴",
            location=generation.location or "지역",
            mood=generation.mood,
            recommended_concept=recommended_concept,
            extra_prompt=None,
            image_path=None,
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
        db.commit()

    except Exception as e:
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

    uploaded_filename = None
    if image_file is not None and getattr(image_file, "filename", ""):
        saved_path = UPLOAD_DIR / image_file.filename
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        uploaded_filename = str(saved_path)

    generation = Generation(
        user_id=current_user.id,
        purpose=purpose,
        business_category=business_category,
        menu_name=menu_name,
        mood=mood,
        location=location,
        extra_info="[PENDING] 생성 작업 대기 중",
        generation_status="PENDING",
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
