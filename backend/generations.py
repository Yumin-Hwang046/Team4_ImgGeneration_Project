import json
from datetime import datetime
from typing import Optional, List

import requests
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from db import get_db, SessionLocal
from models import Generation, User
from schemas import (
    GenerationCreate,
    GenerationUpdate,
    GenerationResponse,
    GenerationDetailResponse,
    GenerationListItem,
)
from auth import get_current_user
from ai_adapter import normalize_image_result, normalize_text_result


router = APIRouter(prefix="/generations", tags=["generations"])


# =========================================================
# Helper functions
# =========================================================

def parse_target_datetime(date_str: str, time_str: Optional[str]) -> datetime:
    if time_str:
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return datetime.strptime(f"{date_str} 12:00", "%Y-%m-%d %H:%M")


def get_season_context(target_dt: datetime) -> str:
    month = target_dt.month

    if month in [3, 4, 5]:
        return "봄 시즌, 야외활동 증가, 산뜻한 분위기 선호"
    elif month in [6, 7, 8]:
        return "여름 시즌, 시원함/청량감/더위 회피 니즈 증가"
    elif month in [9, 10, 11]:
        return "가을 시즌, 따뜻함/감성/저녁 방문 유도에 적합"
    else:
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

        if target_hour in times:
            idx = times.index(target_hour)
        else:
            idx = 0

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


async def analyze_uploaded_image(file: UploadFile) -> str:
    return f"업로드 이미지 분석 완료: {file.filename}"


async def generate_image_placeholder(
    business_category: str,
    menu_name: str,
    recommended_concept: str,
) -> dict:
    fake_url = f"https://dummy.local/generated/{business_category}_{menu_name}.png"
    return {
        "success": True,
        "image_url": fake_url,
        "prompt_used": recommended_concept,
        "error": None,
    }


def generate_copy_and_hashtags(
    business_category: str,
    menu_name: str,
    purpose: str,
    location: str,
    recommended_concept: str,
    weather_summary: str,
    season_context: str,
    extra_prompt: Optional[str],
) -> dict:
    if purpose == "story":
        copy = (
            f"{location}에서 지금 어울리는 {menu_name}. "
            f"{weather_summary}인 날에 딱 맞는 분위기로 준비했어요. "
            f"{recommended_concept}"
        )
    else:
        copy = (
            f"{location} 매장에서 즐기는 {menu_name}. "
            f"{season_context}에 맞춰 더 끌리게 보이도록 구성했어요. "
            f"{recommended_concept}"
        )

    if extra_prompt:
        copy += f" / 추가 요청 반영: {extra_prompt}"

    hashtags = [
        f"#{location.replace(' ', '')}",
        f"#{business_category.replace(' ', '')}",
        f"#{menu_name.replace(' ', '')}",
        "#소상공인홍보",
        "#인스타마케팅",
    ]

    return {
        "success": True,
        "copy": copy,
        "hashtags": hashtags,
        "error": None,
    }


def safe_load_hashtags(value) -> list:
    if not value:
        return []

    if isinstance(value, list):
        return value

    try:
        return json.loads(value)
    except Exception:
        return []


# =========================================================
# Background processing
# =========================================================

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
        weather_summary = get_weather_summary(location, target_dt)
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

        if uploaded_filename:
            image_mode = "uploaded_and_analyzed"
            analysis_result = f"업로드 이미지 분석 완료: {uploaded_filename}"
            original_image_url = f"https://dummy.local/uploads/{uploaded_filename}"

            raw_image_result = {
                "success": True,
                "image_url": original_image_url,
                "prompt_used": "",
                "error": None,
            }

            extra_info = f"[IMAGE_ANALYSIS] {analysis_result}\n[USER_PROMPT] {extra_prompt or ''}"
        else:
            image_mode = "generated"
            raw_image_result = {
                "success": True,
                "image_url": f"https://dummy.local/generated/{business_category}_{menu_name}.png",
                "prompt_used": recommended_concept,
                "error": None,
            }
            extra_info = f"[NO_UPLOAD_IMAGE]\n[USER_PROMPT] {extra_prompt or ''}"

        image_result = normalize_image_result(raw_image_result)

        if not image_result["success"]:
            generation.generation_status = "FAILED"
            generation.extra_info = (generation.extra_info or "") + "\n[ERROR] 이미지 처리 실패"
            db.commit()
            return

        generated_image_url = image_result["image_url"]

        raw_text_result = generate_copy_and_hashtags(
            business_category=business_category,
            menu_name=menu_name,
            purpose=purpose,
            location=location,
            recommended_concept=recommended_concept,
            weather_summary=weather_summary,
            season_context=season_context,
            extra_prompt=extra_prompt,
        )

        text_result = normalize_text_result(raw_text_result)

        if not text_result["success"]:
            generation.generation_status = "FAILED"
            generation.extra_info = (generation.extra_info or "") + "\n[ERROR] 문구 생성 실패"
            db.commit()
            return

        generated_copy = text_result["copy"]
        hashtags = text_result["hashtags"]

        generation.purpose = purpose
        generation.business_category = business_category
        generation.menu_name = menu_name
        generation.mood = mood
        generation.location = location
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

        db.commit()

    except Exception as e:
        generation = db.query(Generation).filter(Generation.id == generation_id).first()
        if generation:
            generation.generation_status = "FAILED"
            generation.extra_info = (generation.extra_info or "") + f"\n[ERROR] {str(e)}"
            db.commit()
    finally:
        db.close()


# =========================================================
# CRUD
# =========================================================

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


# =========================================================
# RUN API
# =========================================================

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
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_date 또는 target_time 형식이 올바르지 않습니다. 예: 2026-05-01 / 18:30",
        )

    uploaded_filename = None
    if image_file is not None and getattr(image_file, "filename", ""):
        uploaded_filename = image_file.filename

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