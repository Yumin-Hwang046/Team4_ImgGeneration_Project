## 📌 프로젝트 개요

소상공인을 위한 AI 기반 인스타그램 콘텐츠 생성 서비스입니다.

사용자가 업종, 메뉴, 위치, 날짜 등을 입력하면  
날씨 및 시기 데이터를 반영하여:

- 광고 문구 생성
- 이미지 생성
- 해시태그 추천

을 자동으로 수행하고, 결과를 보관 및 조회할 수 있습니다.

## 🧠 핵심 기능

### 1. 인증 시스템
- 회원가입 / 로그인
- JWT 기반 인증

### 2. 콘텐츠 생성 (핵심)
- POST /generations/run
- 입력값 기반 자동 생성

동작 흐름:
1. 사용자 입력 수집
2. 날씨 API 조회
3. 시즌 분석
4. 추천 컨셉 생성
5. 이미지 처리 (업로드 or 생성)
6. 문구 생성
7. DB 저장

### 3. 비동기 처리
- BackgroundTasks 사용
- 요청 즉시 응답 (PENDING)
- 처리 완료 후 SUCCESS 상태로 변경

### 4. 보관함 기능
- 생성 결과 저장
- 목록 조회 (GET /generations)
- 상세 조회 (GET /generations/{id})

## ⚙️ 주요 API

### 인증
- POST /auth/signup
- POST /auth/login
- GET /auth/me

### 생성
- POST /generations/run

### 조회
- GET /generations          (보관함 목록)
- GET /generations/{id}     (상세 조회)

### 수정
- PUT /generations/{id}

## 🗄️ DB 구조

### users
사용자 정보

### user_profiles
매장 정보 (업종, 위치 등)

### generations
콘텐츠 생성 결과

주요 컬럼:
- purpose
- business_category
- menu_name
- location
- target_datetime
- weather_summary
- recommended_concept
- generated_copy
- hashtags
- generated_image_url
- generation_status (PENDING / SUCCESS / FAILED)

## 🔄 처리 흐름

POST /generations/run 요청

→ DB에 PENDING 상태 저장  
→ Background Task 실행  

[비동기 처리]
→ 날씨 조회
→ 컨셉 생성
→ 이미지 처리
→ 문구 생성

→ DB 업데이트 (SUCCESS)

→ 사용자는 조회 API로 결과 확인

## 📊 현재 진행 상태

- 인증 시스템: 완료
- DB 설계: 완료
- CRUD API: 완료
- 통합 실행 API: 완료
- 비동기 처리: 완료
- 보관함 API: 완료

👉 백엔드 약 80% 완료

## 🚧 향후 계획

- generated_images 테이블 (이미지 여러 버전)
- 실제 AI 모델 연동
- 인스타그램 API 연동 (자동 업로드)
- 캘린더 기반 업로드 예약 기능

## ⚙️ 실행 방법

### 1. 프로젝트 클론

```bash
git clone https://github.com/Yumin-Hwang046/Team4_ImgGeneration_Project.git
cd Team4_ImgGeneration_Project

### 2. 가상환경 생성 및 활성화

python3 -m venv .venv
source .venv/bin/activate

### 3. 패키지 설치

pip install -r requirements.txt

### 4. MySQL 실행 및 DB 설정

CREATE DATABASE team4_project;

### 5. 환경 설정 (.env)

DB_HOST=localhost
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=team4_project
SECRET_KEY=your_secret_key

### 6. 서버 실행

cd backend
uvicorn main:app --reload


### 7. API 테스트

Swagger 접속: http://localhost:8000/docs

---

# 💡 추가하면 좋은 것 (플러스 점수)

```md
## 🧪 테스트 방법

1. 회원가입
2. 로그인
3. Authorize (토큰 입력)
4. POST /generations/run 실행
5. GET /generations 확인

