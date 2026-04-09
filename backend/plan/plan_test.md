# 🧪 모델 실험 계획 (Image Generation Test Plan)

## 핵심 목표

> **사용자의 음식 사진** + **무드별 레퍼런스 이미지** 를 입력하면,  
> 레퍼런스 이미지의 **분위기·조명·구도**를 유지하면서  
> 사용자 음식이 그 안에 자연스럽게 적용된 광고 이미지를 생성한다.

---

## 폴더 구조 (데이터 위치)

```
backend/test/
├── reference/          ← 무드별 레퍼런스 이미지 (각 3장)
│   ├── warm/           ref_01.png / ref_02.png / ref_03.png
│   ├── clean/          ref_01.png / ref_02.png / ref_03.png
│   ├── trendy/         ref_01.png / ref_02.png / ref_03.png
│   └── premium/        ref_01.png / ref_02.png / ref_03.png
│
└── user_input/         ← 실험에 쓸 음식(사용자) 사진
    product_01.png / product_02.png / ...
```

---

## Step 1 — 데이터 준비

> 이미지를 직접 찾아서 폴더에 넣는 단계입니다.

### 1-1. 레퍼런스 이미지 수집 (총 12장)

각 무드의 **분위기를 대표하는 광고 사진**을 구글 이미지, Pinterest, Unsplash 등에서 찾아 저장합니다.  
파일명은 `ref_01.png`, `ref_02.png`, `ref_03.png` 으로 통일합니다.

| 상태 | 무드 | 이미지 설명 | 저장 경로 |
|:---:|:---:|---|---|
| [ ] | **warm** | 따뜻한 조명, 브라운·베이지 계열, 아늑한 카페 분위기 | `test/reference/warm/` |
| [ ] | **clean** | 흰 배경, 균일한 조명, 여백이 많은 미니멀 구도 | `test/reference/clean/` |
| [ ] | **trendy** | 채도 높은 색감, 감성적인 SNS 스타일, 힙한 느낌 | `test/reference/trendy/` |
| [ ] | **premium** | 다크 계열, 절제된 구도, 고급스러운 분위기 | `test/reference/premium/` |

### 1-2. 사용자 입력 이미지 준비

실험에 사용할 **음식 사진**을 최소 1~3장 준비하고 아래 경로에 저장합니다.

| 상태 | 파일명 | 내용 | 저장 경로 |
|:---:|:---:|---|---|
| [ ] | `product_01.png` | 실험용 음식 사진 1 | `test/user_input/` |
| [ ] | `product_02.png` | 실험용 음식 사진 2 (선택) | `test/user_input/` |
| [ ] | `product_03.png` | 실험용 음식 사진 3 (선택) | `test/user_input/` |

> **이미지 준비 팁**
> - 배경이 단순한 음식 사진일수록 결과가 깔끔합니다.
> - 해상도는 512×512 이상 권장합니다.
> - `.png` 또는 `.jpg` 모두 사용 가능하지만 파일명은 위와 일치시켜 주세요.

---

## Step 2 — Case별 단독 실행 테스트 (베이스라인)

> 각 생성 케이스를 한 번씩 실행해서 이미지가 정상 출력되는지 확인합니다.  
> 아직 품질 평가는 하지 않고, **에러 없이 실행되는지**만 체크합니다.

```bash
# backend/ 디렉터리에서 실행
python -m image_generator.case1_sdxl
python -m image_generator.case2_ip_adapter
python -m image_generator.case3_controlnet
```

| 상태 | Case | 입력 | 확인 내용 |
|:---:|:---:|---|---|
| [ ] | Case 1 | 텍스트 프롬프트 | `assets/generated/`에 이미지 파일 생성 여부 |
| [ ] | Case 2 | 레퍼런스 이미지 + 프롬프트 | 이미지 생성 여부 + VRAM 에러 없는지 |
| [ ] | Case 3 | 음식 사진 + 배경 프롬프트 | 이미지 생성 여부 + 배경 교체 여부 |

