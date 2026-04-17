import time
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


def _create_media_container(
    ig_account_id: str,
    access_token: str,
    image_url: str,
    caption: str,
    channel: str,
) -> str:
    """미디어 컨테이너 생성 후 creation_id 반환"""
    params: dict = {
        "image_url": image_url,
        "access_token": access_token,
    }

    # 스토리/피드 모두 IMAGE 타입으로 발행 (caption 포함)
    # media_type=STORIES 는 앱 심사 통과 후 Meta에서 별도 활성화 필요
    if caption:
        params["caption"] = caption

    res = http_requests.post(
        f"{GRAPH_API}/{ig_account_id}/media",
        params=params,
        timeout=30,
    )

    if not res.ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Instagram 미디어 생성 실패: {res.json().get('error', {}).get('message', res.text)}",
        )

    return res.json().get("id")


def _wait_for_container(creation_id: str, access_token: str, max_retries: int = 10):
    """컨테이너 처리 완료(FINISHED)까지 폴링"""
    for _ in range(max_retries):
        res = http_requests.get(
            f"{GRAPH_API}/{creation_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=10,
        )
        if not res.ok:
            break
        code = res.json().get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR" or code == "EXPIRED":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Instagram 미디어 처리 실패: {code}",
            )
        time.sleep(2)
    # 폴링 타임아웃 시 그냥 진행 (일부 경우 status_code 미지원)


def _publish_media(ig_account_id: str, access_token: str, image_url: str, caption: str, channel: str) -> str:
    """미디어 컨테이너 생성 → 처리 완료 대기 → 게시"""
    creation_id = _create_media_container(ig_account_id, access_token, image_url, caption, channel)
    _wait_for_container(creation_id, access_token)

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