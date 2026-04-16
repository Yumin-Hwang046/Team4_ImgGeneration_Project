import requests as http_requests
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

GRAPH_API = "https://graph.facebook.com/v19.0"

router = APIRouter(prefix="/instagram", tags=["instagram"])


def validate_channel(channel: str) -> str:
    allowed = {"instagram_feed", "instagram_story"}
    if channel not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="channel은 instagram_feed 또는 instagram_story 만 가능합니다.",
        )
    return channel


def _require_instagram(user: User) -> tuple[str, str]:
    """Instagram 연동 여부 확인 후 (account_id, access_token) 반환"""
    if not user.instagram_account_id or not user.instagram_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instagram 계정이 연동되지 않았습니다. 설정에서 Instagram을 연동해주세요.",
        )
    return user.instagram_account_id, user.instagram_access_token


def _build_caption(generation: Generation) -> str:
    parts = []
    if generation.generated_copy:
        parts.append(generation.generated_copy)
    if generation.hashtags:
        parts.append(generation.hashtags)
    return "\n\n".join(parts)


def _publish_media(ig_account_id: str, access_token: str, image_url: str, caption: str, channel: str) -> str:
    """미디어 컨테이너 생성 후 게시, 게시된 미디어 ID 반환"""
    media_type = "STORIES" if channel == "instagram_story" else None

    container_params: dict = {
        "image_url": image_url,
        "caption": caption,
        "access_token": access_token,
    }
    if media_type:
        container_params["media_type"] = media_type

    container_res = http_requests.post(
        f"{GRAPH_API}/{ig_account_id}/media",
        params=container_params,
        timeout=30,
    )
    if not container_res.ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Instagram 미디어 생성 실패: {container_res.json().get('error', {}).get('message', container_res.text)}",
        )
    creation_id = container_res.json().get("id")

    publish_res = http_requests.post(
        f"{GRAPH_API}/{ig_account_id}/media_publish",
        params={"creation_id": creation_id, "access_token": access_token},
        timeout=30,
    )
    if not publish_res.ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Instagram 게시 실패: {publish_res.json().get('error', {}).get('message', publish_res.text)}",
        )
    return publish_res.json().get("id", "")


# =========================
# 업로드 (즉시)
# =========================
@router.post("/upload", response_model=InstagramUploadResponse)
def upload_to_instagram(
    payload: InstagramUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    channel = validate_channel(payload.channel)
    ig_account_id, access_token = _require_instagram(current_user)

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

    if not generation.generated_image_url:
        raise HTTPException(status_code=400, detail="업로드할 이미지가 없습니다.")

    caption = _build_caption(generation)
    _publish_media(ig_account_id, access_token, generation.generated_image_url, caption, channel)

    return InstagramUploadResponse(
        generation_id=generation.id,
        channel=channel,
        status="SUCCESS",
        message="Instagram 업로드 완료",
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