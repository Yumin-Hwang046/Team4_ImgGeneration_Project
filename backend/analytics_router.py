from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db import get_db
from models import User, UserProfile, RegionAnalytics
from schemas import RegionAnalyticsItem, RegionAnalyticsRefreshResponse
from auth import get_current_user
from analytics_service import build_region_analytics_result

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/refresh/me", response_model=RegionAnalyticsRefreshResponse)
def refresh_my_region_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

    if not profile.sido or "서울" not in profile.sido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 MVP는 서울 지역만 지원합니다.",
        )

    result = build_region_analytics_result(profile)

    row = RegionAnalytics(
        user_profile_id=profile.id,
        analysis_date=result["analysis_date"],
        region_name=result["region_name"],
        legal_code=result["legal_code"],
        floating_population=result["floating_population"],
        competitor_count=result["competitor_count"],
        top_categories_json=result["top_categories_json"],
        summary_text=result["summary_text"],
        source_name=result["source_name"],
        raw_payload=result["raw_payload"],
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return RegionAnalyticsRefreshResponse(
        message="상권분석 데이터를 저장했습니다.",
        analysis_id=row.id,
        region_name=row.region_name,
        source_name=row.source_name or "PARTIAL",
    )


@router.get("/me/latest", response_model=RegionAnalyticsItem)
def get_my_latest_region_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

    row = (
        db.query(RegionAnalytics)
        .filter(RegionAnalytics.user_profile_id == profile.id)
        .order_by(RegionAnalytics.analysis_date.desc(), RegionAnalytics.id.desc())
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="저장된 상권분석 결과가 없습니다.",
        )

    return row