> 실행 중 `CUDA out of memory` 에러가 나면 아래를 `case*.py` 파일에 추가합니다.
> ```python
> pipe.enable_model_cpu_offload()
> ```

---

## Step 3 — 핵심 기능 실험 (무드 × 레퍼런스 조합)

> 핵심 목표인 **"사용자 음식 + 레퍼런스 → 합성 이미지"** 를 무드별로 실험합니다.  
> 레퍼런스 3장 × 무드 4개 = **총 12가지 조합**을 실행합니다.

### 실험 조합표

| 상태 | 실험 ID | 사용자 이미지 | 무드 | 레퍼런스 |
|:---:|:---:|---|:---:|---|
| [ ] | EXP-W1 | product_01.png | warm | warm/ref_01.png |
| [ ] | EXP-W2 | product_01.png | warm | warm/ref_02.png |
| [ ] | EXP-W3 | product_01.png | warm | warm/ref_03.png |
| [ ] | EXP-C1 | product_01.png | clean | clean/ref_01.png |
| [ ] | EXP-C2 | product_01.png | clean | clean/ref_02.png |
| [ ] | EXP-C3 | product_01.png | clean | clean/ref_03.png |
| [ ] | EXP-T1 | product_01.png | trendy | trendy/ref_01.png |
| [ ] | EXP-T2 | product_01.png | trendy | trendy/ref_02.png |
| [ ] | EXP-T3 | product_01.png | trendy | trendy/ref_03.png |
| [ ] | EXP-P1 | product_01.png | premium | premium/ref_01.png |
| [ ] | EXP-P2 | product_01.png | premium | premium/ref_02.png |
| [ ] | EXP-P3 | product_01.png | premium | premium/ref_03.png |

### 각 실험 후 기록 양식

```
실험 ID : EXP-W1
사용 모델 : case2_ip_adapter.py
소요 시간 : X초
VRAM 사용량 : XGB
성공한 점 :
실패/이슈 :
다음 실험 방향 :
```

---

## Step 4 — 파라미터 튜닝

> Step 4에서 가장 결과가 좋았던 조합을 기준으로 파라미터를 조금씩 바꾸며 품질을 개선합니다.

| 상태 | 튜닝 항목 | 변경 내용 | 기대 효과 |
|:---:|---|---|---|
| [ ] | `ip_adapter_scale` | 0.3 / 0.5 / 0.7 / 0.9 순서로 실험 | 레퍼런스 스타일 반영 강도 조절 |
| [ ] | `guidance_scale` | 6.0 / 7.0 / 8.5 비교 | 프롬프트 충실도 조절 |
| [ ] | `num_inference_steps` | 20 / 30 / 40 비교 | 품질 vs 속도 트레이드오프 |
| [ ] | Negative Prompt 추가 | `"blurry, low quality, deformed"` 등 추가 | 불필요한 요소 제거 |
| [ ] | Base 모델 교체 | `RealVisXL_V5.0` 으로 교체 실험 | 포토리얼리즘 강화 |

---

## Step 5 — 경량화 실험 (배포 대비)

> GCP 배포 시 속도와 비용을 줄이기 위한 실험입니다. Step 5 이후 진행합니다.

| 상태 | 경량화 방법 | 내용 |
|:---:|---|---|
| [ ] | 모델 교체 | `segmind/SSD-1B` (SDXL 대비 ~60% 빠름) |
| [ ] | Steps 감소 | base 30→20, refiner 15→10 으로 줄여서 속도 비교 |
| [ ] | CPU Offload | `pipe.enable_model_cpu_offload()` — VRAM 부족 시 대안 |

---

## 실험 결과 로그 (누적)

실험을 진행하면서 아래에 결과를 계속 추가해 나갑니다.

| 실험 ID | 무드 | 레퍼런스 | ip_scale | 소요 시간 | 성공 | 이슈 |
|---------|:---:|---|:---:|---|---|---|
| (실험 후 기록) | | | | | | |
