import textwrap


def prepare_overlay_text(text: str, max_chars: int = 60, line_width: int = 18) -> str:
    if not text:
        return ""

    cleaned = text.replace("\n", " ").strip()
    cleaned = " ".join(cleaned.split())

    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "..."

    wrapped = "\n".join(textwrap.wrap(cleaned, width=line_width))
    return wrapped
#텍스트 길이 / 줄바꿈 처리 인스타 업로드 시 텍스트가 깨지지 않기 위함