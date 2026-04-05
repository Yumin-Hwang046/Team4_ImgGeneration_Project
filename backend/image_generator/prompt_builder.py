# backend/image_generator/prompt_builder.py

import os
from openai import OpenAI
from dotenv import load_dotenv

# 환경 변수 로드 및 서버 클라이언트 준비
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def build_dalle_prompt(image_analysis_text: str, mood_key: str) -> str:
    """
    한글로 된 '사진 분석 텍스트'와 '무드'를 입력받아,
    DALL-E 3가 가장 잘 이해할 수 있는 최적화된 영문 프롬프트(지시문)로 변환해 줍니다.
    """
    
    # 1. GPT에게 변환 규칙 명령 (시스템 프롬프트)
    # 불필요한 대화형 텍스트 없이 오직 영문 프롬프트만 출력하도록 규칙을 엄격하게 적용합니다.
    system_instruction = """
    You are an expert AI image generation prompt engineer.
    Your job is to translate the [User's Request] into a highly detailed English prompt for DALL-E 3.
    Always follow this structure: 
    [Main Subject] in [Setting/Lighting], [Mood/Style], highly detailed, 4k resolution, instagram photography style.
    Do not output any conversational text, ONLY output the final English prompt.
    """
    
    # 2. 한글로 된 원본 데이터 세팅
    user_message = f"""
    [User's Request]
    - 사진 분석 정보: {image_analysis_text}
    - 원하는 이미지 분위기: {mood_key}
    """
    
    # 3. GPT-5-mini 모델을 이용해 '영문 프롬프트'로 똑똑하게 번역/가공
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message}
            ]
        )
        # 번역 및 최적화된 영문 프롬프트 문자열만 추출 (안정성을 위해 temperature 옵션은 사용하지 않음)
        english_prompt = response.choices[0].message.content.strip()
        return english_prompt
        
    except Exception as e:
        print(f"프롬프트 변환 중 에러 발생: {e}")
        # 예기치 않은 오류 시 후속 파이프라인(DALL-E)의 작동 중단을 방지하기 위해 대체용 기본 프롬퍼트를 반환합니다.
        return "A high quality instagram photography of a product, beautiful lighting."
