# 🎯 LocalAd AI · Team 4

> 생성형 AI로 지역 맛집·로컬 카페 소상공인을 위한 **네이버 · 인스타그램 광고 콘텐츠를 자동 생성**하는 플랫폼

<br>

---

## 1. 📌 프로젝트 개요

**핵심 아이디어**
소상공인이 매장 사진 한 장만 올려도 AI가 광고 문구와 이미지를 자동 생성해주는 플랫폼.
별도의 디자이너·마케터 없이도 SNS·포털 광고에 바로 쓸 수 있는 결과물을 제공합니다.

### 배경
- 지역 소상공인은 마케팅 예산과 전문 인력이 부족합니다.
- 생성형 AI 기술은 발전했지만 소상공인이 직접 활용하기엔 진입 장벽이 높습니다.
- 네이버·인스타그램 광고는 규격(사이즈·무드)이 정해져 있어 맞춤 자동화가 가능합니다.

### 목표
| 기능 | 설명 |
|------|------|
| ✍️ 문구 생성 | 매장/메뉴 사진을 분석해 광고 카피를 자동 작성 |
| 🎨 이미지 생성 | 텍스트 프롬프트 또는 참고 이미지로 광고 이미지 생성 |
| 📐 규격 맞춤 | 인스타 피드/스토리, 웹 배너 등 광고 규격별 결과 제공 |

### 기대 효과
- AI 자동화로 광고 제작 비용·시간 대폭 절감
- 사진 한 장으로 SNS 광고 즉시 제작 → 소상공인 디지털 마케팅 진입 장벽 해소
- 반복 사용으로 브랜드 이미지 일관성 유지

### 🛠️ 기술 스택

**언어**
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=flat&logo=jupyter&logoColor=white)

**프레임워크**
![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat&logo=next.js&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat&logo=mysql&logoColor=white)

