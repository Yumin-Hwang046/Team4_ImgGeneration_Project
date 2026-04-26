import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

SEOUL_OPEN_API_KEY = os.getenv("SEOUL_OPEN_API_KEY", "")
SEOUL_LIVING_POP_SERVICE = os.getenv("SEOUL_LIVING_POP_SERVICE", "")
SBIZ_SERVICE_KEY = os.getenv("SBIZ_SERVICE_KEY", "")
SBIZ_API_URL = os.getenv("SBIZ_API_URL", "")

SEOUL_OPEN_API_BASE = "http://openapi.seoul.go.kr:8088"
DEFAULT_SEOUL_LIVING_POP_SERVICE = "VwsmAdstrdFlpopW"
DEFAULT_SBIZ_API_URL = (
    "https://apis.data.go.kr/B553077/api/open/sdctrdartrdarinfopd/storeListInDong"
)


def get_region_name_from_profile(profile) -> str:
    return " ".join(
        [value for value in [profile.sido, profile.sigungu, profile.emd] if value]
    ).strip() or profile.road_address


def get_target_analysis_date() -> date:
    # 서울 생활인구는 안내상 5일 전 기준으로 보는 게 안전
    return date.today() - timedelta(days=5)


def map_business_category_to_keywords(category: str) -> List[str]:
    mapping = {
        "카페 & 베이커리": ["카페", "커피", "베이커리", "디저트"],
        "한식당": ["한식", "백반", "국밥", "한정식"],
        "주점": ["주점", "포차", "호프", "술집"],
        "양식 & 레스토랑": ["양식", "레스토랑", "파스타", "스테이크"],
        "일식 & 아시안": ["일식", "초밥", "라멘", "아시안"],
        "분식 & 패스트푸드": ["분식", "김밥", "떡볶이", "패스트푸드"],
        "고기 & 구이": ["고기", "구이", "삼겹살", "갈비"],
    }
    return mapping.get(category, [category])


def call_seoul_open_api(service_name: str, start: int = 1, end: int = 1000) -> Dict[str, Any]:
    if not SEOUL_OPEN_API_KEY:
        raise RuntimeError("SEOUL_OPEN_API_KEY가 설정되지 않았습니다.")

    url = f"{SEOUL_OPEN_API_BASE}/{SEOUL_OPEN_API_KEY}/json/{service_name}/{start}/{end}"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.json()


