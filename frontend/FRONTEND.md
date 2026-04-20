# Frontend Documentation

## 목차

1. [기술 스택](#기술-스택)
2. [디렉토리 구조](#디렉토리-구조)
3. [사용자 흐름 (파이프라인)](#사용자-흐름-파이프라인)
4. [페이지별 상세](#페이지별-상세)
5. [API 연동](#api-연동)
6. [디자인 시스템](#디자인-시스템)
7. [공통 컴포넌트](#공통-컴포넌트)
8. [환경 변수](#환경-변수)
9. [개발 실행](#개발-실행)

---

## 기술 스택

| 항목 | 버전 / 내용 |
|------|-------------|
| Framework | Next.js 14.2.29 (App Router) |
| Language | TypeScript 5 |
| Styling | Tailwind CSS 3.4.1 |
| Runtime | React 18 |
| Fonts | Instrument Serif, Be Vietnam Pro, Manrope, Lobster |
| Icons | Google Material Symbols Outlined |
| 이미지 | Unsplash CDN (`images.unsplash.com`) + picsum.photos (fallback) |

---

## 디렉토리 구조

```
frontend/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # 루트 레이아웃 (폰트, Material Symbols 로드)
│   ├── page.tsx                  # 랜딩 페이지 (/)
│   ├── globals.css               # 전역 CSS (커스텀 유틸리티 클래스)
│   │
│   ├── api/[...path]/route.ts    # 백엔드 프록시 (catch-all)
│   │
│   ├── auth/
│   │   ├── login/page.tsx        # 로그인
│   │   └── signup/page.tsx       # 회원가입
│   │
│   ├── onboarding/
│   │   ├── confirm/page.tsx      # 매장 정보 확인
│   │   ├── analysis/page.tsx     # Instagram 분석 중 (자동 리다이렉트)
│   │   ├── report/page.tsx       # 분석 리포트 + AI 추천 페르소나 4종
│   │   └── personas/page.tsx     # 페르소나 선택 (4종)
│   │
│   ├── dashboard/page.tsx        # 워크스페이스 홈
│   ├── studio/page.tsx           # 이미지 생성 페이지
│   ├── generating/page.tsx       # 생성 중 로딩 (자동 리다이렉트)
│   ├── archive/page.tsx          # 보관함
│   └── calendar/page.tsx         # 마케팅 캘린더
│
├── components/
│   └── SideBar.tsx               # 공통 사이드바
│
├── lib/
│   └── api.ts                    # API 클라이언트 (fetch wrapper)
│
├── public/                       # 정적 파일
├── .env.local                    # 환경 변수 (git 제외)
├── next.config.mjs               # Next.js 설정 (이미지 도메인 허용 목록)
├── tailwind.config.ts            # 디자인 토큰 정의
└── tsconfig.json
```

---

## 사용자 흐름 (파이프라인)

```
[랜딩 /]
    │
    ├─ 로그인 → /auth/login
    │               │
    │               └─→ /dashboard (로그인 성공)
    │
    └─ 시작하기 → /auth/signup
                    │
                    └─→ /onboarding/confirm  (매장 정보 입력 완료)
                                │
                                └─→ /onboarding/analysis  (4초 후 자동 이동)
                                            │
                                            └─→ /onboarding/report  (분석 결과 + 페르소나 4종 추천)
                                                        │
                                                        ├─→ /onboarding/personas  (전체 페르소나 4종)
                                                        │               │
                                                        │               └─→ /dashboard
                                                        └─→ /dashboard  (선택하기 직접)


[메인 앱 - SideBar 공통]
    ├─ 워크스페이스  /dashboard
    │       └─→ 제작하기 버튼 → /studio
    │
    ├─ 생성하기  /studio
    │       └─→ 생성하기 버튼 → /generating
    │                               │
    │                               └─→ /studio  (5초 후 자동 이동)
    │
    ├─ 보관함  /archive
    │       ├─ 전체 탭  (검색, 이미지 그리드)
    │       ├─ 날짜별 탭  (연도/월 폴더 → 폴더 진입)
    │       └─ 행사별 탭  (폴더 관리, 새 폴더 생성 → 폴더 진입)
    │
    ├─ 캘린더  /calendar
    │       ├─ 월간 뷰
    │       ├─ 주간 뷰
    │       └─ 리스트 뷰
    │
    └─ 설정  /settings
```

---

## 페이지별 상세

### `/` — 랜딩 페이지

- **레이아웃**: 상단 네비바 + 좌우 분할 히어로 섹션 + 푸터
- **주요 요소**
  - 헤드라인: _"당신의 브랜드를 빛내는 AI 마케팅 파트너"_
  - CTA: "무료로 시작하기" → `/auth/signup`, "로그인" → `/auth/login`
- **상태**: 정적 (Server Component)

---

### `/auth/login` — 로그인

- 이메일 + 비밀번호 입력 폼
- Instagram OAuth 버튼 (그라디언트)
- 링크: 회원가입 → `/auth/signup`

---

### `/auth/signup` — 회원가입

- **입력 필드**: 매장명, 카테고리(셀렉트), 위치 검색, Instagram 연동
- **플로우**: 완료 시 → `/onboarding/confirm`

---

### `/onboarding/confirm` — 매장 정보 확인

- 입력된 위치·카테고리 정보 카드 표시
- "분석 시작" CTA → `/onboarding/analysis`

---

### `/onboarding/analysis` — 분석 중

- **'use client'** — `useEffect`로 4000ms 후 `/onboarding/report` 자동 리다이렉트
- 스피닝 애니메이션 + "Instagram 분석 중" 텍스트

---

### `/onboarding/report` — 분석 리포트

- 인구통계 벤토 그리드 (연령대 바 차트, 성별 비율)
- **AI 추천 브랜드 페르소나 4종** (`sm:grid-cols-2 lg:grid-cols-4`)
  - Unsplash 이미지 + 그라디언트 오버레이
  - 선택하기 버튼 → `/dashboard`
- "더보기" → `/onboarding/personas`

---

### `/onboarding/personas` — 페르소나 라이브러리

- **4종 페르소나** 카드 그리드 (`xl:grid-cols-4`)

| 페르소나 | 태그 | 이미지 분위기 |
|----------|------|--------------|
| Warm | 따뜻한 | 커피·카페 따뜻한 톤 |
| Clean | 깔끔한 | 미니멀 인테리어 |
| Trendy | 트렌디 | 패션·도시 감성 |
| Premium | 프리미엄 | 고급 럭셔리 공간 |

- 각 카드: Unsplash 이미지 + 그라디언트 + 태그 뱃지 + "선택하기" → `/dashboard`

---

### `/dashboard` — 워크스페이스

- **SideBar** 포함
- **히어로 배너**: 다크 무드 카페 배경 + Instagram 그라디언트 텍스트 + "지금 바로 제작하기" CTA
- **최근 생성 콘텐츠**: 4열 그리드, hover 시 줌 효과
- "View Archive" 링크 → `/archive`

---

### `/studio` — 이미지 생성

- **'use client'** — 3단계 입력 구성

| 단계 | 내용 |
|------|------|
| 1 | 이미지 업로드 (클릭, `useRef` 파일 입력) |
| 2 | 무드/날씨 선택 (4종 — CSS 그라디언트 + Material Icon) |
| 3 | 카피라이팅 프롬프트 텍스트에어리어 |

**날씨 옵션 상세** (외부 이미지 없이 CSS로 구현):

| ID | 레이블 | 그라디언트 | 아이콘 |
|----|--------|-----------|--------|
| `sunny` | 맑은 날씨 | sky→yellow→amber | `wb_sunny` |
| `cloudy` | 흐린 날씨 | slate→gray | `cloud` |
| `rainy` | 비 오는 배경 | slate-dark→blue | `rainy` |
| `warm` | 따뜻한 조명 | amber→orange→yellow | `light_mode` |

- **Live Preview 패널** (우측 sticky)
  - 피드 탭: Instagram 피드 카드 목업
  - 스토리 탭: 9:16 세로 스토리 목업
  - 업로드 이미지 실시간 미리보기 반영
- "생성하기" 버튼 → `/generating`

---

### `/generating` — 생성 중

- **'use client'** — `useEffect`로 5000ms 후 `/studio` 자동 리다이렉트
- `progress-pulse` 애니메이션 바

---

### `/archive` — 보관함

- **'use client'**, 3탭 구성

#### 전체 탭
- 4열 이미지 그리드 (hover: 그레이스케일 해제 + 줌 + 위로 이동)
- **검색**: 헤더 검색 버튼 → 슬라이드 다운 검색창, 제목 실시간 필터링
- FAB (+) → `/studio`

#### 날짜별 탭
- 연도 네비게이터 (현재 연도 기준 초기화, ← 연도 →)
- **GRID VIEW**: 12개월 폴더 카드 (월별 사진 배경) → 클릭 시 폴더 진입
- **LIST VIEW**: 월 목록 + 개수 → 클릭 시 폴더 진입
- **폴더 내부**: 파일 없을 시 `folder_open` 아이콘 + "파일이 없습니다" 빈 상태 표시
- 뒤로가기 버튼으로 목록 복귀

#### 행사별 탭
- 폴더 카드 그리드 (기념일, 데일리, 축제 및 행사) → 클릭 시 폴더 진입
- **추가하기 / 새 폴더** 버튼 → 모달 팝업 (이름 입력)
- **폴더 내부**: 파일 없을 시 빈 상태 표시, 뒤로가기 복귀
- 통계 벤토: 최근 아카이브 이미지 3장 + Storage 용량 카드

---

### `/calendar` — 마케팅 캘린더

- **'use client'**, 3뷰 + 이벤트 CRUD

#### 이벤트 태그 및 색상

| 태그 | 색상 | 설명 |
|------|------|------|
| `예약` | 파란색 (blue) | 예정된 포스팅 |
| `행사` | 빨간색 (red) | 이벤트·행사 |
| `완료` | 회색 (stone) | 완료된 일정 |
| `기타` | 황금색 (amber) | 기타 일정 |

> **자동 완료 처리**: 오늘 이전 날짜의 이벤트는 태그에 관계없이 완료(회색) 색상으로 렌더링

#### 이벤트 추가/수정 모달
- **날짜 셀 클릭** → 해당 날짜로 일정 추가 모달 오픈
- **이벤트 칩 클릭** → 수정 모달 (제목·시간·태그 변경 + 삭제 버튼)
- Enter 키 저장, 배경 클릭 닫기

#### 커스텀 TimePicker
- `오전/오후` 클릭 → 드롭다운 선택
- 시간 숫자 직접 타이핑 (1–12)
- `시` 레이블 클릭 → 1–12 드롭다운
- 분 숫자 직접 타이핑 (0–59)
- `분` 레이블 클릭 → 5분 단위(00–55) 드롭다운

#### 월간 뷰
- 7열 날짜 그리드, 셀 최소 높이 90px
- 날짜 숫자 원형 배지 (오늘: primary 색상)
- 이벤트 칩: border-left 컬러 코딩

#### 주간 뷰
- 현재 주의 7일 컬럼, 빈 셀 클릭 시 일정 추가

#### 리스트 뷰
- 이달 이벤트 타임라인 (날짜 + 시간 + 태그)
- "새 포스팅 예약" 버튼 → 오늘 날짜로 추가 모달

**상단 위젯**
- 날씨 카드: 성수동 기온/강수확률/습도
- AI Curator Tip: 날씨 기반 포스팅 추천 메시지

---

## API 연동

### 프록시 구조

```
브라우저 → Next.js /api/* → 백엔드 서버 (BACKEND_URL)
```

`app/api/[...path]/route.ts`가 모든 `/api/**` 요청을 백엔드로 전달합니다.  
`host` 헤더를 제외한 모든 헤더가 그대로 전달됩니다.

### API 클라이언트 (`lib/api.ts`)

```typescript
// 이미지 생성 요청
api.generateImage({
  prompt: string,
  style?: string,
  type?: 'feed' | 'story',
  referenceImage?: string,   // base64 or URL
})
// → POST /api/generate
// ← { imageUrl, caption, processId }

// 생성 상태 폴링
api.getGenerationStatus(processId)
// → GET /api/generate/:processId/status
// ← { status, progress, imageUrl? }
```

---

## 디자인 시스템

### 색상 토큰 (`tailwind.config.ts`)

| 토큰 | HEX | 용도 |
|------|-----|------|
| `primary` | `#296678` | 메인 강조색 |
| `primary-container` | `#6ba4b8` | 버튼, 배지 배경 |
| `surface` | `#fbf9f6` | 페이지 배경 |
| `surface-container-low` | `#f5f3f0` | 카드 배경 (낮은 단계) |
| `surface-container-lowest` | `#ffffff` | 카드 배경 (최저) |
| `on-surface` | `#1b1c1a` | 본문 텍스트 |
| `on-surface-variant` | `#40484b` | 보조 텍스트 |
| `tertiary` | `#84532a` | AI Tip 등 강조 |
| `error` | `#ba1a1a` | 일요일, 오류 상태 |

### 커스텀 CSS 유틸리티 (`globals.css`)

```css
.cta-gradient       /* 135deg #296678 → #6ba4b8 CTA 버튼 */
.instagram-gradient /* Instagram 브랜드 그라디언트 */
.glass-card         /* 반투명 유리 카드 (backdrop-blur) */
.progress-pulse     /* 생성 중 진행 바 애니메이션 */
.active-tab         /* 활성 탭 언더라인 스타일 */
```

### 폰트

| 클래스 | 폰트 | 용도 |
|--------|------|------|
| `font-headline` | Instrument Serif (이탤릭) | 제목, 헤드라인 |
| `font-body` | Be Vietnam Pro | 본문 |
| `font-manrope` | Manrope | 숫자, 강조 레이블 |
| (인스타) | Lobster | Instagram 텍스트 |

### 이미지 도메인 허용 목록 (`next.config.mjs`)

`next/image` 컴포넌트 사용 시 허용된 외부 도메인:

```
lh3.googleusercontent.com  — Google OAuth 프로필 이미지
images.unsplash.com         — 페르소나·데모 이미지
picsum.photos               — 플레이스홀더 이미지
fastly.picsum.photos        — picsum CDN
```

---

## 공통 컴포넌트

### `components/SideBar.tsx`

- **'use client'** — `usePathname()`으로 현재 경로 감지 → 활성 메뉴 하이라이트
- **상단 로고**: "The Digital Curator" 클릭 → `/dashboard`
- **네비게이션 항목**

| 아이콘 | 레이블 | 경로 |
|--------|--------|------|
| `grid_view` | 워크스페이스 | `/dashboard` |
| `auto_awesome` | 생성하기 | `/studio` |
| `auto_awesome_motion` | 보관함 | `/archive` |
| `calendar_today` | 캘린더 | `/calendar` |

- **하단**: 설정(`/settings`), 사용자 프로필 영역

---

## 환경 변수

`.env.local` (프로젝트 루트에 생성 필요)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000   # 브라우저 → 백엔드 직접 호출용
BACKEND_URL=http://localhost:8000           # 서버사이드 프록시용
```

---

## 개발 실행

```bash
# 의존성 설치
npm install

# 개발 서버 (http://localhost:3000)
npm run dev

# 프로덕션 빌드
npm run build

# 빌드 결과 실행
npm start
```

### 현재 빌드 라우트

```
/                       정적
/auth/login             정적
/auth/signup            정적
/onboarding/confirm     정적
/onboarding/analysis    정적
/onboarding/report      정적
/onboarding/personas    정적
/dashboard              정적
/studio                 클라이언트
/generating             클라이언트
/archive                클라이언트
/calendar               클라이언트
/api/[...path]          동적 (프록시)
```
