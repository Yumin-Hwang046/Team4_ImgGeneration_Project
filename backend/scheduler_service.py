from datetime import datetime
from typing import Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from db import SessionLocal
from models import SchedulerJobLog, UserProfile, CalendarEvent, WeatherDaily
from festival_service import build_festival_event_rows_for_profile
from weather_service import fetch_daily_weather_rows_for_profile

scheduler = BackgroundScheduler(timezone="Asia/Seoul")


def write_job_log(
    *,
    job_name: str,
    job_type: str,
    target_region: Optional[str] = None,
    status: str,
    processed_count: int = 0,
    error_message: Optional[str] = None,
    run_started_at: Optional[datetime] = None,
    run_finished_at: Optional[datetime] = None,
) -> None:
    db = SessionLocal()
    try:
        row = SchedulerJobLog(
            job_name=job_name,
            job_type=job_type,
            target_region=target_region,
            status=status,
            processed_count=processed_count,
            error_message=error_message,
            run_started_at=run_started_at or datetime.now(),
            run_finished_at=run_finished_at,
        )
        db.add(row)
        db.commit()
    finally:
        db.close()


def upsert_calendar_event(db, payload: Dict) -> None:
    existing = None
    if payload.get("external_id"):
        existing = (
            db.query(CalendarEvent)
            .filter(
                CalendarEvent.external_id == payload["external_id"],
                CalendarEvent.event_date == payload["event_date"],
            )
            .first()
        )

    if existing:
        existing.title = payload["title"]
        existing.event_type = payload["event_type"]
        existing.location = payload["location"]
        existing.description = payload["description"]
        existing.event_start_date = payload["event_start_date"]
        existing.event_end_date = payload["event_end_date"]
        existing.source_name = payload["source_name"]
        existing.source_url = payload["source_url"]
        existing.road_address = payload["road_address"]
        existing.jibun_address = payload["jibun_address"]
        existing.latitude = payload["latitude"]
        existing.longitude = payload["longitude"]
        existing.is_auto_collected = payload["is_auto_collected"]
        existing.last_synced_at = datetime.now()
        db.flush()
        return

    row = CalendarEvent(
        event_date=payload["event_date"],
        title=payload["title"],
        event_type=payload["event_type"],
        location=payload["location"],
        description=payload["description"],
        external_id=payload["external_id"],
        event_start_date=payload["event_start_date"],
        event_end_date=payload["event_end_date"],
        source_name=payload["source_name"],
        source_url=payload["source_url"],
        road_address=payload["road_address"],
        jibun_address=payload["jibun_address"],
        legal_code=None,
        latitude=payload["latitude"],
        longitude=payload["longitude"],
        is_auto_collected=payload["is_auto_collected"],
        last_synced_at=datetime.now(),
    )
    db.add(row)
    db.flush()


def upsert_weather_daily(db, user_profile_id: int, payload: Dict) -> None:
    existing = (
        db.query(WeatherDaily)
        .filter(
            WeatherDaily.user_profile_id == user_profile_id,
            WeatherDaily.weather_date == payload["weather_date"],
        )
        .first()
    )

    if existing:
        existing.region_name = payload["region_name"]
        existing.legal_code = payload["legal_code"]
        existing.latitude = payload["latitude"]
        existing.longitude = payload["longitude"]
        existing.weather_code = payload["weather_code"]
        existing.weather_summary = payload["weather_summary"]
        existing.temp_min = payload["temp_min"]
        existing.temp_max = payload["temp_max"]
        existing.precipitation_probability = payload["precipitation_probability"]
        existing.forecast_type = payload["forecast_type"]
        existing.source_name = payload["source_name"]
        existing.fetched_at = datetime.now()
        return

    row = WeatherDaily(
        user_profile_id=user_profile_id,
        weather_date=payload["weather_date"],
        region_name=payload["region_name"],
        legal_code=payload["legal_code"],
        latitude=payload["latitude"],
        longitude=payload["longitude"],
        weather_code=payload["weather_code"],
        weather_summary=payload["weather_summary"],
        temp_min=payload["temp_min"],
        temp_max=payload["temp_max"],
        precipitation_probability=payload["precipitation_probability"],
        forecast_type=payload["forecast_type"],
        source_name=payload["source_name"],
        fetched_at=datetime.now(),
    )
    db.add(row)


