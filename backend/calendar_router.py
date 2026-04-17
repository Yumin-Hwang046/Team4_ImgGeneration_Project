from calendar import monthrange
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from db import get_db
from models import (
    CalendarEvent,
    Generation,
    UploadSchedule,
    User,
    UserProfile,
    WeatherDaily,
)
from schemas import (
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
from auth import get_current_user

router = APIRouter(prefix="/calendar", tags=["calendar"])


def get_seasonal_weather_fallback(target_date: date) -> str:
    month = target_date.month

    if month in [3, 4, 5]:
        return "봄 예상 날씨, 온화함 / 야외활동 적합"
    elif month in [6, 7, 8]:
        return "여름 예상 날씨, 더움 / 시원한 실내 수요 증가"
    elif month in [9, 10, 11]:
        return "가을 예상 날씨, 선선함 / 감성 마케팅 적합"
    else:
        return "겨울 예상 날씨, 추움 / 따뜻한 실내 분위기 강조"


def get_profile_or_404(db: Session, current_user: User) -> UserProfile:
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="사용자 프로필이 없습니다.")
    return profile


def get_profile_region_text(profile: UserProfile) -> str:
    return " ".join(
        [value for value in [profile.sido, profile.sigungu, profile.emd] if value]
    ).strip() or profile.road_address


def get_weather_summary_from_storage(
    db: Session,
    profile: UserProfile,
    target_date: date,
) -> str:
    row = (
        db.query(WeatherDaily)
        .filter(
            WeatherDaily.user_profile_id == profile.id,
            WeatherDaily.weather_date == target_date,
        )
        .first()
    )

    if row and row.weather_summary:
        return row.weather_summary

    diff_days = (target_date - date.today()).days

    # 저장정책: 0~14일은 실제 예보 저장 대상
    if 0 <= diff_days <= 14:
        return "날씨 정보 준비중"

    # 15일 이후는 실예보 대신 계절 fallback
    return get_seasonal_weather_fallback(target_date)


def build_event_region_query(query, profile: UserProfile):
    conditions = []

    # 도로명주소 기준
    if profile.sido:
        conditions.append(CalendarEvent.road_address.contains(profile.sido))
    if profile.sigungu:
        conditions.append(CalendarEvent.road_address.contains(profile.sigungu))
    if profile.emd:
        conditions.append(CalendarEvent.road_address.contains(profile.emd))

    # location 컬럼도 보조로 같이 사용
    if profile.sido:
        conditions.append(CalendarEvent.location.contains(profile.sido))
    if profile.sigungu:
        conditions.append(CalendarEvent.location.contains(profile.sigungu))
    if profile.emd:
        conditions.append(CalendarEvent.location.contains(profile.emd))

    # 주소가 없거나 일부만 들어온 행사도 있으니 OR로 완화
    if conditions:
        query = query.filter(or_(*conditions))

    return query

def get_event_display_priority(event: CalendarEvent) -> int:
    """
    숫자가 작을수록 먼저 보여줌
    """
    if event.event_type == "festival":
        return 1
    if event.event_type == "local_event":
        return 2
    if event.event_type == "festival_long":
        return 9
    return 5

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
        recommended_concept = "시원한 실내 / 청량한 음료·메뉴 강조"

    elif "가을 예상 날씨" in weather_summary:
        recommended_time = "오후 4시"
        recommended_channel = "instagram_feed"
        recommended_purpose = "감성 방문 유도"
        recommended_concept = "가을 감성 / 따뜻한 톤 / 분위기 강조"

    elif "겨울 예상 날씨" in weather_summary:
        recommended_time = "오후 5시"
        recommended_channel = "instagram_story"
        recommended_purpose = "따뜻한 실내 방문 유도"
        recommended_concept = "겨울 감성 / 온기 / 따뜻한 메뉴 강조"

    if "festival" in event_types:
        recommended_time = "오후 3시"
        recommended_channel = "instagram_feed"
        recommended_purpose = "행사 유입 연계 방문 유도"
        recommended_concept = f"지역 축제 연계 홍보 / {' / '.join(event_titles[:2])} 반영"

    if "local_event" in event_types:
        recommended_time = "오후 4시"
        recommended_channel = "instagram_story"
        recommended_purpose = "상권 유동 고객 즉시 유입"
        recommended_concept = f"지역 행사 맞춤 짧은 홍보 / {' / '.join(event_titles[:2])} 반영"

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = get_profile_or_404(db, current_user)
    _, last_day = monthrange(year, month)
    days: List[CalendarMonthDayItem] = []

    for day_num in range(1, last_day + 1):
        current_date = date(year, month, day_num)

        event_query = db.query(CalendarEvent).filter(CalendarEvent.event_date == current_date)
        event_query = build_event_region_query(event_query, profile)
        event_exists = event_query.first() is not None

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

        weather_summary = get_weather_summary_from_storage(db, profile, current_date)

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date 형식이 올바르지 않습니다. 예: 2026-05-01",
        )

    profile = get_profile_or_404(db, current_user)
    location = get_profile_region_text(profile)
    weather_summary = get_weather_summary_from_storage(db, profile, target_date)

    event_query = db.query(CalendarEvent).filter(CalendarEvent.event_date == target_date)
    event_query = build_event_region_query(event_query, profile)
    events = event_query.all()

    events = sorted(
        events,
        key=lambda e: (
            get_event_display_priority(e),
            e.event_start_date or target_date,
            e.title or "",
            e.id,
        ),
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = get_profile_or_404(db, current_user)

    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)

    query = db.query(CalendarEvent).filter(
        CalendarEvent.event_date >= start_date,
        CalendarEvent.event_date <= end_date,
    )
    query = build_event_region_query(query, profile)

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
        is_auto_collected=0,
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