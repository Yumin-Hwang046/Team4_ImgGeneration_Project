# DB Schema Guide

Team4_BE 프로젝트의 주요 DB 테이블과 컬럼 목적을 정리한 문서입니다.  
현재 `backend/models.py`와 실제 generation 처리 흐름을 기준으로 작성했습니다.

---

# 태그 기준

- `[PK]` 기본키
- `[FK]` 외래키
- `[INPUT]` 사용자 입력값
- `[PROFILE]` 회원/가게 기본정보
- `[DERIVED]` 시스템이 계산·보정한 값
- `[RESULT]` 생성 결과
- `[MEDIA]` 이미지/파일 경로
- `[STATUS]` 상태값
- `[CACHE]` 캐시/재조회 방지용 데이터
- `[ANALYTICS]` 상권/분석 데이터
- `[SCHEDULE]` 예약/일정 데이터
- `[LOG]` 로그/디버그/추적 데이터
- `[SECURITY]` 인증/권한 관련
- `[OPS]` 생성·수정 시각 등 운영 공통 컬럼

---

# 1. users

회원 계정 기본 테이블입니다.  
로그인, 권한, 활성 여부를 관리하며 `user_profiles`, `generations`, `upload_schedules`와 연결됩니다.

| 컬럼명 | 태그 | 설명 |
|---|---|---|
| id | `[PK]` | 회원 식별자 |
| email | `[INPUT] [SECURITY]` | 로그인 이메일, 유니크 |
| password_hash | `[SECURITY]` | 암호화된 비밀번호 |
| name | `[INPUT] [PROFILE]` | 회원 이름 |
| role | `[SECURITY] [STATUS]` | 권한 구분 (`user` 등) |
| is_active | `[STATUS] [SECURITY]` | 계정 활성 여부 |
| created_at | `[OPS]` | 생성 시각 |
| updated_at | `[OPS]` | 수정 시각 |

---

# 2. user_profiles

회원의 가게 프로필 테이블입니다.  
가게명, 업종, 주소, 좌표, 기본 무드 등을 저장하며 generation/날씨/상권분석의 기준 정보로 사용됩니다.

| 컬럼명 | 태그 | 설명 |
|---|---|---|
| id | `[PK]` | 프로필 식별자 |
| user_id | `[FK] [PROFILE]` | 회원 연결 키, 1:1 |
| store_name | `[INPUT] [PROFILE]` | 가게명 |
| business_category | `[INPUT] [PROFILE]` | 업종 카테고리 |
| road_address | `[INPUT] [PROFILE]` | 도로명 주소 |
| jibun_address | `[INPUT] [PROFILE]` | 지번 주소 |
| detail_address | `[INPUT] [PROFILE]` | 상세 주소 |
| zipcode | `[INPUT] [PROFILE]` | 우편번호 |
| sido | `[DERIVED] [PROFILE]` | 시/도 |
| sigungu | `[DERIVED] [PROFILE]` | 시/군/구 |
| emd | `[DERIVED] [PROFILE]` | 읍/면/동 |
| legal_code | `[DERIVED] [PROFILE]` | 법정동 코드 |
| latitude | `[DERIVED] [PROFILE]` | 위도 |
| longitude | `[DERIVED] [PROFILE]` | 경도 |
| default_mood | `[PROFILE]` | 기본 무드 |
| created_at | `[OPS]` | 생성 시각 |
| updated_at | `[OPS]` | 수정 시각 |

> 참고: generation 과정에서 입력 location 값이 부정확하거나 비어 있으면, 사용자 프로필 주소 정보가 보정값으로 활용될 수 있습니다.

---

# 3. generations

이미지/문구 생성 작업의 핵심 테이블입니다.  
입력값, 추천 컨셉, 날씨 요약, 생성 문구, 대표 이미지, 상태 등을 한 건 단위로 저장합니다.

