"""
run_case4_experiments.py
========================
Case4 IP-Adapter 실험 일괄 실행 스크립트.

핵심 목표:
  사용자의 음식/카페 사진(user_input)을 유지하면서,
  레퍼런스 이미지(reference)의 분위기·조명·배경 스타일을 입혀 광고 이미지를 생성한다.

실험 조합 (총 6개):
  W-CAFE-01~03 : cafe 사진 3장  ×  warm 레퍼런스 (fc_201/205/209)
  P-FOOD-01~03 : food 사진 3장  ×  premium 레퍼런스 (ff_207/211/213)

실행 방법 (VM의 Team4_ImgGeneration_Project/ 루트에서):
  python -m backend.test.experiment.run_case4_experiments
"""

import os
import sys
import time
import csv
from datetime import datetime

# ─────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────

# 이 파일이 위치한 폴더(backend/test/experiment/)의 절대경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# backend/test/ 경로 (레퍼런스·사용자 이미지가 여기 있음)
TEST_DIR = os.path.join(BASE_DIR, "..")

# backend/ 경로를 Python 모듈 탐색 경로에 추가
# → 'from image_generator.case4_ip_adapter import ...' 가 작동하게 하기 위함
sys.path.insert(0, os.path.join(BASE_DIR, "..", ".."))

from image_generator.case4_ip_adapter import generate_image_case4_ip_adapter

# ─────────────────────────────────────────────
# 레퍼런스 이미지 목록 (무드별 3장)
# ─────────────────────────────────────────────

# warm 무드 레퍼런스: 따뜻한 조명, 카페 감성
REF_WARM = [
    os.path.join(TEST_DIR, "reference/warm/fc_201.png"),
    os.path.join(TEST_DIR, "reference/warm/fc_205.png"),
    os.path.join(TEST_DIR, "reference/warm/fc_209.png"),
]

# premium 무드 레퍼런스: 다크 계열, 고급스러운 분위기
REF_PREMIUM = [
    os.path.join(TEST_DIR, "reference/premium/ff_207.png"),
    os.path.join(TEST_DIR, "reference/premium/ff_211.png"),
    os.path.join(TEST_DIR, "reference/premium/ff_213.png"),
]

# ─────────────────────────────────────────────
# 사용자 입력 이미지 목록
# ─────────────────────────────────────────────

# cafe 폴더: 카페 매장 환경 사진
USER_CAFE = [
    os.path.join(TEST_DIR, "user_input/cafe/KakaoTalk_20260409_103018854_01.jpg"),
    os.path.join(TEST_DIR, "user_input/cafe/KakaoTalk_20260409_103018854_21.jpg"),
    os.path.join(TEST_DIR, "user_input/cafe/KakaoTalk_20260409_103350583_06.jpg"),
]

# food 폴더: 음식 단독 사진
USER_FOOD = [
    os.path.join(TEST_DIR, "user_input/food/KakaoTalk_20260409_103018854_26.jpg"),
    os.path.join(TEST_DIR, "user_input/food/KakaoTalk_20260409_103207841_01.jpg"),
    os.path.join(TEST_DIR, "user_input/food/KakaoTalk_20260409_103350583_19.jpg"),
]

# ─────────────────────────────────────────────
# 실험 조합 리스트 구성
# ─────────────────────────────────────────────

# zip()은 두 리스트를 순서대로 1:1 쌍으로 묶어준다.
# enumerate(..., 1)은 1부터 번호를 매긴다.
EXPERIMENTS = []

# 조합 1: cafe 사진 × warm 레퍼런스 (3쌍)
for i, (user, ref) in enumerate(zip(USER_CAFE, REF_WARM), 1):
    EXPERIMENTS.append({
        "id":   f"W-CAFE-{i:02d}",   # 실험 고유 ID
        "user": user,                 # 사용자 이미지 경로
        "ref":  ref,                  # 레퍼런스 이미지 경로
        "mood": "warm",               # 무드 키 (프롬프트 선택용)
    })

