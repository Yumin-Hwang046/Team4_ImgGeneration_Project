from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Generation, UploadSchedule, User
from backend.schemas import (
    InstagramUploadRequest,
    InstagramUploadResponse,
    InstagramScheduleUploadRequest,
    InstagramScheduleStatusResponse,
)
from backend.auth import get_current_user


router = APIRouter(prefix="/instagram", tags=["instagram"])


def validate_channel(channel: str) -> str:
    allowed = {"instagram_feed", "instagram_story"}
    if channel not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="channel은 instagram_feed 또는 instagram_story 만 가능합니다.",
        )
    return channel


@router.post("/upload", response_model=InstagramUploadResponse)
def upload_to_instagram(
    payload: InstagramUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

    return InstagramUploadResponse(
        generation_id=generation.id,
        channel=channel,
        status="MOCK_SUCCESS",
        message="인스타 업로드 mock 처리 완료",
    )


@router.post("/schedule-upload", response_model=InstagramScheduleStatusResponse)
def schedule_instagram_upload(
    payload: InstagramScheduleUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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


@router.get("/status/{schedule_id}", response_model=InstagramScheduleStatusResponse)
def get_status(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(UploadSchedule)
        .filter(
            UploadSchedule.id == schedule_id,
            UploadSchedule.user_id == current_user.id,
        )
        .first()
    )

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
