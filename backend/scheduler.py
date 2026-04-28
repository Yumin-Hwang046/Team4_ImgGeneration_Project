"""
Instagram 예약 업로드 스케줄러
- 1분마다 실행 (threading 기반, 외부 라이브러리 불필요)
- status=PENDING이고 scheduled_at <= 현재 시간인 레코드 처리
"""

import logging
import threading
from datetime import datetime

from db import SessionLocal
from models import Generation, UploadSchedule, User
from instagram_router import _publish_media, _build_caption

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 60


class InstagramUploadScheduler:
    def __init__(self):
        self._timer: threading.Timer | None = None
        self._running = False

    def start(self):
        self._running = True
        self._schedule_next()
        logger.info("[스케줄러] Instagram 예약 업로드 스케줄러 시작")

    def shutdown(self):
        self._running = False
        if self._timer:
            self._timer.cancel()
        logger.info("[스케줄러] Instagram 예약 업로드 스케줄러 종료")

    def _schedule_next(self):
        if not self._running:
            return
        self._timer = threading.Timer(INTERVAL_SECONDS, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _tick(self):
        try:
            _run_pending_uploads()
        finally:
            self._schedule_next()


def _run_pending_uploads():
    db = SessionLocal()
    now = datetime.now()

    try:
        pending = (
            db.query(UploadSchedule)
            .filter(
                UploadSchedule.status == "PENDING",
                UploadSchedule.scheduled_at <= now,
            )
            .all()
        )

        if not pending:
            return

        logger.info(f"[스케줄러] 처리 대상 {len(pending)}건")

        for schedule in pending:
            _process_one(db, schedule)

    except Exception as e:
        logger.error(f"[스케줄러] 실행 오류: {e}")
    finally:
        db.close()


def _process_one(db, schedule: UploadSchedule):
    try:
        user: User = db.query(User).filter(User.id == schedule.user_id).first()
        if not user:
            _fail(db, schedule, "유저 없음")
            return

        if not user.instagram_account_id or not user.instagram_access_token:
            _fail(db, schedule, "Instagram 계정 미연동")
            return

        generation: Generation = (
            db.query(Generation).filter(Generation.id == schedule.generation_id).first()
        )
        if not generation:
            _fail(db, schedule, "Generation 없음")
            return

        if not generation.generated_image_url:
            _fail(db, schedule, "업로드할 이미지 없음")
            return

        from generations import to_public_media_url
        from instagram_router import _upload_to_cdn
        caption = _build_caption(generation)
        img_url = to_public_media_url(generation.generated_image_url, absolute=True)
        img_url = _upload_to_cdn(img_url)
        _publish_media(
            user.instagram_account_id,
            user.instagram_access_token,
            img_url,
            caption,
            schedule.channel,
        )

        schedule.status = "SUCCESS"
        db.commit()
        logger.info(f"[스케줄러] schedule_id={schedule.id} 업로드 성공")

    except Exception as e:
        _fail(db, schedule, str(e))


def _fail(db, schedule: UploadSchedule, reason: str):
    schedule.status = "FAILED"
    db.commit()
    logger.warning(f"[스케줄러] schedule_id={schedule.id} 실패: {reason}")


def create_scheduler() -> InstagramUploadScheduler:
    return InstagramUploadScheduler()
