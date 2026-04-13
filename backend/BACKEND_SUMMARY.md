# Backend 구현 정리

## 1. 프로젝트 구조

```
backend/
├── main.py                        # FastAPI 진입점, 라우터, lifespan
├── requirements.txt               # 의존성
├── .env                           # 환경변수 (API 키 등)
├── .env.example                   # 환경변수 템플릿
│
├── image_analyzer/                # GPT Vision 이미지 분석
│   ├── __init__.py
│   └── analyzer.py                # 무드별 카피 + 배경 프롬프트 + 해시태그 추출
│
├── image_generator/               # 배경 이미지 생성
│   ├── __init__.py
│   └── image_gen.py               # SD 1.5 (기본) / SDXL + IP-Adapter (레퍼런스 있을 때)
│
├── compositor/                    # 이미지 합성 + 광고 렌더링
│   ├── __init__.py
│   ├── compositor.py              # 배경 제거(rembg) + 이미지 합성
│   ├── lighting.py                # 조명 분석 + 색감 조화 (light wrap, color match)
│   ├── playwright_renderer.py     # HTML 템플릿 → Playwright 스크린샷
│   ├── font_manager.py            # 폰트 관리
│   └── templates/                 # 무드별 HTML 광고 템플릿
│       ├── clean.html             # 깔끔한 상품 홍보
│       ├── warm.html              # 따뜻한 매장 분위기
│       ├── trendy.html            # 트렌디한 메뉴 홍보
│       └── premium.html           # 프리미엄 매장·상품
│
└── text_generator/                # 광고 문구 생성 전용
    ├── __init__.py
    └── generator.py               # 감성형·직접형·스토리형 카피 3종 생성
```

---

## 2. API 엔드포인트

### `GET /api/health`
서버 상태 확인

---

### `POST /api/generate`
**이미지 생성 마법사** — 제품/음식 사진으로 완성된 광고 이미지 생성

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `image` | file | ✅ | 제품/음식 사진 (JPG, PNG, WebP, 최대 10MB) |
| `ref_image` | file | ❌ | 스타일 레퍼런스 이미지 (JPG, PNG) — 있으면 SDXL 파이프라인 |
| `user_prompt` | string | ❌ | 추가 요청사항 |
| `mood` | string | ❌ | 광고 무드 (기본: `깔끔한 상품 홍보`) |
| `subject_type` | string | ❌ | `food` \| `product` (기본: `food`) |
| `size` | string | ❌ | `square` \| `portrait` \| `landscape` \| `naver` (기본: `square`) |

**응답**
```json
{
  "product_description": "제품 설명",
  "hashtags": ["#태그1", "#태그2"],
  "results": [
    { "ad_copy": "광고 문구", "image_b64": "base64..." }
  ]
}
```

**파이프라인 분기**

```
이미지 업로드
  → GPT Vision 분석 (ad_copy, bg_prompt, hashtags, details 추출)
  ┌─ ref_image 없음 (food / product 공통)
  │     → SD 1.5 (DreamShaper) 로컬 배경 생성
  │     → rembg 배경 제거
  │     → 이미지 합성 (접지 그림자 + 색감 조화)
  │     → SD inpainting으로 경계 자연화
  │     → Playwright HTML 렌더링
  └─ ref_image 있음
        → SDXL-Lightning + IP-Adapter 배경 생성 (레퍼런스 스타일 반영)
        → rembg 배경 제거
        → 이미지 합성 (접지 그림자 + 색감 조화)
        → Playwright HTML 렌더링
  → JPEG base64 반환
```

**합성 파이프라인 (compositor)**

```
[1] rembg (isnet-general-use)
    → 제품 배경 제거 → RGBA 이미지

[2] 제품 레이아웃 계산
    → 가로세로 비율에 따라 scale / 위치 결정
    → 하단 텍스트 패널(34%) 위로 제품 배치

[3] 이미지 합성
    → 접지 그림자 (타원형 contact shadow)
    → 제품 붙여넣기

[4] 후처리
    → color match (Reinhard-style 색 통계 조화)
    → light wrap (배경 빛이 제품 경계를 감싸는 효과)

[5] inpainting (SD 1.5, ref_image 없을 때만)
    → 제품-배경 경계 자연화
```

---

### `POST /api/generate/text`
**텍스트만으로 광고 이미지 생성** (제품 사진 불필요)

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `ad_copy` | string | ✅ | 광고 문구 |
| `user_prompt` | string | ❌ | 추가 요청사항 |
| `mood` | string | ❌ | 광고 무드 |
| `size` | string | ❌ | 출력 비율 |

