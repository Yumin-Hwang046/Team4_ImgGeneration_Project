from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.auth import get_current_user
from backend.models import User, UserProfile
from backend.weather_service import fetch_daily_weather_rows_for_profile
from backend.festival_service import build_festival_debug_result
from backend.analytics_service import build_region_analytics_result

router = APIRouter(prefix="/integrations", tags=["integrations"])


def get_profile_or_404(db: Session, current_user: User) -> UserProfile:
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자 프로필이 없습니다.",
        )
    return profile


@router.post("/test/weather")
def test_weather_integration(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = get_profile_or_404(db, current_user)

    rows = fetch_daily_weather_rows_for_profile(profile)

    return {
        "message": "날씨 API 테스트 결과",
        "profile_id": profile.id,
        "region_name": " ".join(
            [value for value in [profile.sido, profile.sigungu, profile.emd] if value]
        ).strip() or profile.road_address,
        "count": len(rows),
        "sample": rows[:3],
    }


@router.post("/test/festival")
def test_festival_integration(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = get_profile_or_404(db, current_user)
    debug_result = build_festival_debug_result(profile)

    return {
        "message": "행사/축제 API 테스트 결과",
        "profile_id": profile.id,
        "debug": debug_result,
    }


@router.post("/test/analytics")
def test_analytics_integration(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = get_profile_or_404(db, current_user)

    if not profile.sido or "서울" not in str(profile.sido):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 상권분석 테스트는 서울 지역만 지원합니다.",
        )

    result = build_region_analytics_result(profile)

    return {
        "message": "상권분석 API 테스트 결과",
        "profile_id": profile.id,
        "result": result,
    }