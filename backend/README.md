# 📦 Backend - 기능 명세

## 1. 문구 만들기

| 항목 | 내용 |
|------|------|
| **입력** | 상품 이미지 (필수) · 문구 요청 사항 (무드 선택) |
| **출력** | 광고 문구, 해시태그 (텍스트) |
| **출력 옵션** | 따뜻한 매장 분위기 / 깔끔한 상품 홍보 / 트렌디한 메뉴 홍보 / 프리미엄 매장·상품 |

---

## 2. 이미지 만들기

### Case 1 — 텍스트 입력만

| 항목 | 내용 |
|------|------|
| **입력** | 광고 문구 · 요청 사항 · 무드 선택 |
| **출력** | 텍스트와 무드가 반영된 100% 생성 이미지 |
| **비율 선택** | 인스타 스토리 / 인스타 피드 / 웹 광고 배너 |
| **무드 제어** | 따뜻한 매장 분위기 / 깔끔한 상품 홍보 / 트렌디한 메뉴 홍보 / 프리미엄 매장·상품 |

### Case 2 — 레퍼런스 이미지 사용

| 항목 | 내용 |
|------|------|
| **입력** | 레퍼런스 이미지 · 광고 문구 · 요청 사항 · 무드 선택 |
| **출력** | 레퍼런스의 색감과 구도를 모방한 이미지 |
| **비율 선택** | 인스타 스토리 / 인스타 피드 / 웹 광고 배너 |
| **스타일 제어** | IP-Adapter 가중치 조절 (레퍼런스 색감 우선 ↔ 무드 프리셋 혼합 비율) |

### Case 3 — 입력 이미지 보존

| 항목 | 내용 |
|------|------|
| **입력** | 실제 제품 사진 · 광고 문구 · 요청 사항 · 무드 선택 |
| **출력** | 원본 형태 유지 + 배경·조명이 합성된 광고 이미지 |
| **비율 선택** | 인스타 스토리 / 인스타 피드 / 웹 광고 배너 |
| **배경/조명 제어** | ControlNet — 따뜻한 분위기 / 깔끔한 홍보 / 트렌디 / 프리미엄 |

사용자가 업종, 메뉴, 위치, 날짜 등을 입력하면
날씨 및 시기 데이터를 반영하여:

* 광고 문구 생성
* 이미지 생성
* 해시태그 추천

을 자동으로 수행하고, 결과를 저장 및 관리할 수 있습니다.

또한 캘린더 기반으로 **업로드 일정 관리 및 마케팅 전략 추천**까지 지원합니다.

---

# 🧠 핵심 기능

## 1. 인증 시스템

* 회원가입 / 로그인
* JWT 기반 인증

---

## 2. 콘텐츠 생성 (핵심 기능)

### API

`POST /generations/run`

### 동작 흐름

1. 사용자 입력 수집
2. 날씨 데이터 조회
3. 시즌 분석
4. 추천 콘셉트 생성
5. 이미지 생성 또는 업로드 처리
6. 광고 문구 및 해시태그 생성
7. DB 저장

---

## 3. 비동기 처리

* FastAPI BackgroundTasks 사용
* 요청 즉시 응답 (PENDING 상태)
* 작업 완료 후 SUCCESS 상태로 업데이트

---

## 4. 보관함 기능

* 생성 결과 저장
* 목록 조회: `GET /generations`
* 상세 조회: `GET /generations/{id}`

---

## 5. 이미지 버전 관리

* `generated_images` 테이블 사용
* 이미지 재생성 가능
* 버전별 관리 지원

---

## 6. 캘린더 기능 (마케팅 핵심)

### 📅 월간 조회

`GET /calendar/month`

* 날짜별:

  * 날씨
  * 행사 여부
  * 콘텐츠 생성 여부
  * 예약 여부

---

### 📅 일간 상세 조회

`GET /calendar/day`

조회 시 제공 정보:

* 날씨 정보 (실제 + fallback)
* 행사/축제 정보
* 생성된 콘텐츠 목록
* 예약된 업로드 일정
* 추천 마케팅 전략

---

### 🧠 추천 기능

다음 데이터를 기반으로 자동 생성:

* 날씨
* 행사
* 시즌

👉 결과:

* 추천 업로드 시간
* 추천 채널 (피드 / 스토리)
* 추천 목적
* 추천 콘텐츠 콘셉트

