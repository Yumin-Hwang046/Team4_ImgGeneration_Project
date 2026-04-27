#!/usr/bin/env bash
# Case5 모델 다운로드 스크립트
# 실행 전: hf auth login

set -e

ANYDOOR_DIR="${ANYDOOR_CACHE_DIR:-/root/.cache/anydoor}"
SAM3_DIR="${SAM3_CACHE_DIR:-/root/.cache/sam3}"

echo "=== HuggingFace 로그인 확인 ==="
hf auth whoami || { echo "먼저 'hf auth login' 으로 로그인하세요."; exit 1; }

echo ""
echo "=== SAM3.1 체크포인트 다운로드 ==="
echo "(facebook/sam3.1 접근 권한이 승인되어 있어야 합니다)"
mkdir -p "$SAM3_DIR"
hf download facebook/sam3.1 \
    --local-dir "$SAM3_DIR" \
    --include "*.pt" "config.json"

echo ""
echo "=== AnyDoor 체크포인트 다운로드 ==="
mkdir -p "$ANYDOOR_DIR"
hf download xichenhku/AnyDoor \
    --local-dir "$ANYDOOR_DIR" \
    --include "*.ckpt" "*.yaml" "*.pt"

echo ""
echo "=== 다운로드 완료 ==="
echo "  SAM3.1: $SAM3_DIR"
echo "  AnyDoor: $ANYDOOR_DIR"