| 컬럼명 | 태그 | 설명 |
|---|---|---|
| id | `[PK]` | 생성건 식별자 |
| user_id | `[FK]` | 생성 요청 사용자 |
| purpose | `[INPUT]` | 홍보 목적 |
| business_category | `[INPUT]` | 업종 |
| menu_name | `[INPUT]` | 메뉴/상품명 |
| mood | `[INPUT]` | 선택 무드 |
| location | `[INPUT] [DERIVED]` | 사용자 입력 또는 보정된 지역 |
| target_datetime | `[INPUT] [SCHEDULE]` | 목표 날짜/시간 |
| extra_info | `[LOG]` | 업로드 여부, 사용자 추가 요청, 에러 로그 등 |
| generated_copy | `[RESULT]` | 생성된 홍보 문구 |
| hashtags | `[RESULT]` | 생성된 해시태그(JSON 문자열 저장) |
| weather_summary | `[DERIVED] [CACHE]` | 날씨 요약 |
| recommended_concept | `[DERIVED]` | 추천 컨셉 |
| original_image_url | `[MEDIA]` | 업로드 원본 이미지 URL |
| generated_image_url | `[MEDIA] [RESULT]` | 대표 생성 이미지 URL |
| image_mode | `[STATUS]` | 이미지 생성 방식 (`generated`, `uploaded_and_analyzed` 등) |
| generation_status | `[STATUS]` | 생성 상태 (`PENDING`, `SUCCESS`, `FAILED`) |
| created_at | `[OPS]` | 생성 시각 |
| updated_at | `[OPS]` | 수정 시각 |

> 참고: 실제 generation 흐름에서는 이 테이블에 입력값과 결과값이 함께 저장됩니다.

---

# 4. generated_images

generation 결과 이미지의 버전 이력을 관리하는 테이블입니다.  
재생성 시 버전 번호를 올리면서 여러 이미지를 저장합니다.

| 컬럼명 | 태그 | 설명 |
|---|---|---|
| id | `[PK]` | 생성 이미지 식별자 |
| generation_id | `[FK]` | 연결된 generation |
| image_url | `[MEDIA] [RESULT]` | 생성 이미지 URL |
| final_image_url | `[MEDIA] [RESULT]` | 후처리/최종 이미지 URL |
| prompt_used | `[LOG] [DERIVED]` | 이미지 생성에 사용된 프롬프트 |
| version_no | `[OPS] [RESULT]` | 버전 번호 |
| image_type | `[STATUS]` | 이미지 유형 (`generated` 등) |
| status | `[STATUS]` | 이미지 상태 |
| created_at | `[OPS]` | 생성 시각 |
| updated_at | `[OPS]` | 수정 시각 |

> 참고: 같은 generation에 여러 이미지 버전이 연결될 수 있습니다.

---

# 5. calendar_events

외부 행사/캘린더 데이터를 저장하는 테이블입니다.  
캘린더 표시, 지역 행사 추천, 외부 일정 연동에 활용할 수 있습니다.

| 컬럼명 | 태그 | 설명 |
|---|---|---|
| id | `[PK]` | 행사 식별자 |
| event_date | `[SCHEDULE]` | 캘린더 표시 날짜 |
| title | `[INPUT]` | 행사명 |
| event_type | `[STATUS]` | 행사 유형 |
| location | `[INPUT]` | 행사 지역 |
| description | `[INPUT]` | 행사 설명 |
| external_id | `[DERIVED]` | 외부 시스템 행사 ID |
| event_start_date | `[SCHEDULE]` | 행사 시작일 |
| event_end_date | `[SCHEDULE]` | 행사 종료일 |
| source_name | `[LOG]` | 데이터 출처명 |
| source_url | `[LOG]` | 원문 링크 |
| road_address | `[DERIVED]` | 도로명 주소 |
| jibun_address | `[DERIVED]` | 지번 주소 |
| legal_code | `[DERIVED]` | 법정동 코드 |
| latitude | `[DERIVED]` | 위도 |
| longitude | `[DERIVED]` | 경도 |
| is_auto_collected | `[STATUS]` | 자동 수집 여부 |
| last_synced_at | `[OPS]` | 마지막 동기화 시각 |
| created_at | `[OPS]` | 생성 시각 |
| updated_at | `[OPS]` | 수정 시각 |

---

# 6. upload_schedules

생성 결과를 예약 업로드하기 위한 테이블입니다.  
사용자, generation, 예약 시각, 채널, 상태를 연결합니다.

| 컬럼명 | 태그 | 설명 |
|---|---|---|
| id | `[PK]` | 예약 식별자 |
| user_id | `[FK]` | 사용자 연결 |
| generation_id | `[FK]` | generation 연결 |
| scheduled_at | `[SCHEDULE]` | 예약 업로드 시각 |
| channel | `[SCHEDULE] [INPUT]` | 업로드 채널 |
| status | `[STATUS]` | 예약 상태 (`PENDING` 등) |
| created_at | `[OPS]` | 생성 시각 |
| updated_at | `[OPS]` | 수정 시각 |

---

# 7. region_analytics

상권 분석 결과를 저장하는 테이블입니다.  
프로필 주소 기준의 지역 분석, 유동인구, 경쟁업체 수, 주변 업종 분포 등을 보관합니다.

