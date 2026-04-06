# 🗂️ Backend 구현 계획

## 구현 목표
광고 문구와 이미지를 AI로 자동 생성하는 백엔드 파이프라인 구축

---

## 0. 데이터 및 학습 전략

> **모든 모델은 파인튜닝 없이 추론(Inference)만 사용합니다.**
> 사전학습된 모델을 그대로 사용하기 때문에 별도 학습 데이터가 필요하지 않습니다.

| 데이터 종류 | 필요 여부 | 비고 |
|------------|-----------|------|
| 학습 데이터 | ❌ | 모델을 새로 학습하지 않음 |
| 파인튜닝 데이터 | ❌ | API 프롬프트 엔지니어링으로 대체 |
| 레퍼런스 이미지 | ✅ (런타임) | 사용자가 직접 업로드 (Case 2) |
| 평가용 테스트 이미지 | 🟡 권장 | 상품 사진 5~10장 준비 → 품질 검증용 |

---

## 1. 사용 모델 설명

| 모델 | 역할 | 왜 필요한가 | 파인튜닝 | 실행 방식 |
|------|------|------------|---------|-----------|
| **GPT-4o** | 이미지 분석 + 문구 생성 | 사진을 보고 광고 카피를 쓸 수 있는 멀티모달 LLM | ❌ 불필요 | OpenAI API (GPU 불필요) |
| **SDXL Base+Refiner** | Case 1 이미지 생성 | 텍스트 → 고품질 광고 이미지, 품질 우선 | ❌ 불필요 | 서버 추론 (GPU 필요) |
| **SDXL** | Case 2, 3 이미지 생성 | IP-Adapter / ControlNet과 결합 가능한 오픈소스 기반 | ❌ 불필요 | 서버 추론 (GPU 필요) |
| **IP-Adapter** | 레퍼런스 스타일 적용 | SDXL 어댑터, 레퍼런스 이미지의 색감·스타일 복사 | ❌ 불필요 | SDXL과 함께 추론 (GPU 필요) |
| **ControlNet** | 제품 형태 보존 | 원본 사진 구조(depth map)를 유지하며 배경 합성 | ❌ 불필요 | SDXL과 함께 추론 (GPU 필요) |
| **rembg** | 배경 제거 | 제품 사진에서 배경 제거 (Case 3 전처리) | ❌ 불필요 | CPU 추론 가능 |

---

## 2. 인프라 전략 (Mac + GPU 없음)

### 단계별 접근

```
1단계 (모델 개발, 4/4~4/6)
  → OpenAI API (GPT-4o) + SDXL Base+Refiner(이미지 생성) 위주로 구현
  → 이미지 생성은 GCP L4 GPU 환경 필요
  → Case 1 + 문구 생성 완성 목표

2단계 (서빙, 4/6~4/9)
  → Case 2, 3 (SDXL + IP-Adapter + ControlNet) 구현이 필요하면
  → Google Colab (무료 T4 GPU)으로 실험 먼저
  → 안정화되면 GCP T4 인스턴스로 이전
```

| 방법 | 적합 시점 | GPU | 비용 |
|------|-----------|-----|------|
| Mac 로컬 | 문구/분석 단계 | 불필요 | API 사용료만 |
| GCP L4 | Case 1 이미지 생성 | L4 | 유료 |
| Google Colab | 2단계 실험 | T4 무료 | 무료 (세션 제한) |
| GCP T4 | 2단계 배포 | T4 | 유료 (시간당 과금) |

---

## 3. 문구 생성 (text_generator/)

### 입력 → 출력
- 입력: 상품 이미지 + 무드 선택
- 출력: 광고 문구 + 해시태그

### 구현 계획
| 단계 | 내용 | 핵심 기술 |
|------|------|-----------|
| 1 | 이미지 분석 | GPT-4o Vision API |
| 2 | 무드별 프롬프트 템플릿 작성 | 프롬프트 엔지니어링 |
| 3 | 광고 문구 + 해시태그 생성 | OpenAI Chat API |
| 4 | FastAPI 엔드포인트 연결 | `/generate/text` |

### 파일 구조
```
backend/text_generator/
├── prompt_templates.py   # 무드별 프롬프트 템플릿
├── generator.py          # 문구 생성 메인 로직
└── schemas.py            # 입출력 데이터 구조 정의
```

---

## 4. 이미지 생성 (image_generator/)

### Case 1: 텍스트 입력만 → 100% 생성 이미지

| 단계 | 내용 | 핵심 기술 |
|------|------|-----------|
| 1 | 무드 + 프롬프트 → 이미지 생성 프롬프트 변환 | 프롬프트 엔지니어링 |
| 2 | 이미지 생성 | SDXL Base + Refiner (Diffusers) |
| 3 | 광고 사이즈별 리사이즈 | Pillow |

### Case 2: 레퍼런스 이미지 사용 → 스타일 모방 (직접 업로드 / 프리셋 선택)
**[UX 확장]** 사용자가 직접 사진을 업로드하는 방식 외에도, 특정 무드 선택 시 제공되는 **프리셋 이미지**를 고를 수 있습니다.

| 단계 | 내용 | 핵심 기술 |
|------|------|-----------|
| 1 | 레퍼런스 이미지 특징 추출 | IP-Adapter |
| 2 | 스타일 가중치 혼합 | IP-Adapter weight 조절 |
| 3 | 이미지 생성 | SDXL + IP-Adapter |

### Case 3: 실제 제품 사진 → 배경/조명 합성

| 단계 | 내용 | 핵심 기술 |
|------|------|-----------|
| 1 | 배경 제거 | rembg |
| 2 | 제품 형태 보존용 depth map 추출 | ControlNet |
| 3 | 무드별 배경/조명 합성 | SDXL + ControlNet |

