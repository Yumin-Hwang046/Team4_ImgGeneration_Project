"""
광고 문구 생성 전용 모듈 (문구 만들기 마법사)

image_analyzer와의 차이:
- image_analyzer: 이미지 파이프라인 원샷 (분석 + bg_prompt + 카피 한 번에)
- text_generator: 문구 품질에 집중, 스타일별 3개 변형 제안, 이미지/텍스트 모두 지원
"""

import base64
import json
import os
import re

from openai import AsyncOpenAI
from pydantic import BaseModel

from image_analyzer.analyzer import MOOD_CONFIGS, resolve_mood, DEFAULT_MOOD


class CopyVariant(BaseModel):
    style: str        # 감성형 | 직접형 | 스토리형
    headline: str     # 메인 광고 문구 (10~16자)
    tagline: str      # 보조 문구 / 서브카피 (15~30자)


class CopyResult(BaseModel):
    product_description: str
    variants: list[CopyVariant]   # 3개 스타일별 제안
    hashtags: list[str]           # 5~8개


async def generate_copy_from_image(
    image_bytes: bytes,
    mood: str = DEFAULT_MOOD,
    user_prompt: str = "",
    client: AsyncOpenAI = None,
) -> CopyResult:
    """이미지 기반 광고 문구 생성 (GPT Vision)."""
    if client is None:
        raise ValueError("OpenAI client가 필요합니다. FastAPI lifespan에서 생성된 client를 전달하세요.")

    mood = resolve_mood(mood)
    mood_cfg = MOOD_CONFIGS.get(mood, MOOD_CONFIGS[DEFAULT_MOOD])
    image_b64 = base64.b64encode(image_bytes).decode()
    user_text = f"추가 요청사항: {user_prompt}" if user_prompt else "이미지를 분석하고 JSON을 반환하세요."

    try:
        response = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            messages=[
                {"role": "system", "content": _build_copy_prompt(mood, mood_cfg)},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                        {"type": "text", "text": user_text},
                    ],
                },
            ],
        )
        content = response.choices[0].message.content or ""
        if not content:
            raise RuntimeError("GPT 응답이 비어있습니다.")
        return _parse_copy_result(content)

    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"문구 생성 실패: {e}") from e


async def generate_copy_from_text(
    description: str,
    mood: str = DEFAULT_MOOD,
    user_prompt: str = "",
    client: AsyncOpenAI = None,
) -> CopyResult:
    """텍스트 설명 기반 광고 문구 생성 (이미지 없이)."""
    if client is None:
        raise ValueError("OpenAI client가 필요합니다. FastAPI lifespan에서 생성된 client를 전달하세요.")

    mood = resolve_mood(mood)
    mood_cfg = MOOD_CONFIGS.get(mood, MOOD_CONFIGS[DEFAULT_MOOD])

    extra = f"\n추가 요청사항: {user_prompt}" if user_prompt else ""
    user_text = f"제품/매장 설명: {description}{extra}"

    try:
        response = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            messages=[
                {"role": "system", "content": _build_copy_prompt(mood, mood_cfg)},
                {"role": "user", "content": user_text},
            ],
        )
        content = response.choices[0].message.content or ""
        if not content:
            raise RuntimeError("GPT 응답이 비어있습니다.")
        return _parse_copy_result(content)

    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"문구 생성 실패: {e}") from e


def _build_copy_prompt(mood: str, mood_cfg: dict) -> str:
    return f"""당신은 한국 소상공인 전문 광고 카피라이터입니다.
제품/매장을 분석하고 무드에 맞는 광고 문구 3종을 제안합니다.

반드시 아래 JSON 형식만 반환하세요:

{{
  "product_description": "제품/매장 설명 (1문장, 한국어)",
  "variants": [
    {{
      "style": "감성형",
      "headline": "메인 광고 문구",
      "tagline": "보조 문구"
    }},
    {{
      "style": "직접형",
      "headline": "메인 광고 문구",
      "tagline": "보조 문구"
    }},
    {{
      "style": "스토리형",
      "headline": "메인 광고 문구",
      "tagline": "보조 문구"
    }}
  ],
  "hashtags": ["#태그1", "#태그2", "#태그3", "#태그4", "#태그5"]
}}

━━━ 선택된 무드: {mood} ━━━
카피 톤: {mood_cfg["copy_tone"]}

━━━ 3가지 스타일 정의 ━━━
- 감성형: 감정과 분위기로 소구. 공감과 따뜻함. "이 제품을 쓰면 어떤 기분일까"를 그림
- 직접형: 제품의 핵심 강점을 직구. 명확하고 신뢰감. "왜 이걸 사야 하나"를 한 방에
- 스토리형: 장면·상황을 묘사. 고객이 주인공이 되는 서사. "언제 어디서 누가"를 자연스럽게

━━━ headline 규칙 ━━━
- 10~16자 이내. 짧을수록 강렬함
- 가격·할인·%는 사용자가 명시한 경우에만
- 무드 카피 톤 철저히 반영

━━━ tagline 규칙 ━━━
- 15~30자. headline을 보완하는 서브카피
- 구체적인 장면·감각·상황 묘사
- 예: "바쁜 점심, 든든하게 채우는 한 그릇" / "오늘 하루의 쉼표가 되어줄게요"

━━━ 해시태그 규칙 ━━━
- 5~8개, # 포함, 한국어
- 제품·무드·상황·지역 관련 태그 혼합
- JSON 외 다른 텍스트 절대 반환 금지"""


def _parse_copy_result(content: str) -> CopyResult:
    content = content.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        content = match.group(1)
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        content = match.group(0)

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"GPT 응답 파싱 실패: {e}\n응답: {content[:200]}") from e

    variants = [
        CopyVariant(
            style=v.get("style", ""),
            headline=v.get("headline", ""),
            tagline=v.get("tagline", ""),
        )
        for v in data.get("variants", [])
    ]

    return CopyResult(
        product_description=data.get("product_description", ""),
        variants=variants,
        hashtags=data.get("hashtags", []),
    )
