from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests


MAX_FORECAST_DAYS = 15


def get_region_name_from_profile(profile) -> str:
    return " ".join(
        [value for value in [profile.sido, profile.sigungu, profile.emd] if value]
    ).strip() or profile.road_address


def weather_code_to_text(code: Optional[int]) -> str:
    weather_map = {
        0: "맑음",
        1: "대체로 맑음",
        2: "부분적으로 흐림",
        3: "흐림",
        45: "안개",
        48: "짙은 안개",
        51: "약한 이슬비",
        53: "보통 이슬비",
        55: "강한 이슬비",
        61: "약한 비",
        63: "비",
        65: "강한 비",
        71: "약한 눈",
        73: "눈",
        75: "강한 눈",
        80: "소나기",
        81: "강한 소나기",
        82: "매우 강한 소나기",
        95: "뇌우",
    }
    if code is None:
        return "날씨 정보 없음"
    return weather_map.get(code, "날씨 정보 없음")


def safe_float(value: Any) -> Optional[float]:
    if value in (None, "", "*"):
        return None
    try:
        return float(value)
    except Exception:
        return None


def geocode_location_from_profile(profile) -> Tuple[Optional[float], Optional[float]]:
    if profile.latitude is not None and profile.longitude is not None:
        return float(profile.latitude), float(profile.longitude)

    query = get_region_name_from_profile(profile)

    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": query,
        "count": 1,
        "language": "ko",
        "format": "json",
    }

    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results")
    if not results:
        return None, None

    return results[0]["latitude"], results[0]["longitude"]


def build_weather_summary(
    weather_code: Optional[int],
    temp_min: Optional[float],
    temp_max: Optional[float],
    precipitation_probability: Optional[float],
) -> str:
    weather_text = weather_code_to_text(weather_code)
    min_text = f"{temp_min:.1f}°C" if temp_min is not None else "?"
    max_text = f"{temp_max:.1f}°C" if temp_max is not None else "?"
    pop_text = f"{precipitation_probability:.0f}%" if precipitation_probability is not None else "?"
    return f"{weather_text}, 최저 {min_text} / 최고 {max_text}, 강수확률 {pop_text}"


def fetch_daily_weather_rows_for_profile(profile) -> List[Dict[str, Any]]:
    lat, lon = geocode_location_from_profile(profile)
    if lat is None or lon is None:
        return []

    today = date.today()
    end_date = today + timedelta(days=MAX_FORECAST_DAYS - 1)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "Asia/Seoul",
        "start_date": today.isoformat(),
        "end_date": end_date.isoformat(),
    }

    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    weather_codes = daily.get("weather_code", [])
    temp_maxs = daily.get("temperature_2m_max", [])
    temp_mins = daily.get("temperature_2m_min", [])
    pops = daily.get("precipitation_probability_max", [])

    region_name = get_region_name_from_profile(profile)

    rows: List[Dict[str, Any]] = []
    for idx, date_str in enumerate(dates):
        weather_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        weather_code = weather_codes[idx] if idx < len(weather_codes) else None
        temp_max = safe_float(temp_maxs[idx]) if idx < len(temp_maxs) else None
        temp_min = safe_float(temp_mins[idx]) if idx < len(temp_mins) else None
        pop = safe_float(pops[idx]) if idx < len(pops) else None

        rows.append(
            {
                "weather_date": weather_date,
                "region_name": region_name,
                "legal_code": profile.legal_code,
                "latitude": lat,
                "longitude": lon,
                "weather_code": weather_code,
                "weather_summary": build_weather_summary(
                    weather_code=weather_code,
                    temp_min=temp_min,
                    temp_max=temp_max,
                    precipitation_probability=pop,
                ),
                "temp_min": temp_min,
                "temp_max": temp_max,
                "precipitation_probability": pop,
                "forecast_type": "forecast",
                "source_name": "OPEN_METEO",
            }
        )

    return rows