def run_weather_sync_job() -> None:
    started_at = datetime.now()
    db = SessionLocal()
    try:
        profiles = db.query(UserProfile).all()

        target_regions = []
        processed_count = 0

        for profile in profiles:
            region_name = " ".join(
                [value for value in [profile.sido, profile.sigungu, profile.emd] if value]
            ).strip() or profile.road_address
            target_regions.append(region_name)

            rows = fetch_daily_weather_rows_for_profile(profile)
            for payload in rows:
                upsert_weather_daily(db, profile.id, payload)
            processed_count += len(rows)

        db.commit()

        write_job_log(
            job_name="weather_sync",
            job_type="calendar_sync",
            target_region=", ".join(target_regions[:5]) if target_regions else None,
            status="SUCCESS",
            processed_count=processed_count,
            run_started_at=started_at,
            run_finished_at=datetime.now(),
        )
    except Exception as e:
        db.rollback()
        write_job_log(
            job_name="weather_sync",
            job_type="calendar_sync",
            status="FAILED",
            processed_count=0,
            error_message=str(e),
            run_started_at=started_at,
            run_finished_at=datetime.now(),
        )
    finally:
        db.close()


def run_festival_sync_job() -> None:
    started_at = datetime.now()
    db = SessionLocal()
    try:
        profiles = db.query(UserProfile).filter(UserProfile.sido.like("%서울%")).all()

        target_regions = []
        processed_count = 0

        for profile in profiles:
            region_name = " ".join(
                [value for value in [profile.sido, profile.sigungu, profile.emd] if value]
            ).strip() or profile.road_address
            target_regions.append(region_name)

            rows = build_festival_event_rows_for_profile(profile)
            for payload in rows:
                upsert_calendar_event(db, payload)
            processed_count += len(rows)

        db.commit()

        write_job_log(
            job_name="festival_sync",
            job_type="calendar_sync",
            target_region=", ".join(target_regions[:5]) if target_regions else "서울",
            status="SUCCESS",
            processed_count=processed_count,
            run_started_at=started_at,
            run_finished_at=datetime.now(),
        )
    except Exception as e:
        db.rollback()
        write_job_log(
            job_name="festival_sync",
            job_type="calendar_sync",
            target_region="서울",
            status="FAILED",
            processed_count=0,
            error_message=str(e),
            run_started_at=started_at,
            run_finished_at=datetime.now(),
        )
    finally:
        db.close()


def run_region_analytics_refresh_job() -> None:
    started_at = datetime.now()
    db = SessionLocal()
    try:
        profiles = db.query(UserProfile).filter(UserProfile.sido.like("%서울%")).all()
        processed_count = len(profiles)

        write_job_log(
            job_name="region_analytics_refresh",
            job_type="analytics_sync",
            target_region="서울",
            status="SUCCESS",
            processed_count=processed_count,
            run_started_at=started_at,
            run_finished_at=datetime.now(),
        )
    except Exception as e:
        write_job_log(
            job_name="region_analytics_refresh",
            job_type="analytics_sync",
            target_region="서울",
            status="FAILED",
            processed_count=0,
            error_message=str(e),
            run_started_at=started_at,
            run_finished_at=datetime.now(),
        )
    finally:
        db.close()


def register_default_jobs() -> None:
    if scheduler.get_job("weather_sync_job") is None:
        scheduler.add_job(
            run_weather_sync_job,
            CronTrigger(hour="*/6", minute=0),
            id="weather_sync_job",
            replace_existing=True,
        )

    if scheduler.get_job("festival_sync_job") is None:
        scheduler.add_job(
            run_festival_sync_job,
            CronTrigger(hour=4, minute=10),
            id="festival_sync_job",
            replace_existing=True,
        )

    if scheduler.get_job("region_analytics_refresh_job") is None:
        scheduler.add_job(
            run_region_analytics_refresh_job,
            CronTrigger(hour=3, minute=30),
            id="region_analytics_refresh_job",
            replace_existing=True,
        )


def start_scheduler() -> None:
    if not scheduler.running:
        register_default_jobs()
        scheduler.start()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def get_scheduler_status() -> Dict:
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": str(job.name),
                "next_run_time": str(job.next_run_time),
                "trigger": str(job.trigger),
            }
        )

    return {
        "running": scheduler.running,
        "job_count": len(jobs),
        "jobs": jobs,
    }