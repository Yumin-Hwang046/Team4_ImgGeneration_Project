from fastapi import APIRouter

from scheduler_service import (
    get_scheduler_status,
    run_festival_sync_job,
    run_region_analytics_refresh_job,
    run_weather_sync_job,
)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("/status")
def scheduler_status():
    return get_scheduler_status()


@router.post("/run/weather")
def run_weather_now():
    run_weather_sync_job()
    return {"message": "날씨 동기화 작업을 수동 실행했습니다."}


@router.post("/run/festival")
def run_festival_now():
    run_festival_sync_job()
    return {"message": "행사/축제 동기화 작업을 수동 실행했습니다."}


@router.post("/run/analytics")
def run_analytics_now():
    run_region_analytics_refresh_job()
    return {"message": "상권분석 갱신 작업을 수동 실행했습니다."}