### 파일 구조
```
backend/image_generator/
├── case1_sdxl.py             # Case 1: 텍스트 → 이미지
├── case2_sdxl.py             # Case 2: 레퍼런스 스타일 적용
├── case3_product_preserve.py # Case 3: 제품 이미지 보존
├── prompt_builder.py         # 무드별 이미지 프롬프트 빌더
├── resize.py                 # 광고 사이즈별 후처리
└── schemas.py                # 입출력 데이터 구조
```

---

## 5. 공통 (image_analyzer/)

```
backend/image_analyzer/
├── analyzer.py     # 업로드 이미지 분석 (GPT-4o Vision)
└── schemas.py
```

---
## 6. 구현 순서 (권장 - 4/4~4/6 기준)

```
1단계 (4/4)      Case 1 이미지 생성(DALL·E 3) 및 문구 생성(GPT-4o Vision) 1차 구현
2단계 (4/5)      Case 2, 3 구현 → Colab에서 IP-Adapter, ControlNet 실험
3단계 (4/6)      FastAPI 엔드포인트 구현 및 테스트, 1단계 마무리
```

## 7. 전체 파이프라인 구축 단계 및 기능별 흐름

전체 파이프라인이 제공하는 핵심 기능은 크게 **1. 광고 문구 생성**과 **2. 이미지 생성(3가지 Case)** 총 4가지로 나뉩니다.

### 🔄 기능별 전체 파이프라인 작동 흐름 (요약표)

| 기능 | 입력 | 흐름 | 관련 모듈/파일 |
|---|---|---|---|
| **기능 1. 광고 문구 단독 생성 (Image-to-Text)** | 업로드/프리셋 이미지 + 무드 | `image_analyzer` 분석 ➡️ `text_generator` 문구/해시태그 생성 | `image_analyzer` / `text_generator` |
| **기능 2-1. 프롬프트 기반 이미지 생성 (Case 1)** | 프롬프트 + 무드 | (이미지 없음 → 분석 생략 가능) ➡️ `text_generator` 프롬프트 조합 ➡️ `case1_sdxl.py` 실행 | `text_generator` / `image_generator/case1_sdxl.py` |
| **기능 2-2. 스타일 및 무드 벤치마킹 (Case 2)** | 레퍼런스 이미지 + 무드 | `image_analyzer` 분석 ➡️ `text_generator` 프롬프트 조합 ➡️ `case2_sdxl.py` 실행 | `image_analyzer` / `text_generator` / `image_generator/case2_sdxl.py` |
| **기능 2-3. 제품 형태 유지 배경 합성 (Case 3)** | 제품 이미지 + 무드 | `image_analyzer` 분석 ➡️ `text_generator` 프롬프트 조합 ➡️ `case3_controlnet.py` 실행 | `image_analyzer` / `text_generator` / `image_generator/case3_controlnet.py` |

### 🚀 파이프라인 4단계 핵심 로직 구축 상세 계획
| 상태 | 단계 | 핵심 역할 | 작업 내용 |
|:---:|:---:|---|---|
| [ ] | **Step 1** | **시각 분석기** (Image Analyzer) | 사용자가 입력한 사진(원본 이미지)을 GPT-4o Vision을 통해 글로 번역(분석) |
| [ ] | **Step 2** | **광고 문구 생성기** (Text Generator) | 분석된 내용 + 선택한 '무드'를 합쳐 ChatGPT가 마케팅 문구 작성 |
| [ ] | **Step 3** | **AI 이미지 공장 가동** (Image Generator) | SDXL Base+Refiner (Case1) 및 SDXL 오픈소스 모델 연동 |
| [ ] | **Step 4** | **통합 연결** (API Routing) | 사용자의 요청 한 번에 위 1~3단계 파이프라인이 즉각 물 흐르듯 연결되도록 라우팅 |

---

## 8. 세부 구현 계획: Step 1 (시각 분석기)

파이프라인의 가장 첫 단추인 `backend/image_analyzer/analyzer.py` 개발을 위한 구체적인 액션 플랜입니다. 여기서부터 코딩을 직접 시작합니다!

### 📝 Step 1 구현 목표
사용자가 던진 사진을 컴퓨터(API)가 볼 수 있는 형태로 변환해서 OpenAI에 보낸 뒤, "이건 광택이 나는 하얀 컵에 담긴 커피야"라는 형태의 텍스트 답변을 돌려받게 만듭니다.

### 🛠️ 세부 개발 진행 순서 (할 일 목록)

| 상태 | 순서 | 목표 | 세부 내용 |
|:---:|:---:|---|---|
| [O] | 1 | **키(Key) 관리 세팅** | OpenAI API 키 발급 및 프로젝트 폴더의 `.env` 파일에 안전하게 저장 |
| [O] | 2 | **라이브러리 설치** | 통신을 위한 `openai` 툴과 이미지 처리를 위한 `Pillow` 등 필요 패키지 설치 (`pip install`) |
| [O] | 3 | **사진 변환기 제작** | `analyzer.py`에 사진 파일을 GPT가 읽을 수 있도록 `Base64` 문자열로 변환하는 헬퍼 함수(`encode_image`) 작성 |
| [O] | 4 | **메인 통신 로직 작성** | GPT에게 내릴 프롬프트 명령을 작성하고, 변환된 사진을 넘겨 텍스트 응답을 받아오는 메인 함수(`analyze_image`) 완성 |
| [ ] | 5 | **독립 테스트 진행 🔥** | 복잡한 웹 서버 구동 없이, `analyzer.py` 스크립트를 단독 실행하여 터미널에 요약 글이 나오는지 바로 체크! |
