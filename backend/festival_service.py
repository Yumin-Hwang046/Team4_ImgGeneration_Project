import os
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

TOUR_API_SERVICE_KEY = os.getenv("TOUR_API_SERVICE_KEY", "")
TOUR_API_EVENTS_URL = os.getenv("TOUR_API_EVENTS_URL", "")

PRIMARY_RADIUS_KM = 2.0
SECONDARY_RADIUS_KM = 5.0
MAX_FINAL_EVENTS = 5


def get_region_name_from_profile(profile) -> str:
    return " ".join(
        [value for value in [profile.sido, profile.sigungu, profile.emd] if value]
    ).strip() or profile.road_address


def parse_yyyymmdd(value: Any) -> Optional[date]:
    if not value:
        return None

    value = str(value).strip()
    if len(value) != 8 or not value.isdigit():
        return None

    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except Exception:
        return None


def safe_float(value: Any) -> Optional[float]:
    if value in (None, "", "*"):
        return None
    try:
        return float(value)
    except Exception:
        return None


def extract_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = [
        ("response", "body", "items", "item"),
        ("body", "items", "item"),
        ("items", "item"),
        ("items",),
    ]

    for path in candidates:
        node = payload
        ok = True
        for key in path:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                ok = False
                break
        if ok:
            if isinstance(node, list):
                return node
            if isinstance(node, dict):
                return [node]

    return []


def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    radius = 6371.0

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def geocode_profile_if_needed(profile) -> Tuple[Optional[float], Optional[float]]:
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


def normalize_event(item: Dict[str, Any]) -> Dict[str, Any]:
    start_date = parse_yyyymmdd(item.get("eventstartdate"))
    end_date = parse_yyyymmdd(item.get("eventenddate")) or start_date

    latitude = safe_float(item.get("mapy"))
    longitude = safe_float(item.get("mapx"))

    duration_days = 0
    if start_date and end_date:
        duration_days = (end_date - start_date).days + 1

    # 90일 이상이면 장기행사로 후순위 표시
    event_type = "festival_long" if duration_days >= 90 else "festival"

    return {
        "external_id": str(item.get("contentid") or ""),
        "title": str(item.get("title") or "행사/축제"),
        "description": str(item.get("overview") or ""),
        "location": str(item.get("addr1") or ""),
        "road_address": str(item.get("addr1") or ""),
        "jibun_address": str(item.get("addr2") or ""),
        "event_start_date": start_date,
        "event_end_date": end_date,
        "source_name": "KTO_TOUR_API",
        "source_url": str(item.get("homepage") or ""),
        "latitude": latitude,
        "longitude": longitude,
        "event_type": event_type,
        "is_auto_collected": 1,
    }

