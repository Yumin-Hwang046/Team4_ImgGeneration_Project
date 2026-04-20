from typing import Optional


SYSTEM_PERSONA = """
당신은 소상공인 인스타그램 마케팅 카피라이터입니다.
입력된 업종, 메뉴, 지역, 날씨, 계절, 목적, 무드, 추천 컨셉, 추가 요청을 바탕으로
실제 게시물에 바로 넣을 수 있는 짧고 매력적인 한국어 홍보 문구를 작성합니다.
""".strip()


OUTPUT_CONSTRAINTS = """
[출력 규칙]
1. 반드시 JSON 객체로만 응답합니다.
2. 형식은 {"copy": "...", "hashtags": ["...", "..."]} 입니다.
3. copy는 자연스러운 한국어 문장 1~2문장으로 작성합니다.
4. copy는 너무 길지 않게, 대체로 90자 이내를 권장합니다.
5. hashtags 각 요소에는 #를 붙이지 않습니다.
6. 허위·과장 표현은 피하고, 실제 방문/관심으로 이어질 수 있게 씁니다.
7. 메뉴명과 목적이 자연스럽게 드러나야 합니다.
""".strip()


PURPOSE_GUIDE = {
    "방문 유도": """
- 지금 가보고 싶다는 느낌이 들게 쓰세요.
- 장소감, 분위기, 타이밍을 살려 주세요.
- 너무 광고 문구처럼 딱딱하지 않게 써 주세요.
""".strip(),
    "신메뉴 홍보": """
- '새롭다', '이번에 나왔다'는 느낌이 자연스럽게 드러나게 쓰세요.
- 궁금증을 자극하되 과장하지 마세요.
""".strip(),
    "이벤트 홍보": """
- 지금 확인해야 하는 이유가 드러나게 쓰세요.
- 혜택, 분위기, 참여 동기를 자연스럽게 넣으세요.
""".strip(),
    "매장 홍보": """
- 매장 분위기, 메뉴, 방문 이유가 균형 있게 드러나게 쓰세요.
- 브랜드 첫인상에 도움이 되는 톤으로 쓰세요.
""".strip(),
}


MOOD_GUIDE = {
    "따뜻한 감성": "포근하고 부드러운 톤으로 쓰세요.",
    "따뜻한 매장 분위기": "아늑하고 편안한 분위기를 살려 쓰세요.",
    "깔끔한 상품 홍보": "군더더기 없이 정돈된 톤으로 쓰세요.",
    "트렌디한 메뉴 홍보": "요즘 감각의 경쾌한 톤으로 쓰세요.",
    "프리미엄 매장·상품": "고급스럽고 세련된 톤으로 쓰세요.",
    "힙한 감성": "과하지 않게 감각적이고 요즘 말투로 쓰세요.",
}


def _pick_purpose_guide(purpose: str) -> str:
    return PURPOSE_GUIDE.get(
        (purpose or "").strip(),
        "목적에 맞는 설득 포인트가 자연스럽게 드러나게 작성하세요.",
    )


def _pick_mood_guide(mood: Optional[str]) -> str:
    mood_text = (mood or "").strip()
    if not mood_text:
        return "인스타그램 게시물에 어울리는 자연스러운 홍보 톤으로 작성하세요."
    return MOOD_GUIDE.get(mood_text, f"'{mood_text}' 느낌이 자연스럽게 느껴지도록 작성하세요.")


def build_user_context(
    purpose: str,
    business_category: str,
    menu_name: str,
    location: str,
    mood: Optional[str],
    weather_summary: str,
    season_context: str,
    recommended_concept: str,
    extra_prompt: Optional[str] = None,
) -> str:
    mood_text = mood.strip() if mood else "없음"
    extra_text = extra_prompt.strip() if extra_prompt else "없음"

    return (
        "[콘텐츠 입력]\n"
        f"- 목적: {purpose}\n"
        f"- 업종: {business_category}\n"
        f"- 메뉴: {menu_name}\n"
        f"- 지역: {location}\n"
        f"- 무드: {mood_text}\n"
        f"- 날씨: {weather_summary}\n"
        f"- 시즌: {season_context}\n"
        f"- 추천 컨셉: {recommended_concept}\n"
        f"- 추가 요청: {extra_text}\n"
    )


def get_full_prompt(
    purpose: str,
    business_category: str,
    menu_name: str,
    location: str,
    mood: Optional[str],
    weather_summary: str,
    season_context: str,
    recommended_concept: str,
    extra_prompt: Optional[str] = None,
) -> tuple[str, str]:
    system_prompt = (
        f"{SYSTEM_PERSONA}\n\n"
        "[작성 가이드]\n"
        f"{_pick_purpose_guide(purpose)}\n"
        f"{_pick_mood_guide(mood)}\n"
        "- 너무 설명문처럼 길게 쓰지 말고, 게시물 캡션처럼 써 주세요.\n"
        "- 날씨와 계절 정보는 자연스러울 때만 녹이세요.\n"
        "- 지역이 있다면 장소감이 느껴지게 쓰세요.\n"
        "- 추천 컨셉과 추가 요청이 있으면 우선 반영하세요.\n"
        "- 해시태그는 실사용 가능한 단어 위주로 4~7개 정도 제안하세요.\n\n"
        f"{OUTPUT_CONSTRAINTS}"
    )

    user_prompt = build_user_context(
        purpose=purpose,
        business_category=business_category,
        menu_name=menu_name,
        location=location,
        mood=mood,
        weather_summary=weather_summary,
        season_context=season_context,
        recommended_concept=recommended_concept,
        extra_prompt=extra_prompt,
    )

    return system_prompt, user_prompt