**라이브러리**
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat&logo=pytorch&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat&logo=openai&logoColor=white)
![HuggingFace](https://img.shields.io/badge/HuggingFace-FFD21E?style=flat&logo=huggingface&logoColor=black)

**도구**
![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat&logo=github&logoColor=white)
![Notion](https://img.shields.io/badge/Notion-000000?style=flat&logo=notion&logoColor=white)
![Discord](https://img.shields.io/badge/Discord-5865F2?style=flat&logo=discord&logoColor=white)

<br>

---

## 2. ⚙️ 설치 및 실행 방법

> **사전 요구사항:** Node.js 18+, Python 3.10+, MySQL 8.0+, [uv](https://github.com/astral-sh/uv) 패키지 매니저

---

### Step 1. 저장소 클론

```bash
git clone https://github.com/your-org/Team4_ImgGeneration_Project1.git
cd Team4_ImgGeneration_Project1
```

---

### Step 2. MySQL 데이터베이스 준비

```sql
CREATE DATABASE team4_project CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

### Step 3. 환경 변수 설정

#### 3-1. 백엔드 — `backend/.env`

```env
# ── 데이터베이스 ──────────────────────────────────────────
DATABASE_URL=mysql+pymysql://root:1234@127.0.0.1:3306/team4_project

# ── OpenAI ───────────────────────────────────────────────
OPENAI_API_KEY=sk-...
TEXT_MODEL_NAME=gpt-4o-mini

# ── GCP 텍스트 생성 서버 (팀 내부 서버 URL) ────────────────
TEXT_GENERATOR_URL=https://your-gcp-server/generate

# ── Meta (Instagram OAuth) ───────────────────────────────
META_APP_ID=your_meta_app_id
META_APP_SECRET=your_meta_app_secret
META_REDIRECT_URI=https://xxxx.ngrok-free.app/api/auth/callback/instagram

```

#### 3-2. 프론트엔드 — `frontend/.env.local`

```env
# ── 백엔드 API 주소 ───────────────────────────────────────
BACKEND_URL=http://localhost:8000

# ── 프론트엔드 공개 URL (OAuth 콜백용, ngrok 사용 시 교체) ─
NEXT_PUBLIC_APP_URL=http://localhost:3000

# ── Meta (Instagram OAuth, 백엔드와 동일 값) ─────────────
NEXT_PUBLIC_META_APP_ID=your_meta_app_id
NEXT_PUBLIC_META_REDIRECT_URI=https://xxxx.ngrok-free.app/api/auth/callback/instagram

# ── OpenAI (AI 캘린더 팁, 상권 분석) ─────────────────────
OPENAI_API_KEY=sk-...

# ── 카카오 REST API (주소 검색) ───────────────────────────
KAKAO_REST_API_KEY=your_kakao_rest_api_key

# ── 공공데이터 (축제·행사) ────────────────────────────────
FESTIVAL_API_KEY=your_festival_api_key

# ── 상권 분석 API ─────────────────────────────────────────
SANGKWON_API_KEY=your_sangkwon_api_key
SEOUL_API_KEY=your_seoul_api_key
```

---

### Step 4. 백엔드 실행

```bash
cd backend

# 가상환경 생성 및 활성화
uv venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 패키지 설치
uv pip install -r requirements.txt

# NVIDIA GPU 환경이라면 CUDA 버전 torch 설치 (선택)
# uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# DB 테이블 생성 (최초 1회)
python -c "from db import Base, engine; from models import *; Base.metadata.create_all(engine)"

# 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

백엔드가 정상 실행되면 → `http://localhost:8000/docs` 에서 Swagger UI 확인 가능

---

### Step 5. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 → `http://localhost:3000` 접속

---

### Step 6. ngrok — Instagram OAuth 로컬 연동

Instagram OAuth 콜백은 `https://` 주소만 허용합니다. 로컬에서 OAuth를 테스트하려면 ngrok으로 터널을 열어야 합니다.

#### 6-1. ngrok 설치

```bash
# macOS
brew install ngrok

# Windows (winget)
winget install ngrok.ngrok

# 또는 https://ngrok.com/download 에서 직접 다운로드
```

#### 6-2. 계정 인증 (최초 1회)

[ngrok 대시보드](https://dashboard.ngrok.com)에서 authtoken 복사 후:

```bash
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
```

#### 6-3. 터널 실행

프론트엔드(3000)만 터널을 열면 됩니다. Next.js가 `/api/[...path]`를 통해 백엔드로 내부 프록시하기 때문입니다.

```bash
# ngrok 폴더에서 실행 (또는 PATH에 등록된 경우 어디서든)
ngrok.exe http 3000 
```

실행 후 출력되는 `Forwarding` 주소(예: `https://abcd-1234.ngrok-free.app`)를 확인합니다.

#### 6-4. 환경 변수 업데이트

ngrok 주소로 `.env` 파일들을 업데이트합니다.

**`backend/.env`**
```env
META_REDIRECT_URI=https://<ngrok-주소>/api/auth/callback/instagram
```

**`frontend/.env.local`**
```env
NEXT_PUBLIC_APP_URL=https://<ngrok-주소>
NEXT_PUBLIC_META_REDIRECT_URI=https://<ngrok-주소>/api/auth/callback/instagram
```

#### 6-5. Meta 앱 설정

[Meta for Developers](https://developers.facebook.com) → 앱 선택 → **Instagram Basic Display** 또는 **Instagram API** → **Valid OAuth Redirect URIs** 에 아래 주소 추가:

```
https://<ngrok-주소>/api/auth/callback/instagram
```

> ngrok 무료 플랜은 재시작할 때마다 주소가 바뀝니다. 주소가 바뀌면 `.env` 파일과 Meta 앱 설정을 함께 업데이트해야 합니다.

---

### 전체 실행 순서 요약

| 순서 | 작업 |
|------|------|
| 1 | MySQL 서버 실행 후 `team4_project` DB 생성 |
| 2 | `backend/.env` 작성 |
| 3 | `frontend/.env.local` 작성 |
| 4 | 백엔드 가상환경 활성화 후 `uvicorn` 실행 |
| 5 | 프론트엔드 `npm run dev` 실행 |
| 6 | Instagram 연동이 필요하면 ngrok 터널 2개 실행 후 주소 업데이트 |


<br>

---

## 3. 📂 프로젝트 구조

```
Team4_ImgGeneration_Project/
├── frontend/                 # Next.js 앱
│   ├── app/                  # App Router 페이지
│   ├── components/           # 공통 컴포넌트
│   └── public/               # 정적 파일
├── backend/                  # 백엔드 (기술 스택 미확정)
│   ├── image_analyzer/       # 업로드 이미지 분석
│   ├── text_generator/       # 광고 문구 생성
│   ├── image_generator/      # 광고 이미지 생성
│   └── main.py               # 백엔드 진입점
├── .env.example
├── requirements.txt
└── README.md
```

<br>

---

## 4. 🗺️ User Flow

> **💡 핵심 요약:** 홈에서 기능을 선택한 후, **문구 생성** 또는 **이미지 생성** 마법사를 통해 단계별로 광고 콘텐츠를 완성합니다.

**서비스 진입:** 홈 화면 → 기능 선택 (✍️ 문구 생성 / 🎨 이미지 생성)

<details>
<summary>✍️ 문구 생성 마법사 (Image → Text)</summary>

| 단계 | 내용 |
|------|------|
| 1 | 광고 사이즈 선택 (인스타 피드 / 인스타 스토리 / 웹 배너) |
| 2 | 무드 선택 (따뜻한 매장 분위기 / 깔끔한 상품 홍보 등) |
| 3 | 이미지 업로드 ⭐️ **필수** — AI가 분석할 매장/메뉴 사진 |
| 4 | 추가 정보 입력 (메뉴명, 가격, 이벤트 등) |
| 5 | 광고 문구 생성 완료 → 결과 확인 및 복사 |

</details>

<details>
<summary>🎨 이미지 생성 마법사 (Text/Image → Image)</summary>

| 단계 | 내용 |
|------|------|
| 1 | 광고 사이즈 선택 (인스타 피드 / 인스타 스토리 / 웹 배너) |
| 2 | 무드 선택 (따뜻한 매장 분위기 / 깔끔한 상품 홍보 등) |
| 3 | 레퍼런스 선택 ▫️ 선택사항 — 스타일 참고 이미지 선택 또는 직접 입력 |
| 4 | 내 이미지 업로드 ▫️ 선택사항 — 합성/형태 참고용 사진 업로드 |
| 5 | 프롬프트 입력 — 원하는 결과물을 글로 묘사 |
| 6 | 광고 이미지 생성 완료 → 결과 확인 및 다운로드 |

</details>

<br>

---

## 5. 👥 팀 소개: Team 4

| 이름 | 역할 |
|------|------|
| 황유민 | PM / 모델 |
| 김슬기 | 모델 |
| 문진우 | 모델 |
| 김민주 | 모델 |

<br>

---

## 6. 📊 타임라인

| 날짜 | 단계 | 주요 내용 | 담당자 | 상태 |
|------|------|-----------|--------|------|
| 2026-03-30 | 기획 | 프로젝트 시작 및 팀 구성 | 전원 | ✅ 완료 |
| 2026-03-31 | 기획 | 요구사항 정의 · User Flow 설계 · 기술 스택 확정 및 GitHub 세팅 | 전원 | ✅ 완료 |
| 2026-04-01 | 모델 | 이미지 분석 모델 선정 및 API 연동 테스트 | TBD | 🔄 진행 중 |
| 2026-04-02 | 모델 | 문구 생성 프롬프트 설계 및 출력 품질 실험 | TBD | ⏳ 예정 |
| 2026-04-03 | 모델 | 이미지 생성 모델 선정 및 테스트 | TBD | ⏳ 예정 |
| 2026-04-04 | 모델 | 이미지 생성 프롬프트 설계 및 사이즈별 출력 실험 | TBD | ⏳ 예정 |
| 2026-04-05 | 모델 | 문구/이미지 생성 파이프라인 초기 버전 완성 | TBD | ⏳ 예정 |
| 2026-04-06 | 서빙 | 백엔드 서버 구현 및 라우터 설계 | TBD | ⏳ 예정 |
| 2026-04-07 | 서빙 | Next.js UI 프로토타입 구현 | TBD | ⏳ 예정 |
| 2026-04-08 | 서빙 | 프론트-백엔드 연동 및 통합 테스트 | 전원 | ⏳ 예정 |
| 2026-04-09 | 서비스 | UI 고도화 및 사용성 개선 | TBD | ⏳ 예정 |
| 2026-04-10 | 서비스 | 최종 기능 테스트 및 버그 수정 | 전원 | ⏳ 예정 |
| 2026-04-12 | 서비스 | 최종 보고서 및 README 정리 + 발표자료 제작 | 전원 | ⏳ 예정 |

<br>

---

## 7. 📎 참고 자료 및 산출물

- 📘 최종 보고서: [다운로드](#)
- 📽️ 발표자료 (PPT): [확인하기](#)

<br>

---

## 8. 📄 사용한 모델 및 라이선스

> 모델 확정 후 업데이트 예정

| 모델 | 라이선스 |
|------|----------|
| TBD | TBD |
