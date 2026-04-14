from calendar import monthrange
from datetime import datetime, date
from typing import List

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import CalendarEvent, Generation, UploadSchedule, User
from backend.schemas import (
    CalendarMonthResponse,
    CalendarMonthDayItem,
    CalendarDayResponse,
    CalendarWeatherItem,
    CalendarRecommendationItem,
    CalendarEventCreate,
    CalendarEventItem,
    CalendarGenerationItem,
    UploadScheduleCreate,
    UploadScheduleItem,
)
from backend.auth import get_current_user

router = APIRouter(prefix="/calendar", tags=["calendar"])


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


def get_seasonal_weather_fallback(target_date: date) -> str:
    month = target_date.month

    if month in [3, 4, 5]:
        return "봄 예상 날씨, 온화함 / 야외활동 적합"
    if month in [6, 7, 8]:
        return "여름 예상 날씨, 더움 / 시원한 실내 수요 증가"
    if month in [9, 10, 11]:
        return "가을 예상 날씨, 선선함 / 감성 마케팅 적합"
    return "겨울 예상 날씨, 추움 / 따뜻한 실내 분위기 강조"


def is_forecast_range_available(target_date: date) -> bool:
    today = date.today()
    diff_days = (target_date - today).days
    return 0 <= diff_days <= 16


def get_weather_summary_by_date(location: str, target_date: date) -> str:
    if not is_forecast_range_available(target_date):
        return get_seasonal_weather_fallback(target_date)

    try:
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {
            "name": location,
            "count": 1,
            "language": "ko",
            "format": "json",
        }
        geo_resp = requests.get(geo_url, params=geo_params, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        results = geo_data.get("results")
        if not results:
            return get_seasonal_weather_fallback(target_date)

        lat = results[0]["latitude"]
        lon = results[0]["longitude"]

        forecast_url = "https://api.open-meteo.com/v1/forecast"
        forecast_params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "timezone": "Asia/Seoul",
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
            "forecast_days": 16,
        }
        forecast_resp = requests.get(forecast_url, params=forecast_params, timeout=10)
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json()

        daily = forecast_data.get("daily", {})
        codes = daily.get("weather_code", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])

        if not codes:
            return get_seasonal_weather_fallback(target_date)

        weather_text = weather_code_to_text(codes[0])
        max_temp = max_temps[0] if max_temps else "?"
        min_temp = min_temps[0] if min_temps else "?"

        return f"{weather_text}, 최고 {max_temp}°C / 최저 {min_temp}°C"

    except Exception:
        return get_seasonal_weather_fallback(target_date)


def build_recommendation(
    *,
    location: str,
    target_date: date,
    weather_summary: str,
    events: List[CalendarEvent],
) -> CalendarRecommendationItem:
    event_titles = [event.title for event in events]
    event_types = [event.event_type for event in events]

    recommended_time = "오후 6시"
    recommended_channel = "instagram_feed"
    recommended_purpose = "방문 유도"
    recommended_concept = f"{location} 지역 맞춤 일반 홍보 콘텐츠"

    if "비" in weather_summary:
        recommended_time = "오후 5시"
        recommended_channel = "instagram_story"
        recommended_purpose = "실내 방문 유도"
        recommended_concept = "비 오는 날 감성 / 따뜻한 실내 분위기 강조"
    elif "맑음" in weather_summary:
        recommended_time = "오후 12시"
        recommended_channel = "instagram_feed"
        recommended_purpose = "점심/오후 유입 유도"
        recommended_concept = "맑은 날 감성 / 밝고 선명한 비주얼 강조"
    elif "봄 예상 날씨" in weather_summary:
        recommended_time = "오후 2시"
        recommended_channel = "instagram_feed"
        recommended_purpose = "야외활동 전후 방문 유도"
        recommended_concept = "봄 감성 / 산뜻한 색감 / 시즌 한정 메뉴 강조"
    elif "여름 예상 날씨" in weather_summary:
        recommended_time = "오후 1시"
        recommended_channel = "instagram_story"
        recommended_purpose = "더위 회피 수요 유입"
        recommended_concept = "시원한 분위기 / 청량한 비주얼 / 여름 특화 메뉴 강조"
    elif "가을 예상 날씨" in weather_summary:
        recommended_time = "오후 4시"
        recommended_channel = "instagram_feed"
        recommended_purpose = "감성 소비 유도"
        recommended_concept = "가을 감성 / 따뜻한 무드 / 저녁 방문 유도"
    elif "겨울 예상 날씨" in weather_summary:
        recommended_time = "오후 5시"
        recommended_channel = "instagram_feed"
        recommended_purpose = "실내 체류 수요 유도"
        recommended_concept = "겨울 감성 / 따뜻한 실내 / 온기 있는 메뉴 강조"

    if "holiday" in event_types:
        recommended_time = "오전 10시"
        recommended_channel = "instagram_feed"
        recommended_purpose = "공휴일 특수 수요 선점"
        recommended_concept = "공휴일 맞춤 프로모션 / 가족·연인 고객 유입 강조"

    if "festival" in event_types:
        recommended_time = "오후 2시"
        recommended_channel = "instagram_story"
        recommended_purpose = "축제 유동 인구 유입"
        recommended_concept = f"행사 연계 홍보 / {' / '.join(event_titles)} 분위기 반영"

    if "local_event" in event_types:
        recommended_time = "오후 4시"
        recommended_channel = "instagram_story"
        recommended_purpose = "상권 유동 고객 즉시 유입"
        recommended_concept = f"지역 행사 맞춤 짧은 홍보 / {' / '.join(event_titles)} 반영"

    return CalendarRecommendationItem(
        recommended_time=recommended_time,
        recommended_channel=recommended_channel,
        recommended_purpose=recommended_purpose,
        recommended_concept=recommended_concept,
    )