def expand_event_dates(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    start_date = event.get("event_start_date")
    end_date = event.get("event_end_date")

    if not start_date:
        return []

    if not end_date or end_date < start_date:
        end_date = start_date

    if (end_date - start_date).days > 60:
        end_date = start_date + timedelta(days=60)

    rows = []
    current = start_date
    while current <= end_date:
        row = dict(event)
        row["event_date"] = current
        rows.append(row)
        current += timedelta(days=1)

    return rows


def filter_by_radius(profile, normalized_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    base_lat, base_lon = geocode_profile_if_needed(profile)
    if base_lat is None or base_lon is None:
        return {
            "selected_items": [],
            "within_primary": [],
            "within_secondary": [],
            "base_lat": None,
            "base_lon": None,
        }

    within_primary: List[Dict[str, Any]] = []
    within_secondary: List[Dict[str, Any]] = []

    for item in normalized_items:
        lat = item.get("latitude")
        lon = item.get("longitude")
        if lat is None or lon is None:
            continue

        distance = haversine_km(base_lat, base_lon, float(lat), float(lon))
        item["distance_km"] = round(distance, 2)

        if distance <= PRIMARY_RADIUS_KM:
            within_primary.append(item)
        elif distance <= SECONDARY_RADIUS_KM:
            within_secondary.append(item)

    within_primary = sorted(within_primary, key=lambda x: x.get("distance_km", 9999))
    within_secondary = sorted(within_secondary, key=lambda x: x.get("distance_km", 9999))

    selected_items: List[Dict[str, Any]] = []
    if within_primary:
        selected_items = within_primary[:MAX_FINAL_EVENTS]
    elif within_secondary:
        selected_items = within_secondary[:MAX_FINAL_EVENTS]

    return {
        "selected_items": selected_items,
        "within_primary": within_primary,
        "within_secondary": within_secondary,
        "base_lat": base_lat,
        "base_lon": base_lon,
    }


def filter_by_region_fallback(profile, normalized_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    for item in normalized_items:
        full_addr = f"{item.get('road_address', '')} {item.get('jibun_address', '')}".strip()
        if not full_addr:
            continue

        if profile.sido and profile.sido not in full_addr:
            continue

        if profile.sigungu and profile.sigungu in full_addr:
            results.append(item)
            continue

        if profile.emd and profile.emd in full_addr:
            results.append(item)
            continue

        if profile.sido and "서울" in str(profile.sido):
            results.append(item)

    return results[:MAX_FINAL_EVENTS]


def fetch_kto_festival_items_raw(profile) -> Dict[str, Any]:
    if not TOUR_API_SERVICE_KEY:
        raise RuntimeError(f"TOUR_API_SERVICE_KEY가 설정되지 않았습니다. env_path={ENV_PATH}")
    if not TOUR_API_EVENTS_URL:
        raise RuntimeError(f"TOUR_API_EVENTS_URL이 설정되지 않았습니다. env_path={ENV_PATH}")

    start_date = (date.today() - timedelta(days=7)).strftime("%Y%m%d")
    end_date = (date.today() + timedelta(days=60)).strftime("%Y%m%d")

    params = {
        "serviceKey": TOUR_API_SERVICE_KEY,
        "MobileOS": "ETC",
        "MobileApp": "Team4Project",
        "_type": "json",
        "arrange": "A",
        "numOfRows": 200,
        "pageNo": 1,
        "eventStartDate": start_date,
        "eventEndDate": end_date,
    }

    resp = requests.get(TOUR_API_EVENTS_URL, params=params, timeout=20)
    resp.raise_for_status()

    payload = resp.json()
    raw_items = extract_items(payload)

    return {
        "params": params,
        "payload": payload,
        "raw_items": raw_items,
        "http_status": resp.status_code,
        "request_url": resp.url,
        "response_preview": resp.text[:1000],
        "payload_top_keys": list(payload.keys()) if isinstance(payload, dict) else [],
    }


def build_festival_debug_result(profile) -> Dict[str, Any]:
    raw_result = fetch_kto_festival_items_raw(profile)
    raw_items = raw_result["raw_items"]
    normalized_items = [normalize_event(item) for item in raw_items]

    radius_result = filter_by_radius(profile, normalized_items)
    radius_selected = radius_result["selected_items"]
    region_fallback = filter_by_region_fallback(profile, normalized_items)

    final_items = radius_selected if radius_selected else region_fallback

    sample_raw = []
    for item in raw_items[:5]:
        sample_raw.append(
            {
                "title": item.get("title"),
                "addr1": item.get("addr1"),
                "addr2": item.get("addr2"),
                "eventstartdate": item.get("eventstartdate"),
                "eventenddate": item.get("eventenddate"),
                "mapx": item.get("mapx"),
                "mapy": item.get("mapy"),
            }
        )

    sample_radius = []
    for item in radius_result["within_primary"][:5] + radius_result["within_secondary"][:5]:
        sample_radius.append(
            {
                "title": item.get("title"),
                "road_address": item.get("road_address"),
                "distance_km": item.get("distance_km"),
            }
        )

    sample_final = []
    for item in final_items[:5]:
        sample_final.append(
            {
                "title": item.get("title"),
                "road_address": item.get("road_address"),
                "event_start_date": str(item.get("event_start_date")),
                "event_end_date": str(item.get("event_end_date")),
                "distance_km": item.get("distance_km"),
            }
        )

    return {
        "region_name": get_region_name_from_profile(profile),
        "profile_latitude": radius_result.get("base_lat"),
        "profile_longitude": radius_result.get("base_lon"),
        "request_params": raw_result["params"],
        "request_url": raw_result["request_url"],
        "http_status": raw_result["http_status"],
        "payload_top_keys": raw_result["payload_top_keys"],
        "response_preview": raw_result["response_preview"],
        "raw_count": len(raw_items),
        "normalized_count": len(normalized_items),
        "within_primary_count": len(radius_result["within_primary"]),
        "within_secondary_count": len(radius_result["within_secondary"]),
        "region_fallback_count": len(region_fallback),
        "final_count": len(final_items),
        "sample_raw": sample_raw,
        "sample_radius": sample_radius,
        "sample_final": sample_final,
    }


def fetch_kto_festival_items(profile) -> List[Dict[str, Any]]:
    raw_result = fetch_kto_festival_items_raw(profile)
    raw_items = raw_result["raw_items"]
    normalized_items = [normalize_event(item) for item in raw_items]

    radius_result = filter_by_radius(profile, normalized_items)
    radius_selected = radius_result["selected_items"]
    if radius_selected:
        return radius_selected

    region_filtered = filter_by_region_fallback(profile, normalized_items)
    if region_filtered:
        return region_filtered

    return []


def build_festival_event_rows_for_profile(profile) -> List[Dict[str, Any]]:
    filtered_items = fetch_kto_festival_items(profile)

    rows: List[Dict[str, Any]] = []
    for item in filtered_items:
        rows.extend(expand_event_dates(item))

    return rows