---

## 7. 행사/축제 관리

* 조회: `GET /calendar/events`
* 등록: `POST /calendar/events`
* 삭제: `DELETE /calendar/events/{id}`

---

## 8. 업로드 예약 시스템

* 생성: `POST /calendar/schedules`
* 조회: `GET /calendar/schedules`
* 삭제: `DELETE /calendar/schedules/{id}`

---

## 9. 인스타그램 업로드 (Mock 구현)

### API

* 즉시 업로드
  `POST /instagram/upload`

* 예약 업로드
  `POST /instagram/schedule-upload`

* 상태 조회
  `GET /instagram/status/{schedule_id}`

---

### ⚠️ 현재 상태

* 실제 업로드 ❌
* Mock 기반 구조만 구현

---

# 🗄️ DB 구조

## users

사용자 정보

## user_profiles

매장 정보 (업종, 위치 등)

## generations

콘텐츠 생성 결과

주요 컬럼:

* purpose
* business_category
* menu_name
* location
* target_datetime
* weather_summary
* recommended_concept
* generated_copy
* hashtags
* generated_image_url
* generation_status

---

## generated_images

이미지 버전 관리

---

## calendar_events

행사/축제 데이터

---

## upload_schedules

업로드 예약 관리

---

# 🔄 전체 처리 흐름

```text
사용자 입력
→ POST /generations/run

→ DB 저장 (PENDING)

→ Background Task 실행
   → 날씨 조회
   → 컨셉 생성
   → 이미지 생성
   → 문구 생성

→ DB 업데이트 (SUCCESS)

→ 보관함 조회
→ 캘린더 반영
→ 업로드 예약
→ 인스타 업로드 (mock)
```

---

# 🤖 AI 연동 구조

## 위치

`ai_clients.py`

---

## 🔧 연동 방법

다음 함수만 교체하면 전체 시스템에 반영됩니다:

* `call_image_generator()`
* `call_text_generator()`

---

## 📥 이미지 반환 형식

```json
{
  "success": true,
  "image_url": "...",
  "prompt_used": "...",
  "error": null
}
```

---

## 📝 텍스트 반환 형식

```json
{
  "success": true,
  "copy": "...",
  "hashtags": ["#..."],
  "error": null
}
```

---

# 📸 인스타그램 연동 방법

## 필요 조건

* Instagram Business 또는 Creator 계정
* Facebook Page 연결
* Meta Graph API Access Token

---

## 🔧 연동 위치

`instagram_router.py`

---

## 교체 방법

* mock 응답 제거
* Meta Graph API 호출 추가

---

# ⚙️ 실행 방법

## 1. 프로젝트 클론

```bash
git clone https://github.com/Yumin-Hwang046/Team4_ImgGeneration_Project.git
cd Team4_ImgGeneration_Project
```

---

## 2. 가상환경

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. 패키지 설치

```bash
pip install -r requirements.txt
```

---

## 4. DB 생성

```sql
CREATE DATABASE team4_project;
```

---

## 5. 환경 설정 (.env)

```env
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/team4_project
SECRET_KEY=your_secret_key
```

---

## 6. 서버 실행

```bash
cd backend
uvicorn main:app --reload
```

---

## 7. API 테스트

Swagger 접속:

```
http://localhost:8000/docs
```

---

# 📊 현재 상태

| 항목        | 상태          |
| --------- | ----------- |
| 인증 시스템    | ✅ 완료        |
| 콘텐츠 생성    | ✅ 완료        |
| 비동기 처리    | ✅ 완료        |
| 보관함       | ✅ 완료        |
| 이미지 버전 관리 | ✅ 완료        |
| 캘린더       | ✅ 완료        |
| 예약 시스템    | ✅ 완료        |
| 인스타 구조    | ✅ 완료 (mock) |
| AI 연동     | ✅ 인터페이스 완료  |

---

# 🚧 외부 연동 대기

* 실제 AI 모델 연결
* 인스타그램 실제 업로드 API 연결

---

# 🧩 설계 특징

* 외부 API 완전 분리 구조
* mock 기반 테스트 가능
* 최소 수정으로 실연동 가능
* 확장성 고려 설계

---

# 🚀 최종 결론

👉 **외부 API만 연결하면 바로 서비스 가능한 상태**

---

