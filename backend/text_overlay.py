import os
from PIL import Image, ImageDraw, ImageFont

try:
    from pilmoji import Pilmoji
    from pilmoji.source import TwitterEmojiSource
    HAS_PILMOJI = True
except ImportError:
    HAS_PILMOJI = False

# 무드별 폰트 파일 매핑 (사용할 실제 .ttf 파일명으로 변경하세요)
MOOD_FONT_MAPPING = {
    "따뜻한 매장 분위기": "NanumBrushScript-Regular.ttf",  # 둥글고 따뜻한 느낌의 폰트
    "깔끔한 상품 홍보": "NotoSansKR-Bold.ttf",         # 깔끔하고 반듯한 고딕 폰트
    "트렌디한 메뉴 홍보": "NotoSansKR-Medium.ttf",   # 두껍고 눈에 띄는 트렌디한 폰트
    "프리미엄 매장·상품": "NotoSansKR-Thin.ttf"      # 고급스럽고 우아한 명조 폰트
}

def get_font_path_by_mood(mood_key: str) -> str:
    """선택된 무드에 맞춰 지정된 폰트 파일의 절대 경로를 반환합니다."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fonts_dir = os.path.join(base_dir, "assets", "fonts")
    
    # 매핑된 폰트가 없으면 기본 폰트 사용 (폴백)
    font_filename = MOOD_FONT_MAPPING.get(mood_key, "NotoSansKR-Bold.ttf")
    
    return os.path.join(fonts_dir, font_filename)

def wrap_text(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> str:
    """텍스트가 최대 너비를 넘지 않도록 띄어쓰기 기준으로 자동 줄바꿈합니다."""
    lines = []
    for paragraph in text.split('\n'):
        words = paragraph.split(' ')
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word]) if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # 단어 하나가 최대 너비를 넘는 경우
                    lines.append(word)
                    current_line = []
        if current_line:
            lines.append(' '.join(current_line))
    return '\n'.join(lines)

def add_text_to_image(
    image_path: str,
    text: str,
    output_path: str,
    font_path: str = None,
    font_size: int = None,                # None으로 설정 시 이미지 크기에 비례해 자동 조절
    text_color: tuple = (255, 255, 255),  # 흰색 글씨
    stroke_color: tuple = (0, 0, 0),      # 검은색 테두리
    stroke_width: int = 3,
    padding_ratio: float = 0.1,           # 양옆 및 상하 여백 비율 (기본 10%)
    position: str = "center",             # 텍스트 위치 ("top", "center", "bottom")
    draw_bg_box: bool = True,             # 반투명 배경 박스 그리기 활성화 (기본값 True)
    bg_box_color: tuple = (0, 0, 0, 150), # 반투명 검은색 (R, G, B, Alpha: 투명도 0~255)
    bg_box_padding: int = 30              # 텍스트와 배경 박스 사이의 여백 (픽셀)
) -> str:
    """
    생성된 이미지 중앙에 텍스트(광고 문구 등)를 합성합니다.
    """
    # 1. 이미지 열기
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"이미지를 찾을 수 없습니다: {image_path}")
        
    img = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    img_w, img_h = img.size
    # 폰트 크기 자동 계산 (지정되지 않았을 경우 이미지 너비의 약 4.5%)
    if font_size is None or font_size <= 0:
        font_size = max(int(img_w * 0.045), 16)
    
    # 2. 폰트 로드 (시스템 기본 폰트 또는 프로젝트 내 폰트 파일)
    try:
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
        else:
            print(f"⚠️ 경고: 지정한 폰트 경로를 찾을 수 없습니다! -> {font_path}")
            # 한글이 깨지지 않도록 윈도우 기본 폰트(맑은 고딕) 우선 폴백 시도
            try:
                font = ImageFont.truetype("malgun.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
    except Exception as e:
        print(f"⚠️ 폰트 로드 오류 발생: {e}")
        try:
            font = ImageFont.truetype("malgun.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

    max_text_width = img_w * (1 - padding_ratio * 2)
    
    # 3. 텍스트 자동 줄바꿈 처리
    wrapped_text = wrap_text(text, font, max_text_width, draw)

    # 4. 각 줄의 크기를 계산하여 전체 텍스트 영역(박스 크기) 구하기
    lines = wrapped_text.split('\n')
    line_spacing = int(font_size * 0.4)  # 줄 간격 (폰트 크기의 40%)
    
    line_widths = []
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        # 이모지가 포함될 경우를 대비해 폰트 사이즈보다 약간 여유 있는 높이 지정
        h = max(bbox[3] - bbox[1], int(font_size * 1.1))
        line_widths.append(w)
        line_heights.append(h)
        
    text_width = max(line_widths) if line_widths else 0
    text_height = sum(line_heights) + line_spacing * (len(lines) - 1) if lines else 0

    # X 좌표는 항상 가운데 정렬 (가장 긴 줄 기준)
    x = (img_w - text_width) / 2
    
    # Y 좌표는 position 파라미터에 따라 다르게 계산
    if position == "top":
        y = img_h * padding_ratio
    elif position == "bottom":
        y = img_h * (1 - padding_ratio) - text_height
    else:  # 기본값은 중앙(center)
        y = (img_h - text_height) / 2

    # 5. 반투명 배경 박스 그리기 (옵션)
    if draw_bg_box:
        # 원본과 동일한 크기의 100% 투명한 빈 캔버스(레이어) 생성
        overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # 텍스트 영역을 감싸는 박스의 [좌상단 X, 좌상단 Y, 우하단 X, 우하단 Y] 좌표 계산
        box_x0 = x - bg_box_padding
        box_y0 = y - bg_box_padding
        box_x1 = x + text_width + bg_box_padding
        box_y1 = y + text_height + bg_box_padding
        
        # 모서리가 둥근 반투명 박스 그리기
        overlay_draw.rounded_rectangle([box_x0, box_y0, box_x1, box_y1], radius=15, fill=bg_box_color)
        
        # 투명 레이어를 원본 이미지 위에 합성(Alpha 채널 유지)
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)  # 텍스트를 합성된 이미지 위에 그리기 위해 draw 객체 재할당

    # 6. 텍스트 그리기 (한 줄씩 렌더링하여 이모지 깨짐 및 위치 틀어짐 방지)
    current_y = y
    
    if HAS_PILMOJI:
        # 트위터 이모지 소스 명시 및 크기/위치 미세 조정
        with Pilmoji(img, source=TwitterEmojiSource, emoji_scale_factor=1.2, emoji_position_offset=(0, 6)) as pilmoji:
            for i, line in enumerate(lines):
                line_x = x + (text_width - line_widths[i]) / 2  # 각 줄별 X축 가운데 정렬
                pilmoji.text(
                    (line_x, current_y),
                    line,
                    font=font,
                    fill=text_color,
                    stroke_width=stroke_width,
                    stroke_fill=stroke_color
                )
                current_y += line_heights[i] + line_spacing
    else:
        for i, line in enumerate(lines):
            line_x = x + (text_width - line_widths[i]) / 2
            draw.text(
                (line_x, current_y),
                line,
                font=font,
                fill=text_color,
                stroke_width=stroke_width,
                stroke_fill=stroke_color
            )
            current_y += line_heights[i] + line_spacing
    
    # 7. 최종 이미지 저장 (알파 채널 제거)
    final_img = img.convert("RGB")
    final_img.save(output_path)
    
    return output_path

# --- 독립 테스트 영역 (웹 서버 없이 파일만 단독 실행 시 작동) ---
if __name__ == "__main__":
    # 1. 준비된 원본 이미지 경로 설정 (직접 넣은 test_sample_bg.png 사용)
    test_input_path = "test_sample_bg.png"
    test_output_path = "test_sample_result.png"
    
    print("🎨 1. 준비된 테스트용 배경 이미지 불러오는 중...")
    
    print("✍️ 2. 텍스트 오버레이 합성 중...")
    test_mood = "트렌디한 메뉴 홍보"
    test_font_path = get_font_path_by_mood(test_mood)
    test_text = "부드러운 생크림이 가득한\n딸기 조각 케이크 🍰\n지금 바로 매장에서 만나보세요!\n(텍스트 자동 줄바꿈 테스트 중입니다. 문구가 길어도 박스 안에 잘 들어가는지 확인합니다.)"
    
    if not HAS_PILMOJI:
        print("\n" + "="*55)
        print("🚨 [에러] 이모지 라이브러리가 현재 환경에 없습니다!")
        print("👉 터미널에서 다음 명령어로 꼭 설치/업데이트 해주세요:")
        print("   pip install --upgrade pilmoji emoji requests")
        print("="*55 + "\n")

    try:
        result_file = add_text_to_image(
            image_path=test_input_path,
            text=test_text,
            output_path=test_output_path,
            font_path=test_font_path,
            font_size=None,  # None으로 두면 자동 크기 조절 (원하는 고정 크기가 있다면 숫자로 입력)
            position="bottom",
            draw_bg_box=True
        )
        print(f"✅ 테스트 성공! 결과 확인: {result_file}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