| 컬럼명 | 태그 | 설명 |
|---|---|---|
| id | `[PK]` | 상권분석 식별자 |
| user_profile_id | `[FK]` | 프로필 연결 |
| analysis_date | `[ANALYTICS]` | 분석 기준일 |
| region_name | `[ANALYTICS]` | 분석 지역명 |
| legal_code | `[DERIVED]` | 법정동 코드 |
| floating_population | `[ANALYTICS]` | 유동인구 |
| competitor_count | `[ANALYTICS]` | 경쟁업체 수 |
| top_categories_json | `[ANALYTICS] [CACHE]` | 주변 업종 분포 JSON |
| summary_text | `[ANALYTICS] [RESULT]` | 분석 요약문 |
| source_name | `[LOG]` | 데이터 출처 |
| raw_payload | `[LOG] [CACHE]` | 원본 응답 JSON |
| created_at | `[OPS]` | 생성 시각 |
| updated_at | `[OPS]` | 수정 시각 |

---

# 8. scheduler_job_logs

스케줄러/배치 작업 실행 로그 테이블입니다.  
운영 모니터링, 실패 추적, 처리 건수 확인 등에 사용합니다.

| 컬럼명 | 태그 | 설명 |
|---|---|---|
| id | `[PK]` | 로그 식별자 |
| job_name | `[LOG]` | 작업명 |
| job_type | `[LOG]` | 작업 유형 |
| target_region | `[LOG]` | 대상 지역 |
| run_started_at | `[LOG] [OPS]` | 실행 시작 시각 |
| run_finished_at | `[LOG] [OPS]` | 실행 종료 시각 |
| status | `[STATUS] [LOG]` | 실행 상태 |
| processed_count | `[LOG]` | 처리 건수 |
| error_message | `[LOG]` | 에러 메시지 |
| created_at | `[OPS]` | 로그 생성 시각 |

---

# 9. weather_daily

사용자 프로필 기준의 일별 날씨 캐시 테이블입니다.  
generation 시 날씨 요약을 바로 쓰기 위한 캐시성 데이터로 활용됩니다.

| 컬럼명 | 태그 | 설명 |
|---|---|---|
| id | `[PK]` | 날씨 식별자 |
| user_profile_id | `[FK]` | 프로필 연결 |
| weather_date | `[CACHE]` | 기준 날짜 |
| region_name | `[CACHE]` | 지역명 |
| legal_code | `[DERIVED]` | 법정동 코드 |
| latitude | `[DERIVED]` | 위도 |
| longitude | `[DERIVED]` | 경도 |
| weather_code | `[CACHE]` | 날씨 코드 |
| weather_summary | `[CACHE] [RESULT]` | 날씨 요약 |
| temp_min | `[CACHE]` | 최저기온 |
| temp_max | `[CACHE]` | 최고기온 |
| precipitation_probability | `[CACHE]` | 강수확률 |
| forecast_type | `[STATUS]` | 예보 유형 |
| source_name | `[LOG]` | 데이터 출처 |
| fetched_at | `[OPS]` | 수집 시각 |
| created_at | `[OPS]` | 생성 시각 |
| updated_at | `[OPS]` | 수정 시각 |

> 참고: generation 로직에서는 저장된 날씨(`weather_daily`)를 먼저 조회하고, 없을 때만 외부 날씨 API 조회 및 계절 fallback을 사용합니다.

---

# 운영 기준 요약

## 핵심 운영 테이블
- `users`
- `user_profiles`
- `generations`
- `generated_images`
- `weather_daily`
- `upload_schedules`

## 보조 기능 테이블
- `calendar_events`
- `region_analytics`

## 로그/정리 우선 테이블
- `scheduler_job_logs`
- `generations.extra_info`
- `generated_images.prompt_used`
- `region_analytics.raw_payload`

---

# 운영 시 주의사항

1. `generations.hashtags`는 현재 JSON 문자열 형태로 저장됩니다.  
   프론트에서는 배열처럼 사용되므로 조회 시 JSON 파싱이 필요합니다.

2. `generations.extra_info`는 디버그/실험 정보가 누적되기 쉬운 필드입니다.  
   운영 단계에서는 길이와 사용 목적을 명확히 관리하는 것이 좋습니다.

3. `generated_images`는 generation 1건에 여러 버전이 연결될 수 있습니다.

4. `weather_daily`는 프로필 기반 날씨 캐시이므로, 같은 `user_profile_id + weather_date` 중복 여부를 주기적으로 점검하는 것이 좋습니다.

5. `scheduler_job_logs`는 운영 로그 성격이 강하므로 보관 주기(예: 30일)를 두고 정리하는 것이 좋습니다.