def extract_rows_from_seoul_response(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    for _, value in payload.items():
        if isinstance(value, dict) and "row" in value:
            rows = value.get("row", [])
            if isinstance(rows, list):
                return rows
    return []


def safe_int(value: Any) -> Optional[int]:
    if value in (None, "", "*"):
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except Exception:
        return None


def parse_living_population_row(row: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    possible_code_keys = ["ADSTRD_CD", "ADMDONG_CD", "AREA_CD", "SIGNGU_CODE", "ADM_CD"]
    possible_name_keys = ["ADSTRD_NM", "ADMDONG_NM", "AREA_NM", "SIGNGU_NM", "ADM_NM"]
    possible_pop_keys = [
        "TOT_LVPOP_CO",
        "LIVE_POP",
        "LIVE_POP_CNT",
        "TOT_POP",
        "POP_CNT",
        "TMZON_PPLTN_CO",
    ]

    legal_code = None
    region_name = None
    population = None

    for key in possible_code_keys:
        if key in row and row[key]:
            legal_code = str(row[key])
            break

    for key in possible_name_keys:
        if key in row and row[key]:
            region_name = str(row[key])
            break

    for key in possible_pop_keys:
        if key in row:
            population = safe_int(row.get(key))
            if population is not None:
                break

    return legal_code, region_name, population


def fetch_seoul_floating_population(profile) -> Tuple[Optional[int], Dict[str, Any]]:
    if not profile.sido or "서울" not in str(profile.sido):
        return None, {"source": "SEOUL_OPEN_API", "reason": "NOT_SEOUL"}

    target_date = get_target_analysis_date()
    region_name = get_region_name_from_profile(profile)

    service_name = (SEOUL_LIVING_POP_SERVICE or "").strip() or DEFAULT_SEOUL_LIVING_POP_SERVICE
    payload = call_seoul_open_api(service_name, 1, 1000)
    rows = extract_rows_from_seoul_response(payload)

    if not rows:
        return None, {
            "source": "SEOUL_OPEN_API",
            "analysis_date": target_date.isoformat(),
            "region_name": region_name,
            "reason": "NO_ROWS",
            "raw": payload,
        }

    target_code = str(profile.legal_code).strip() if profile.legal_code else None
    matched_population = None
    matched_row = None

    if target_code:
        for row in rows:
            code, _, population = parse_living_population_row(row)
            if code and target_code in code:
                matched_population = population
                matched_row = row
                break

    if matched_row is None:
        for row in rows:
            _, row_region_name, population = parse_living_population_row(row)
            if row_region_name and profile.emd and str(profile.emd) in row_region_name:
                matched_population = population
                matched_row = row
                break

    raw = {
        "source": "SEOUL_OPEN_API",
        "analysis_date": target_date.isoformat(),
        "region_name": region_name,
        "matched_row": matched_row,
    }
    return matched_population, raw


def call_sbiz_api(params: Dict[str, Any]) -> Dict[str, Any]:
    if not SBIZ_SERVICE_KEY:
        raise RuntimeError("SBIZ_SERVICE_KEY가 설정되지 않았습니다.")

    sbiz_url = (SBIZ_API_URL or "").strip() or DEFAULT_SBIZ_API_URL

    query = {
        "serviceKey": SBIZ_SERVICE_KEY,
        "numOfRows": 100,
        "pageNo": 1,
        "type": "json",
    }
    query.update(params)

    resp = requests.get(sbiz_url, params=query, timeout=20)
    resp.raise_for_status()
    return resp.json()


def extract_sbiz_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = [
        ("items",),
        ("body", "items"),
        ("response", "body", "items"),
        ("body", "items", "item"),
        ("response", "body", "items", "item"),
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
            if isinstance(node, dict) and "item" in node and isinstance(node["item"], list):
                return node["item"]

    return []


def match_store_category(item: Dict[str, Any], keywords: List[str]) -> bool:
    text_candidates = [
        str(item.get("indsLclsNm", "")),
        str(item.get("indsMclsNm", "")),
        str(item.get("indsSclsNm", "")),
        str(item.get("bizesNm", "")),
        str(item.get("ksicNm", "")),
    ]
    joined = " ".join(text_candidates)
    return any(keyword in joined for keyword in keywords)


def build_top_categories(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counter: Dict[str, int] = {}
    for item in items:
        name = (
            item.get("indsMclsNm")
            or item.get("indsSclsNm")
            or item.get("indsLclsNm")
            or "기타"
        )
        counter[name] = counter.get(name, 0) + 1

    sorted_items = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:5]
    return [{"category": name, "count": count} for name, count in sorted_items]


def fetch_competitor_stats(profile) -> Tuple[Optional[int], List[Dict[str, Any]], Dict[str, Any]]:
    region_name = get_region_name_from_profile(profile)
    keywords = map_business_category_to_keywords(profile.business_category)

    params = {
        "divId": "ctprvnCd",
        "key": profile.sigungu or profile.sido or region_name,
    }

    payload = call_sbiz_api(params)
    items = extract_sbiz_items(payload)

    matched = [item for item in items if match_store_category(item, keywords)]
    competitor_count = len(matched)
    top_categories = build_top_categories(items)

    raw = {
        "source": "SBIZ_API",
        "region_name": region_name,
        "request_params": params,
        "total_items": len(items),
        "matched_items_count": len(matched),
    }

    return competitor_count, top_categories, {"meta": raw, "raw": payload}


def build_region_summary(
    *,
    region_name: str,
    business_category: str,
    floating_population: Optional[int],
    competitor_count: Optional[int],
) -> str:
    population_text = (
        f"유동인구는 약 {floating_population:,}명 수준으로 추정됩니다."
        if floating_population is not None
        else "유동인구 데이터는 아직 확보되지 않았습니다."
    )

    competitor_text = (
        f"동일/유사업종 경쟁업체는 약 {competitor_count}개로 추정됩니다."
        if competitor_count is not None
        else "경쟁업체 데이터는 아직 확보되지 않았습니다."
    )

    return (
        f"{region_name} 기준 {business_category} 상권 분석 결과입니다. "
        f"{population_text} {competitor_text}"
    )


def build_region_analytics_result(profile) -> Dict[str, Any]:
    region_name = get_region_name_from_profile(profile)

    floating_population = None
    competitor_count = None
    top_categories: List[Dict[str, Any]] = []
    raw_payload: Dict[str, Any] = {}
    source_name = "PARTIAL"

    try:
        floating_population, seoul_raw = fetch_seoul_floating_population(profile)
        raw_payload["seoul_living_population"] = seoul_raw
    except Exception as e:
        raw_payload["seoul_living_population_error"] = str(e)

    try:
        competitor_count, top_categories, sbiz_raw = fetch_competitor_stats(profile)
        raw_payload["sbiz_competitors"] = sbiz_raw
    except Exception as e:
        raw_payload["sbiz_competitors_error"] = str(e)

    if floating_population is not None and competitor_count is not None:
        source_name = "SEOUL_OPEN_API+SBIZ_API"
    elif floating_population is not None:
        source_name = "SEOUL_OPEN_API"
    elif competitor_count is not None:
        source_name = "SBIZ_API"

    summary_text = build_region_summary(
        region_name=region_name,
        business_category=profile.business_category,
        floating_population=floating_population,
        competitor_count=competitor_count,
    )

    return {
        "analysis_date": get_target_analysis_date(),
        "region_name": region_name,
        "legal_code": profile.legal_code,
        "floating_population": floating_population,
        "competitor_count": competitor_count,
        "top_categories_json": json.dumps(top_categories, ensure_ascii=False),
        "summary_text": summary_text,
        "source_name": source_name,
        "raw_payload": json.dumps(raw_payload, ensure_ascii=False),
    }
