"""
GPT Vision 분석 모듈
- 무드별 비주얼 방향 + 퀄리티 suffix 동적 생성
- 힙하고 자연스러운 한국어 카피
- Structured Outputs (beta.parse) 로 안정적인 파싱
"""

import base64
import json
import logging
import os
from typing import Optional

from openai import AsyncOpenAI
from pydantic import BaseModel

# 무드별 카피 톤 + 비주얼 방향 + 퀄리티 suffix
# 키는 README/프론트 무드명과 동일하게 유지
MOOD_CONFIGS: dict[str, dict] = {
    "따뜻한 매장 분위기": {
        "copy_tone": (
            "포근하고 정겨운 감성. 단골손님에게 말하듯 친근하게. "
            "매장의 온기와 사람 냄새가 느껴지는 언어."
        ),
        "visual": (
            "warm wooden table surface, soft bokeh candlelight background, "
            "amber and honey tones, cozy interior blur, steam rising from food, "
            "gentle window side light"
        ),
        "quality": (
            "warm lifestyle photography, golden hour glow, "
            "cozy café Instagram aesthetic, soft natural light, "
            "inviting and heartwarming mood"
        ),
    },
    "깔끔한 상품 홍보": {
        "copy_tone": (
            "명확하고 직관적. 제품의 강점을 한 문장으로. "
            "군더더기 없이 핵심만. 신뢰감 있는 언어."
        ),
        "visual": (
            "clean white or light grey seamless studio background, "
            "sharp product focus, soft even box lighting, "
            "commercial studio setup, bold negative space"
        ),
        "quality": (
            "professional commercial product photography, "
            "crisp studio lighting, catalog style, "
            "clean sharp details, high clarity"
        ),
    },
    "트렌디한 메뉴 홍보": {
        "copy_tone": (
            "MZ세대 감성. 위트 있고 힙하게. "
            "SNS에서 바이럴될 것 같은 에너지. 짧고 강렬한 임팩트."
        ),
        "visual": (
            "vibrant pop colors, overhead flat lay or 45-degree angle shot, "
            "trendy café table with bold props, neon or pastel color accents, "
            "dynamic modern composition"
        ),
        "quality": (
            "vivid Instagram food photography, high saturation, "
            "trendy aesthetic, social media ready, "
            "bold and eye-catching composition"
        ),
    },
    "프리미엄 매장·상품": {
        "copy_tone": (
            "절제된 고급스러움. 가치를 말하는 언어. "
            "설명 없이 존재감으로. 명품 브랜드처럼 짧고 품격 있게."
        ),
        "visual": (
            "dark marble or slate surface, premium packaging and elegant props, "
            "dramatic single rim light source, rich deep tones, "
            "high-end restaurant ambiance"
        ),
        "quality": (
            "luxury brand campaign photography, "
            "editorial high-end aesthetic, cinematic chiaroscuro lighting, "
            "premium dark palette, Vogue-level finish"
        ),
    },
}

DEFAULT_MOOD = "깔끔한 상품 홍보"


def resolve_mood(mood: str) -> str:
    """무드명을 검증하고 없으면 기본값 반환."""
    return mood if mood in MOOD_CONFIGS else DEFAULT_MOOD


# GPT가 실제로 반환하는 raw 구조 (bg_prompts는 quality suffix 미포함)
class _RawOutput(BaseModel):
    product_description: str
    ad_copies: list[str]
    bg_prompts: list[str]
    hashtags: list[str]
    details: list[str]


class AnalysisResult(BaseModel):
    product_description: str
    ad_copies: list[str]
    bg_prompts: list[str]
    hashtags: list[str]
    details: list[str]   # 재료·특징 등 포스터 상세 문구 (최대 4개)


