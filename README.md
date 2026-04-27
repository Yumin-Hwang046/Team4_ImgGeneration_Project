# 🎯 The-Digital-Curator · Team 4

> 생성형 AI로 지역 맛집·로컬 카페 소상공인을 위한 **인스타그램 광고 콘텐츠를 자동 생성, 업로드**하는 플랫폼

[The digital curator](team4-img-generation-projec-git-2bcd28-yumin-hwang046s-projects.vercel.app)

<br>

---

## 1. 📌 프로젝트 개요

**핵심 아이디어**
요식업계 소상공인을 위한 **인스타 마케팅 에이전트**.
음식 사진을 업로드하면 AI가 **인스타그램 마케팅용 이미지와 문구를 생성**하고, 설정에 따라 **인스타 자동 업로드까지** 이어주는 서비스입니다.

### 배경
- 요식업 소상공인은 매일 반복되는 홍보(신메뉴/이벤트/리뷰) 업무에 시간을 많이 씁니다.
- 인스타그램은 핵심 채널이지만, 콘텐츠 기획·카피 작성·이미지 제작·업로드까지의 작업이 번거롭습니다.
- 생성형 AI로 콘텐츠 제작은 쉬워졌지만, 현장에서는 “내 가게 톤/메뉴/분위기”에 맞춘 결과와 운영 자동화가 필요합니다.

### 목표
| 기능 | 설명 |
|------|------|
| ⚙️ 사용자 맞춤 설정 | 가게 무드/톤앤매너/광고 목적/포맷(피드·스토리) 등을 설정 |
| 🎨 이미지 생성 | 음식 사진 기반으로 인스타 마케팅용 이미지 생성(배경/무드/포맷 최적화) |
| ✍️ 문구 생성 | 이미지/설정 기반으로 인스타 캡션·해시태그·CTA 자동 생성 |
| 📤 인스타 업로드 | 생성 결과를 인스타그램에 자동 업로드(또는 예약 업로드) |

