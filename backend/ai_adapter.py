from typing import Any, Dict


def normalize_image_result(raw_result: Any) -> Dict:
    if not isinstance(raw_result, dict):
        raw_result = {}

    return {
        "success": bool(raw_result.get("success", False)),
        "image_url": raw_result.get("image_url"),
        "prompt_used": raw_result.get("prompt_used", ""),
        "error": raw_result.get("error"),
    }


def normalize_text_result(raw_result: Any) -> Dict:
    if not isinstance(raw_result, dict):
        raw_result = {}

    hashtags = raw_result.get("hashtags", [])
    if hashtags is None:
        hashtags = []
    if not isinstance(hashtags, list):
        hashtags = []

    return {
        "success": bool(raw_result.get("success", False)),
        "copy": raw_result.get("copy", ""),
        "hashtags": hashtags,
        "error": raw_result.get("error"),
    }