@router.get("/month", response_model=CalendarMonthResponse)
def get_calendar_month(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    location: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _, last_day = monthrange(year, month)
    days: List[CalendarMonthDayItem] = []

    for day_num in range(1, last_day + 1):
        current_date = date(year, month, day_num)

        event_exists = (
            db.query(CalendarEvent)
            .filter(
                CalendarEvent.event_date == current_date,
                or_(CalendarEvent.location.is_(None), CalendarEvent.location == location),
            )
            .first()
            is not None
        )

        generation_exists = (
            db.query(Generation)
            .filter(
                Generation.user_id == current_user.id,
                Generation.created_at >= datetime(year, month, day_num, 0, 0, 0),
                Generation.created_at < datetime(year, month, day_num, 23, 59, 59),
            )
            .first()
            is not None
        )

        schedule_exists = (
            db.query(UploadSchedule)
            .filter(
                UploadSchedule.user_id == current_user.id,
                UploadSchedule.scheduled_at >= datetime(year, month, day_num, 0, 0, 0),
                UploadSchedule.scheduled_at < datetime(year, month, day_num, 23, 59, 59),
            )
            .first()
            is not None
        )

        weather_summary = get_weather_summary_by_date(location, current_date)

        days.append(
            CalendarMonthDayItem(
                date=current_date.isoformat(),
                weather_summary=weather_summary,
                has_event=event_exists,
                has_generation=generation_exists,
                has_schedule=schedule_exists,
            )
        )

    return CalendarMonthResponse(year=year, month=month, days=days)


@router.get("/day", response_model=CalendarDayResponse)
def get_calendar_day(
    date_str: str = Query(..., alias="date"),
    location: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date 형식이 올바르지 않습니다. 예: 2026-05-01",
        ) from exc

    weather_summary = get_weather_summary_by_date(location, target_date)

    events = (
        db.query(CalendarEvent)
        .filter(
            CalendarEvent.event_date == target_date,
            or_(CalendarEvent.location.is_(None), CalendarEvent.location == location),
        )
        .order_by(CalendarEvent.id.asc())
        .all()
    )

    generations = (
        db.query(Generation)
        .filter(
            Generation.user_id == current_user.id,
            Generation.created_at >= datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0),
            Generation.created_at < datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59),
        )
        .order_by(Generation.created_at.desc())
        .all()
    )

    schedules = (
        db.query(UploadSchedule)
        .filter(
            UploadSchedule.user_id == current_user.id,
            UploadSchedule.scheduled_at >= datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0),
            UploadSchedule.scheduled_at < datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59),
        )
        .order_by(UploadSchedule.scheduled_at.asc())
        .all()
    )

    recommendation = build_recommendation(
        location=location,
        target_date=target_date,
        weather_summary=weather_summary,
        events=events,
    )

    return CalendarDayResponse(
        date=target_date.isoformat(),
        weather=CalendarWeatherItem(summary=weather_summary),
        recommendation=recommendation,
        events=events,
        generations=generations,
        schedules=schedules,
    )


@router.get("/events", response_model=List[CalendarEventItem])
def list_calendar_events(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    location: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)

    query = db.query(CalendarEvent).filter(
        CalendarEvent.event_date >= start_date,
        CalendarEvent.event_date <= end_date,
    )

    if location:
        query = query.filter(
            or_(CalendarEvent.location.is_(None), CalendarEvent.location == location)
        )

    rows = query.order_by(CalendarEvent.event_date.asc(), CalendarEvent.id.asc()).all()
    return rows


@router.post("/events", response_model=CalendarEventItem, status_code=status.HTTP_201_CREATED)
def create_calendar_event(
    payload: CalendarEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_event = CalendarEvent(
        event_date=payload.event_date,
        title=payload.title,
        event_type=payload.event_type,
        location=payload.location,
        description=payload.description,
    )

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return new_event


@router.delete("/events/{event_id}")
def delete_calendar_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()

    if not row:
        raise HTTPException(status_code=404, detail="Event not found")

    db.delete(row)
    db.commit()

    return {"message": "행사 일정이 삭제되었습니다."}


@router.post("/schedules", response_model=UploadScheduleItem, status_code=status.HTTP_201_CREATED)
def create_upload_schedule(
    payload: UploadScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    generation = (
        db.query(Generation)
        .filter(Generation.id == payload.generation_id, Generation.user_id == current_user.id)
        .first()
    )
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    new_schedule = UploadSchedule(
        user_id=current_user.id,
        generation_id=payload.generation_id,
        scheduled_at=payload.scheduled_at,
        channel=payload.channel,
        status="PENDING",
    )

    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)

    return new_schedule


@router.get("/schedules", response_model=List[UploadScheduleItem])
def list_upload_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(UploadSchedule)
        .filter(UploadSchedule.user_id == current_user.id)
        .order_by(UploadSchedule.scheduled_at.asc())
        .all()
    )
    return rows


@router.delete("/schedules/{schedule_id}")
def delete_upload_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(UploadSchedule)
        .filter(UploadSchedule.id == schedule_id, UploadSchedule.user_id == current_user.id)
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Schedule not found")

    db.delete(row)
    db.commit()

    return {"message": "예약 일정이 삭제되었습니다."}
