"""
run_case5_experiments.py
Case5 (Inpainting + IP-Adapter) 실험 스크립트.

사용 방법:
  python -m backend.test.experiment.run_case5_experiments
"""

import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
TEST_DIR = os.path.join(BASE_DIR, "..")
sys.path.insert(0, BACKEND_DIR)

from image_generator.case5_inpaint_ip_adapter import generate_image_case5_inpaint_ip_adapter

EXPERIMENTS = [
    {
        "id": "E01",
        "user": os.path.join(TEST_DIR, "user_input/cafe/KakaoTalk_20260409_103018854_01.jpg"),
        "ref": os.path.join(TEST_DIR, "reference/warm/fc_201.png"),
        "mask": os.path.join(TEST_DIR, "mask/case5_mask.png"),  # 배경=흰색, 음식=검정
        "prompt": "Warm cafe interior background, cozy lighting, wooden table.",
        "mask_invert": False,
    },
]

RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_SUBDIR = f"case5_{RUN_TS}"

print(f"총 {len(EXPERIMENTS)}개 실험을 시작합니다.")

for exp in EXPERIMENTS:
    print(f"[{exp['id']}] 실행 중...")
    result = generate_image_case5_inpaint_ip_adapter(
        user_image_path=exp["user"],
        reference_image_path=exp["ref"],
        mask_image_path=exp["mask"],
        user_prompt=exp["prompt"],
        mask_invert=exp.get("mask_invert", False),
        output_subdir=OUTPUT_SUBDIR,
    )
    print(f"  ✅ 완료 → {result['path']}")

print("모든 실험 완료.")