async def analyze_and_generate_prompts(
    image_bytes: bytes,
    user_prompt: str = "",
    mood: str = DEFAULT_MOOD,
    client: Optional[AsyncOpenAI] = None,
) -> AnalysisResult:
    if client is None:
        raise ValueError("OpenAI client가 필요합니다. FastAPI lifespan에서 생성된 client를 전달하세요.")

    mood = resolve_mood(mood)
    mood_cfg = MOOD_CONFIGS.get(mood, MOOD_CONFIGS[DEFAULT_MOOD])
    image_b64 = base64.b64encode(image_bytes).decode()
    user_text = (
        f"참고 상황/맥락: {user_prompt}\n"
        "위 상황의 감성과 분위기를 광고 카피와 배경 씬(bg_prompts) 모두에 반영해주세요. "
        "카피에는 그대로 쓰지 말고 감각으로 해석하고, "
        "배경에는 상황에 어울리는 환경·조명·분위기 키워드를 추가하세요."
        if user_prompt else "이미지를 분석하고 JSON을 반환하세요."
    )

    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    messages = [
        {"role": "system", "content": _build_system_prompt(mood, mood_cfg)},
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
    ]

    # reasoning 모델(gpt-5-mini 등)은 plain text가 가장 안정적 → 먼저 시도
    try:
        plain_messages = messages + [
            {"role": "user", "content": (
                "반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이 JSON만 출력하세요:\n"
                "{\n"
                '  "product_description": "제품/음식 설명 (한국어 1문장)",\n'
                '  "ad_copies": ["광고 문구1", "광고 문구2"],\n'
                '  "bg_prompts": ["background scene in English keywords"],\n'
                '  "hashtags": ["#태그1", "#태그2", "#태그3"],\n'
                '  "details": ["상세 문구1", "상세 문구2"]\n'
                "}"
            )}
        ]
        response = await client.chat.completions.create(
            model=model,
            messages=plain_messages,
        )
        content = response.choices[0].message.content or ""
        if content:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > 0:
                data = json.loads(content[start:end])
                raw = _RawOutput(**{k: data.get(k, [] if k != "product_description" else "") for k in _RawOutput.model_fields})
                if not raw.bg_prompts or not raw.ad_copies:
                    raise RuntimeError(f"GPT 응답에 필수 필드 누락. bg_prompts={raw.bg_prompts}, ad_copies={raw.ad_copies}")
                return _enrich_result(raw, mood_cfg)
        logging.warning("[plain text] 응답에서 JSON 추출 실패, structured output 시도")
    except RuntimeError:
        raise
    except Exception as e:
        logging.warning(f"[plain text 실패] {e}")

    try:
        # Fallback: Structured Outputs (beta.parse)
        response = await client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=_RawOutput,
        )
        choice = response.choices[0]
        if choice.message.refusal:
            raise RuntimeError(f"GPT가 요청을 거절했습니다: {choice.message.refusal}")
        raw: _RawOutput = choice.message.parsed
        if raw is None:
            raise RuntimeError(f"GPT 응답 파싱 실패. finish_reason={choice.finish_reason}")
        return _enrich_result(raw, mood_cfg)

    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"이미지 분석 실패: {e}") from e


def _build_system_prompt(mood: str, mood_cfg: dict) -> str:
    return f"""당신은 한국의 힙한 브랜드 크리에이티브 디렉터입니다.
제품 이미지를 보고 선택된 무드에 맞는 광고 소재를 기획합니다.

━━━ 선택된 무드: {mood} ━━━
카피 톤: {mood_cfg["copy_tone"]}
비주얼 방향: {mood_cfg["visual"]}

━━━ 광고 문구 규칙 ━━━
- 10~16자 이내. 짧을수록 강렬함
- 가격·할인·%는 사용자가 명시한 경우에만 포함, 그 외에는 절대 사용 금지
- 설명하지 말고 감각으로 전달
  나쁜 예: "담백한 갈비탕, 점심 30% 할인" → 너무 설명적
  좋은 예: "오늘 점심, 제대로" / "진한 위로 한 그릇" / "국물이 답이다"
- 무드 카피 톤을 철저히 따를 것
- 참고 상황/맥락이 있으면 그것을 그대로 쓰지 말고 감성과 분위기로 해석해서 녹여낼 것
  나쁜 예: "여름 이벤트 특가" (상황을 그대로 설명)
  좋은 예: "이 여름, 딱 한 번" / "뜨거운 계절의 선택" (상황을 감각으로 표현)
- 단, 가격·할인·% 등 구체적 수치는 명시된 경우 그대로 포함

━━━ 배경 프롬프트 규칙 ━━━
- 영어 쉼표 구분 키워드 나열 (형용사+명사 조합)
- 접두사 절대 금지: "Background prompt:", "Here is:", "Scene:" 등 일절 붙이지 말 것
- 배경 환경·표면·조명만 묘사. 제품·음식·음료·사람·손·텍스트·로고 절대 포함 금지
- 제품이 놓일 중앙 공간을 비워두는 구도 (empty center, clear surface, no objects in center)
- 사용자 요청사항에 환경·장소·분위기 관련 내용이 있으면 배경 키워드에 반영할 것
- 올바른 예시: "warm wooden table surface, soft candlelight bokeh, amber tones, cozy blur, empty center"
- 잘못된 예시: "galbi soup in a bowl on table" (음식 포함 금지), "Background prompt: ..." (접두사 금지)

━━━ 해시태그 규칙 ━━━
- 5~8개, # 포함, 한국어
- 제품·무드·상황 관련 태그 혼합
- 예: #소상공인마케팅 #카페광고 #음식스타그램

━━━ 상세 문구(details) 규칙 ━━━
- 포스터에 작게 들어갈 재료·원산지·특징 문구, 2~4개
- 10~20자 이내, 한국어, 간결하게
- 예: "국내산 밀가루 100%", "매일 아침 직접 굽는", "무방부제·무색소"
- 음식이면 재료·원산지, 제품이면 소재·특징·인증 중심

반드시 JSON 형식으로만 응답하세요."""


def _enrich_result(raw: _RawOutput, mood_cfg: dict) -> AnalysisResult:
    """bg_prompts에 무드별 quality suffix를 추가해 최종 AnalysisResult 반환."""
    quality = mood_cfg["quality"]
    enriched_prompts = [f"{p}, {quality}" for p in raw.bg_prompts]

    return AnalysisResult(
        product_description=raw.product_description,
        ad_copies=raw.ad_copies,
        bg_prompts=enriched_prompts,
        hashtags=raw.hashtags,
        details=raw.details,
    )
