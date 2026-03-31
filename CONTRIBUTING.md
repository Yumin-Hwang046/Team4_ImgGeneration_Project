# 🤝 Contributing Guide

## 브랜치 전략

```
main                    ← 최종 배포 브랜치 (직접 push 금지)
dev                     ← 통합 개발 브랜치 (PR로만 merge)
feature/model           ← 모델 개발 (4/1 ~ 4/6)
feature/serving         ← 서빙 (4/6 ~ 4/9)
feature/service         ← 서비스 (4/9 ~ 4/12)
fix/버그명               ← 버그 수정
```

### 브랜치 이름 규칙
- 기본: `feature/단계명-#이슈번호` (예: `feature/model-#1`)
- 같은 이슈를 여러 명이 작업할 경우 이름 접미사 추가:
  `feature/단계명-#이슈번호-이름` (예: `feature/model-#1-슬기`)

## PR 규칙
- `dev` 브랜치로 PR 생성
- 최소 1명 팀원 리뷰 후 merge
- PR 제목 형식: `[feat] 기능 설명` / `[fix] 버그 설명`

## 커밋 메시지 규칙

| 태그 | 설명 |
|------|------|
| `feat` | 새 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 수정 |
| `refactor` | 코드 리팩토링 |
| `test` | 테스트 추가/수정 |

**예시:**
```
feat: 이미지 분석 API 연동
fix: 파일 업로드 오류 수정
docs: README 타임라인 업데이트
```