### 기대 효과
- 사진 1장으로 “이미지+문구+업로드”까지 연결 → 제작/운영 시간 절감
- 가게별 톤앤매너를 유지한 콘텐츠 자동 생성 → 브랜드 일관성 강화
- 반복 작업 자동화로 운영자는 매장 운영/서비스에 집중

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
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![ngrok](https://img.shields.io/badge/ngrok-1F1E37?style=flat&logo=ngrok&logoColor=white)

**배포**
![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat&logo=vercel&logoColor=white)

**관측/실험**
![Langfuse](https://img.shields.io/badge/Langfuse-111827?style=flat&logoColor=white)
![Weights%20%26%20Biases](https://img.shields.io/badge/Weights%20%26%20Biases-FFBE00?style=flat&logo=weightsandbiases&logoColor=black)

<br>

---

## 2. ⚙️ 설치 및 실행 방법

> **사전 요구사항:** Node.js 18+, Python 3.10+, MySQL 8.0+, [uv](https://github.com/astral-sh/uv) 패키지 매니저

---

### 전체 실행 순서 요약

| 순서 | 작업 |
|------|------|
| 1 | MySQL 서버 실행 후 `team4_project` DB 생성 |
| 2 | `backend/.env` 작성 |
| 3 | `frontend/.env.local` 작성 |
| 4 | 백엔드 가상환경 활성화 후 `uvicorn` 실행 |
| 5 | 프론트엔드 `npm run dev` 실행 |
| 6 | Instagram 연동이 필요하면 ngrok 터널 실행 후 주소 업데이트 |

<br>

<details>
<summary>Step 1. 저장소 클론</summary>

```bash
git clone https://github.com/Yumin-Hwang046/Team4_ImgGeneration_Project.git
cd Team4_ImgGeneration_Project1
```

</details>

<details>
<summary>Step 2. MySQL 데이터베이스 준비</summary>

```sql
CREATE DATABASE team4_project CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

</details>

<details>
<summary>Step 3. 환경 변수 설정</summary>

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

</details>

<details>
<summary>Step 4. 백엔드 실행</summary>

```bash
cd backend

# 가상환경 생성 및 활성화
uv venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 패키지 설치
# 기본 requirements.txt 는 Python 3.10에서 바로 설치되도록 일반 torch 버전을 사용합니다.
uv pip install -r requirements.txt

# NVIDIA GPU 환경이라면 PyTorch 전용 인덱스에서 CUDA 빌드로 다시 맞춥니다. (선택)
# `triton` 과 CUDA 런타임 패키지는 torch가 호환 버전으로 함께 가져오도록 별도 고정하지 않습니다.
# uv pip install torch==2.6.0+cu124 torchvision==0.21.0+cu124 torchaudio==2.6.0+cu124 --index-url https://download.pytorch.org/whl/cu124

# DB 테이블 생성 (최초 1회)
python -c "from db import Base, engine; from models import *; Base.metadata.create_all(engine)"

# 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

백엔드가 정상 실행되면 → `http://localhost:8000/docs` 에서 Swagger UI 확인 가능

</details>

<details>
<summary>Step 5. 프론트엔드 실행</summary>

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 → `http://localhost:3000` 접속

</details>

<details>
<summary>Step 6. ngrok — Instagram OAuth 로컬 연동</summary>

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

기본은 프론트엔드(3000)만 터널을 엽니다. (프론트에서 백엔드로 프록시/호출하는 구조일 때)
환경/구성에 따라 백엔드(8000) 터널이 추가로 필요할 수 있습니다.

```bash
ngrok http 3000
# 필요 시:
# ngrok http 8000
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

</details>

---

## 3. 📂 프로젝트 구조

```
Team4_ImgGeneration_Project1/
├── frontend/                         # Next.js 프론트엔드 (Node.js, TypeScript, TailwindCSS)
│   ├── app/                          # Next.js App Router 기반 페이지/라우팅
│   ├── components/                   # UI 컴포넌트 (재사용 컴포넌트 모음)
│   ├── lib/                          # 클라이언트/유틸 (API 호출, 공통 로직)
│   ├── public/                       # 정적 파일 (이미지/폰트 등)
│   ├── next.config.mjs               # Next.js 설정
│   ├── tailwind.config.ts            # Tailwind 설정
│   ├── tsconfig.json                 # TypeScript 설정
│   └── package.json                  # 프론트 의존성/스크립트
├── backend/                          # FastAPI 백엔드 (Python)
│   ├── main.py                       # FastAPI 앱 엔트리 (라우터 include, 서버 진입점)
│   ├── routes/                       # API 라우터 모음 (FastAPI APIRouter)
│   ├── image_generator/              # 이미지 생성 파이프라인 (Diffusers/SDXL, ControlNet, IP-Adapter 등)
│   ├── text_generator/               # 문구 생성 로직 (OpenAI API 등)
│   ├── assets/                       # 생성/프리셋 자산 (presets, generated 등)
│   ├── test/                         # 실험/테스트 데이터 및 실행 스크립트 (reference, user_input, experiment 등)
│   ├── auth.py                       # 인증/보안 라우터 (JWT 등)
│   ├── db.py                         # DB 연결/세션 (SQLAlchemy)
│   ├── models.py                     # DB 모델 정의 (SQLAlchemy ORM)
│   ├── schemas.py                    # 요청/응답 스키마 (Pydantic)
│   ├── ai_clients.py                 # 외부 AI API 클라이언트 (OpenAI 등)
│   ├── generations.py                # 생성 결과 저장/조회 로직
│   ├── analytics_router.py           # 상권/분석 API 라우터
│   ├── analytics_service.py          # 상권/분석 서비스 로직
│   ├── scheduler.py                  # 스케줄링(자동 실행) 엔트리
│   ├── scheduler_router.py           # 스케줄러 API 라우터
│   ├── observability.py              # Langfuse/W&B 로깅 유틸
│   └── requirements.txt              # 백엔드 의존성 (환경에 따라 torch/diffusers 등 추가)
├── docs/                             # 문서/자료 (설계, UI, 참고)
├── model-server/                     # 모델 서버 (Docker, Python) - GPU 환경 추론용
│   ├── main.py                       # 모델 서버 엔트리
│   └── Dockerfile                    # 모델 서버 컨테이너 빌드
├── ngrok/                            # ngrok 설정/실행 파일 (로컬 OAuth 테스트용)
├── wandb/                            # W&B 실행 로그/아티팩트(실험 산출물)
├── docker-compose.yml                # 멀티 서비스 구성 (backend/model-server 등)
├── .env.example                      # 환경변수 템플릿
├── requirements.txt                  # 루트 의존성 (프로젝트 실행 기준)
└── README.md
```

<br>

---

## 4. 🗺️ User Flow

> **💡 핵심 요약:** 매장 정보 입력 → 상권/인사이트 분석 → AI 페르소나 추천 → 콘텐츠 생성(이미지+문구) → **Instagram 업로드**로 이어집니다.

**서비스 진입:** 홈 화면 → 생성 시작

### 1) 매장 정보 입력

| 항목 | 내용 |
|------|------|
| 매장 이름 | 운영 중인 매장명 입력 |
| 업종 카테고리 | 카페/베이커리 등 업종 선택 |
| 매장 위치 | 주소 검색으로 위치 지정 |

### 2) 인사이트 리포트 & AI 페르소나 추천

| 단계 | 내용 |
|------|------|
| 1 | 지역 유동인구/성별/연령 등 인사이트 확인 |
| 2 | 인사이트 기반 브랜드 페르소나 추천(Warm/Clean/Trendy/Premium 등) |
| 3 | 페르소나 선택 후 생성 페이지로 이동 |

### 3) 콘텐츠 생성 (피드/스토리)

| 단계 | 내용 |
|------|------|
| 1 | 포맷 선택: 피드 / 스토리 |
| 2 | IMAGE UPLOAD: 음식 사진 업로드 ⭐️ **필수** |
| 3 | CONTEXTUAL REFERENCE: 레퍼런스/프리셋 선택 (무드/배경/조명) |
| 4 | COPYWRITING HINT: 문구 힌트 입력(선택) |
| 5 | 생성하기 → Live Preview에서 결과 확인 |

### 4) Instagram 업로드 (마지막)

| 단계 | 내용 |
|------|------|
| 1 | Instagram 계정 연동(OAuth) |
| 2 | 이미지/캡션 최종 확인 및 편집 |
| 3 | 즉시 업로드 또는 예약 업로드 |
| 4 | 업로드 결과 확인 |

<br>

---

## 5. 👥 팀 소개: Team 4

| 이름 | 역할 | Github | 협업일지 |
|------|------|--------|----------|
| 황유민 | PM/모델 | <a href="https://github.com/Yumin-Hwang046"><img src="https://github.com/Yumin-Hwang046.png?size=40" width="40" height="40" /></a> | [![Notion](https://img.shields.io/badge/Notion-000000?style=flat&logo=notion&logoColor=white)](https://www.notion.so/333826fb906180b7aa05dda6a9739931?v=333826fb906180ffb807000ca369af84) |
| 김슬기 | 모델 | <a href="https://github.com/devskk25"><img src="https://github.com/devskk25.png?size=40" width="40" height="40" /></a> | [![Notion](https://img.shields.io/badge/Notion-000000?style=flat&logo=notion&logoColor=white)](https://www.notion.so/333826fb9061803c87fdcd48cff9c353?v=333826fb906181a08997000ca6f45287) |
| 문진우 | 프론트엔드/서빙 | <a href="https://github.com/dinu1108"><img src="https://github.com/dinu1108.png?size=40" width="40" height="40" /></a> | [![Notion](https://img.shields.io/badge/Notion-000000?style=flat&logo=notion&logoColor=white)](https://www.notion.so/333826fb9061808b9768ec8ee7f1cd2e?v=333826fb90618136acce000c662dbbc5) |
| 김민주 | 백엔드/모델 | <a href="https://github.com/kmjlast-dev"><img src="https://github.com/kmjlast-dev.png?size=40" width="40" height="40" /></a> | [![Notion](https://img.shields.io/badge/Notion-000000?style=flat&logo=notion&logoColor=white)](https://www.notion.so/333826fb90618042b9dae519f7f57dc7?v=333826fb906181da9569000c2f5694aa) |

<br>

---

## 6. 📊 타임라인

| 날짜 | 단계 | 주요 내용 | 담당자 | 상태 |
|------|------|-----------|--------|------|
| 2026-04-01 | 기획 | 저장소 초기 세팅 · 문서/규칙 정리 |  | ✅ 완료 |
| 2026-04-02 | 프론트엔드 | UI 프로토타입/화면 설계 정리 |  | ✅ 완료 |
| 2026-04-06 | 모델 | 이미지 생성 파이프라인 기본 구조 구축 · 배경/분위기 변환 실험 |  | ✅ 완료 |
| 2026-04-07 | 모델 | “참고 이미지 스타일 반영” 방식의 이미지 생성 실험 |  | ✅ 완료 |
| 2026-04-09 | 모델 | 실험 스크립트/테스트 데이터(입력 이미지, 참고 이미지) 정리 |  | ✅ 완료 |
| 2026-04-10 | 모델 | 결과 저장 구조 정리 · 실험 반복 실행 흐름 개선 |  | ✅ 완료 |
| 2026-04-14 | 모델 | 마스크(가릴 영역) 기반 이미지 재생성 방식 도입 · 배경 교체 안정화 시도 |  | ✅ 완료 |
| 2026-04-15 | 서비스 | 상권/캘린더/추천 등 서비스 기능 반영 |  | ✅ 완료 |
| 2026-04-16 | 백엔드/연동 | Instagram 연동(로그인/권한/업로드) 기능 추가 |  | ✅ 완료 |
| 2026-04-16 | 실험/관측 | 실험 로그/추적(품질 비교용) 도입 |  | 🧪 실험 |
| 2026-04-17 | 백엔드 | 서버 기동 안정화 · DB/환경변수 정리 · 업로드 기능 개선 |  | ✅ 완료 |
| 2026-04-19 | 통합 | 프론트-백엔드-모델 연결 및 통합 작업 |  | ✅ 완료 |
| 2026-04-20 | 서비스/배포 | 참고 이미지/구조 정리 · 프론트 정리 · Docker 구성 보완 |  | ✅ 완료 |
| 2026-04-22 | 배포 | 배포/실행 환경 개선 · 프론트 배포 이슈 수정 |  | ✅ 완료 |
| 2026-04-24 | 모델/서비스 | 문구 생성 API 전환 · 업로드/프리셋 경로 안정화 · 이미지 합성/구도 실험 |  | 🧪 실험 |
| 2026-04-27 | 문서 | README/타임라인 최신화 |  | ✅ 완료 |

<br>

---

## 7. 📎 참고 자료 및 산출물

- 📘 최종 보고서: [다운로드](#)

<br>

---

## 8. 📄 사용한 모델 및 라이선스


| 구성요소 | 용도 | 특징(핵심 파라미터) | 용량 | 라이선스 |
|---|---|---|---:|---|
| `rembg` (Background Removal) | 음식/상품만 분리해서 합성/인페인팅 마스크 제작 | 배경 제거 결과로 마스크 생성에 활용 | 약 `176MB`(u2net.onnx 기준) | 패키지: MIT<br>모델 파일/가중치: 각 배포처 라이선스 확인 |
| GPT Image API (OpenAI) | 이미지 생성/편집을 “API 호출”로 처리 | 서버에 모델을 내려받지 않고 사용(호스팅 모델)<br>고품질 생성/편집(inpaint 포함) | 로컬 다운로드 없음 | OpenAI API 약관/정책 적용 |
| SDXL Inpainting (Stable Diffusion XL) | 마스크 기반 인페인팅(배경 교체/수정) | 텍스트 프롬프트 + 마스크로 특정 영역만 재생성 | 약 `10GB~21GB`(캐시/variant에 따라 차이) | CreativeML Open RAIL++-M |
| Depth ControlNet (SDXL) | “원본 구조/깊이”를 유지하면서 생성 안정화 | 깊이 조건으로 형태/구도 유지에 도움<br>`controlnet_conditioning_scale`로 영향도 조절 | 약 `640MB`(small) ~ `2.5GB`(fp16 safetensors) | OpenRAIL++ |
| Shadow Post-Process (합성 후처리) | 분리된 음식/상품을 자연스럽게 보이게(그림자) | `shadow-darkness 0.35`<br>`--shadow-opacity 0.8` | 해당 없음 | 해당 없음(내부 후처리 파라미터) |