**응답**
```json
{ "image_b64": "base64..." }
```

---

### `POST /api/copy`
**문구 만들기** — 이미지 또는 텍스트로 광고 카피 3종 생성

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `image` | file | ✅ (둘 중 하나) | 제품/매장 사진 |
| `description` | string | ✅ (둘 중 하나) | 제품/매장 텍스트 설명 |
| `user_prompt` | string | ❌ | 추가 요청사항 |
| `mood` | string | ❌ | 광고 무드 |

**응답**
```json
{
  "product_description": "제품 설명",
  "variants": [
    { "style": "감성형",  "headline": "오늘 점심, 제대로",    "tagline": "바쁜 하루 속 진짜 한 끼" },
    { "style": "직접형",  "headline": "국물이 답이다",        "tagline": "20년 묵은 육수, 지금 맛보세요" },
    { "style": "스토리형","headline": "할머니 손맛 그대로",   "tagline": "매일 새벽 끓이는 그 국물" }
  ],
  "hashtags": ["#갈비탕", "#소상공인맛집"]
}
```

---

## 3. 무드 시스템

| 무드명 | 템플릿 | 디자인 특징 |
|---|---|---|
| 깔끔한 상품 홍보 | `clean.html` | 하단 솔리드 패널(34%), 흰색 텍스트, 미니멀 |
| 따뜻한 매장 분위기 | `warm.html` | 그라디언트 스크림, 앰버 톤, 나눔명조 폰트 |
| 트렌디한 메뉴 홍보 | `trendy.html` | 대형 헤드라인, 흰색 태그 뱃지, 다이나믹 |
| 프리미엄 매장·상품 | `premium.html` | 다크 오버레이, 골드 라인, 절제된 럭셔리 |

> 모든 템플릿은 Pretendard 폰트 (jsDelivr CDN) 사용. warm은 추가로 Nanum Myeongjo 사용.

---

## 4. 이미지 생성 엔진

### SD 1.5 DreamShaper (기본 — ref_image 없을 때)

- 모델: `Lykon/DreamShaper`
- 스케줄러: DPMSolverMultistep (karras sigmas)
- 생성 해상도: 최대 768×768 → 타겟 사이즈로 upscale
- GPU(CUDA) 자동 감지, 없으면 CPU 폴백

| size 옵션 | 최종 출력 |
|---|---|
| `square` | 1024×1024 |
| `portrait` | 1024×1792 |
| `landscape` | 1792×1024 |
| `naver` | 860×1200 |

### SDXL-Lightning + IP-Adapter (ref_image 있을 때)

- 모델: `ByteDance/SDXL-Lightning` (4-step, guidance_scale=0.0)
- IP-Adapter: `h94/IP-Adapter` (sdxl_models) — 레퍼런스 이미지 스타일 반영
- GPU(CUDA) 자동 감지, 없으면 CPU 폴백

```env
IMAGE_MODEL=sdxl-lightning
IP_ADAPTER_SCALE=0.40   # 레퍼런스 반영 강도 (0.0~1.0)
IP_ADAPTER_WEIGHT=ip-adapter_sdxl.safetensors
```

---

## 5. 환경변수 (.env)

```env
# 필수
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini   # 기본값

# 선택 — SDXL 파이프라인 (ref_image 있을 때만 사용)
IMAGE_MODEL=sdxl-lightning
IP_ADAPTER_SCALE=0.40
IP_ADAPTER_WEIGHT=ip-adapter_sdxl.safetensors
```

---

## 6. 로컬 실행 방법

```bash
# 가상환경 활성화
.venv\Scripts\activate

# 의존성 설치
uv pip install -r requirements.txt

# Playwright 크로미움 설치 (최초 1회)
playwright install chromium

# 서버 실행
python main.py
```

서버 실행 후 `http://localhost:8000/docs` 에서 Swagger UI로 API 테스트 가능

---

## 7. 미구현 / 추후 결정 필요

| 항목 | 현황 | 비고 |
|---|---|---|
| MySQL DB | 미구현 | 저장할 데이터 범위 확정 후 작업 필요 |
| 인증 / 사용자 관리 | 미구현 | 로그인·저장 기능 추후 추가 예정 |
| 결과 히스토리 | 미구현 | 현재 localStorage에만 임시 저장 |