# 조합 2: food 사진 × premium 레퍼런스 (3쌍)
for i, (user, ref) in enumerate(zip(USER_FOOD, REF_PREMIUM), 1):
    EXPERIMENTS.append({
        "id":   f"P-FOOD-{i:02d}",
        "user": user,
        "ref":  ref,
        "mood": "premium",
    })

# ─────────────────────────────────────────────
# 무드별 텍스트 프롬프트
# ─────────────────────────────────────────────

# 이 프롬프트는 case4_ip_adapter.py의 build_case4_prompt()에 전달된다.
# "음식은 유지하고 배경/테이블 스타일만 무드에 맞게 바꿔라"는 지시가 함수 내부에 이미 포함되어 있으므로,
# 여기서는 무드 분위기만 간략하게 추가한다.
PROMPT_MAP = {
    "warm":    "Warm cafe interior background, cozy lighting, wooden table.",
    "premium": "Dark premium restaurant background, elegant lighting, marble table.",
}

# ─────────────────────────────────────────────
# 실험 실행
# ─────────────────────────────────────────────

GENERATED_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "assets", "generated"))


def get_next_exp_dir() -> str:
    if not os.path.isdir(GENERATED_ROOT):
        return "exp_001"
    candidates = []
    for d in os.listdir(GENERATED_ROOT):
        if d.startswith("exp_") and d[4:].isdigit():
            candidates.append(int(d[4:]))
    next_id = max(candidates) + 1 if candidates else 1
    return f"exp_{next_id:03d}"


EXP_DIR = get_next_exp_dir()

RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_PATH = os.path.join(BASE_DIR, f"case4_log_{RUN_TS}.csv")

try:
    import wandb
    WANDB_ON = bool(os.getenv("WANDB_API_KEY"))
except Exception:
    WANDB_ON = False

if WANDB_ON:
    wandb.init(
        project=os.getenv("WANDB_PROJECT", "case4-experiments"),
        entity=os.getenv("WANDB_ENTITY", None),
        name=RUN_TS,
    )

print(f"\n총 {len(EXPERIMENTS)}개 실험을 시작합니다.\n" + "=" * 50)

with open(LOG_PATH, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["run_id", "exp_id", "user_image", "ref_image", "prompt", "output_path", "elapsed_sec"])

for idx, exp in enumerate(EXPERIMENTS, 1):
    print(f"\n[{exp['id']}] 실행 중...")
    print(f"  user : {os.path.basename(exp['user'])}")
    print(f"  ref  : {os.path.basename(exp['ref'])}")

    t0 = time.time()
    try:
        output_name = f"{RUN_TS}_case4_{exp['id']}_{idx:03d}.png"
        result = generate_image_case4_ip_adapter(
            user_image_path=exp["user"],
            reference_image_path=exp["ref"],
            user_prompt=PROMPT_MAP[exp["mood"]],
            output_name=output_name,
            output_subdir=EXP_DIR,
            # ip_adapter_scale: 레퍼런스 스타일 반영 강도 (0~1, 기본값 0.7)
            # strength: 원본 이미지 변형 강도 (0~1, 낮을수록 원본 유지)
            # 두 값 모두 case4_ip_adapter.py 기본값 사용 (각각 0.7, 0.6)
        )
        elapsed = time.time() - t0
        print(f"  ✅ 완료 ({elapsed:.1f}s) → {result['path']}")

        with open(LOG_PATH, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                idx,
                exp["id"],
                exp["user"],
                exp["ref"],
                PROMPT_MAP[exp["mood"]],
                result["path"],
                f"{elapsed:.1f}",
            ])

        if WANDB_ON:
            wandb.log({
                "exp_id": exp["id"],
                "prompt": PROMPT_MAP[exp["mood"]],
                "output": wandb.Image(result["path"]),
                "elapsed_sec": elapsed,
            })
    except Exception as e:
        print(f"  ❌ 실패: {e}")

print("\n" + "=" * 50)
print("모든 실험 완료. 결과 이미지 위치: backend/assets/generated/")
