"""
Instagram 업로드 API

⚠️ 현재 상태: MOCK

Meta Graph API 연결 전까지는 mock으로 동작합니다.

🔧 실연동 시 수정 위치:
- upload_to_instagram()
- schedule_instagram_upload()

Meta API 연결 시:
- ACCESS TOKEN 필요
- Instagram Business 계정 필요
- Facebook Page 연결 필요
"""


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db import get_db
from models import Generation, UploadSchedule, User
from schemas import (
    InstagramUploadRequest,
    InstagramUploadResponse,
    InstagramScheduleUploadRequest,
    InstagramScheduleStatusResponse,
)
from auth import get_current_user


router = APIRouter(prefix="/instagram", tags=["instagram"])


def validate_channel(channel: str) -> str:
    allowed = {"instagram_feed", "instagram_story"}
    if channel not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="channel은 instagram_feed 또는 instagram_story 만 가능합니다.",
        )
    return channel


# =========================
# 업로드 (즉시)
# =========================
@router.post("/upload", response_model=InstagramUploadResponse)
def upload_to_instagram(
    payload: InstagramUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🔧 실연동 시 이 함수 내부를 교체

    Meta Graph API 흐름:
    1. image_url 업로드
    2. media 생성
    3. publish 호출
    """

    channel = validate_channel(payload.channel)

    generation = (
        db.query(Generation)
        .filter(
            Generation.id == payload.generation_id,
            Generation.user_id == current_user.id,
        )
        .first()
    )
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    # ===== MOCK 응답 =====
    return InstagramUploadResponse(
        generation_id=generation.id,
        channel=channel,
        status="MOCK_SUCCESS",
        message="인스타 업로드 mock 처리 완료",
    )


# =========================
# 예약 업로드
# =========================
@router.post("/schedule-upload", response_model=InstagramScheduleStatusResponse)
def schedule_instagram_upload(
    payload: InstagramScheduleUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🔧 실연동 시:
    - Meta 예약 API 또는 자체 스케줄러 연결
    """

    channel = validate_channel(payload.channel)

    new_schedule = UploadSchedule(
        user_id=current_user.id,
        generation_id=payload.generation_id,
        scheduled_at=payload.scheduled_at,
        channel=channel,
        status="PENDING",
    )

    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)

    return InstagramScheduleStatusResponse(
        schedule_id=new_schedule.id,
        generation_id=new_schedule.generation_id,
        channel=new_schedule.channel,
        scheduled_at=new_schedule.scheduled_at,
        status=new_schedule.status,
        message="예약 등록 완료 (mock)",
    )


# =========================
# 상태 조회
# =========================
@router.get("/status/{schedule_id}", response_model=InstagramScheduleStatusResponse)
def get_status(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.query(UploadSchedule).filter(UploadSchedule.id == schedule_id).first()

    if not row:
        raise HTTPException(status_code=404, detail="Not found")

    return InstagramScheduleStatusResponse(
        schedule_id=row.id,
        generation_id=row.generation_id,
        channel=row.channel,
        scheduled_at=row.scheduled_at,
        status=row.status,
        message="현재 상태 조회",
    )