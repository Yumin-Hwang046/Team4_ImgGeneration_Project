import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# 방금 만든 프롬프트 템플릿 불러오기
from text_generator.prompt_templates import get_full_prompt

# 환경 변수 로드 및 클라이언트 생성
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_ad_copy(image_analysis_text: str, mood_key: str) -> dict:
    """
    Step 1에서 추출한 '사진 요약 텍스트'와 사용자가 선택한 '분위기(무드)'를 바탕으로
    gpt-5-mini 모델을 호출하여 인스타그램 광고 문구를 생성합니다.
    """
    
    # 1. 템플릿 조립: 선택한 무드에 맞는 '통제 가이드라인' 불러오기
    system_prompt = get_full_prompt(mood_key)
    
    # 2. 사용자 데이터 전달: AI에게 분석된 팩트 텍스트 전달하기
    user_message = f"""
[사진 분석 데이터]
{image_analysis_text}

위 사진 분석 데이터를 바탕으로 조건에 맞게 광고 문구를 작성해 줘.
    """
    
    try:
        # 3. 모델 통신 (gpt-5-mini 모델 지정)
        response = client.chat.completions.create(
            model="gpt-5-mini", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            # 핵심! AI가 대답을 JSON 포맷으로 반환하도록 API 차원에서 규칙 강제
            response_format={"type": "json_object"}
        )
        
        # 4. 텍스트로 날아온 JSON 응답을 파이썬 딕셔너리로 추출(파싱)
        result_text = response.choices[0].message.content
        result_json = json.loads(result_text)
        
        return result_json

    except Exception as e:
        print(f"문구 생성 중 에러 발생: {e}")
        # 예기치 않은 오류 발생 시, 프론트엔드 연동 중단을 방지하기 위해 빈 딕셔너리 반환
        return {"copy": "앗, 문구 생성에 실패했어요.", "hashtags": []}


# --- 독립 테스트 영역 (웹 서버 없이 파일만 단독 실행 시 작동) ---
if __name__ == "__main__":
    # 가짜 수신 데이터 생성 (Step 1에서 이런 텍스트가 넘어왔다고 가정)
    test_analysis = "하얀색 접시 위에 놓인 부드러운 초코 롤케이크입니다. 겉면은 진한 초콜릿으로 코팅되어 있고, 따뜻한 카페 조명을 받아 먹음직스러워 보입니다."
    test_mood = "트렌디한 메뉴 홍보"
    
    print(f"[{test_mood}] 무드로 광고 카피를 뽑아내고 있습니다...\n")
    
    # 메인 함수 실행
    result = generate_ad_copy(test_analysis, test_mood)
    
    # 결과 출력
    print("✅ [광고 카피 본문]")
    print(result.get("copy", ""))
    print("-" * 30)
    print("✅ [해시태그]")
    print(" ".join(result.get("hashtags", [])))
