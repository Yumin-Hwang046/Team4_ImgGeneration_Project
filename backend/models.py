from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, func, DECIMAL
from sqlalchemy.orm import relationship
from backend.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)  # #회원ID
    email = Column(String(255), unique=True, nullable=False, index=True)  # #로그인이메일
    password_hash = Column(String(255), nullable=False)  # #암호화비밀번호
    name = Column(String(100), nullable=False)  # #회원이름
    role = Column(String(50), nullable=False, default="user")  # #권한
    is_active = Column(Integer, nullable=False, default=True)  # #활성여부
    created_at = Column(DateTime, server_default=func.now())  # #생성일시
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # #수정일시

    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    generations = relationship("Generation", back_populates="user")
    upload_schedules = relationship(
        "UploadSchedule",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)  # #프로필ID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)  # #회원ID
    store_name = Column(String(255), nullable=False)  # #가게명
    business_category = Column(String(100), nullable=False)  # #업종
    road_address = Column(String(255), nullable=False)  # #기본주소_도로명
    jibun_address = Column(String(255), nullable=True)  # #지번주소
    detail_address = Column(String(255), nullable=True)  # #상세주소
    zipcode = Column(String(20), nullable=True)  # #우편번호
    sido = Column(String(100), nullable=True)  # #시도
    sigungu = Column(String(100), nullable=True)  # #시군구
    emd = Column(String(100), nullable=True)  # #읍면동
    legal_code = Column(String(20), nullable=True)  # #법정동코드
    latitude = Column(DECIMAL(10, 7), nullable=True)  # #위도
    longitude = Column(DECIMAL(10, 7), nullable=True)  # #경도
    default_mood = Column(String(100), nullable=True)  # #기본무드
    created_at = Column(DateTime, server_default=func.now())  # #생성일시
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # #수정일시

    user = relationship("User", back_populates="profile")
    region_analytics = relationship(
        "RegionAnalytics",
        back_populates="user_profile",
        cascade="all, delete-orphan",
)
    weather_daily = relationship(
        "WeatherDaily",
        back_populates="user_profile",
        cascade="all, delete-orphan",
)
    

class Generation(Base):
    __tablename__ = "generations"

    id = Column(Integer, primary_key=True, index=True)  # #생성건ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # #회원ID

    purpose = Column(String(50), nullable=True)  # #홍보목적
    business_category = Column(String(100), nullable=True)  # #업종
    menu_name = Column(String(255), nullable=True)  # #메뉴명
    mood = Column(String(100), nullable=True)  # #무드
    location = Column(String(255), nullable=True)  # #지역
    target_datetime = Column(DateTime, nullable=True)  # #목표일시

    extra_info = Column(Text, nullable=True)  # #추가정보
    generated_copy = Column(Text, nullable=True)  # #생성문구
    hashtags = Column(Text, nullable=True)  # #해시태그

    weather_summary = Column(String(255), nullable=True)  # #날씨요약
    recommended_concept = Column(String(255), nullable=True)  # #추천컨셉

    original_image_url = Column(String(500), nullable=True)  # #원본이미지
    generated_image_url = Column(String(500), nullable=True)  # #생성이미지
    image_mode = Column(String(50), nullable=True)  # #이미지모드
    generation_status = Column(String(50), nullable=False, default="SUCCESS")  # #생성상태

    created_at = Column(DateTime, server_default=func.now())  # #생성일시
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # #수정일시

    user = relationship("User", back_populates="generations")
    generated_images = relationship(
        "GeneratedImage",
        back_populates="generation",
        cascade="all, delete-orphan",
    )
    upload_schedules = relationship(
        "UploadSchedule",
        back_populates="generation",
        cascade="all, delete-orphan",
    )


class GeneratedImage(Base):
    __tablename__ = "generated_images"

    id = Column(Integer, primary_key=True, index=True)  # #생성이미지ID
    generation_id = Column(Integer, ForeignKey("generations.id", ondelete="CASCADE"), nullable=False)  # #생성건ID

    image_url = Column(String(500), nullable=False)  # #이미지URL
    final_image_url = Column(String(500), nullable=True)  # #최종이미지URL
    prompt_used = Column(Text, nullable=True)  # #사용프롬프트
    version_no = Column(Integer, nullable=False, default=1)  # #버전번호
    image_type = Column(String(50), nullable=False, default="generated")  # #이미지유형
    status = Column(String(50), nullable=False, default="SUCCESS")  # #이미지상태

    created_at = Column(DateTime, server_default=func.now())  # #생성일시
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # #수정일시

    generation = relationship("Generation", back_populates="generated_images")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)  # #행사ID
    event_date = Column(Date, nullable=False, index=True)  # #캘린더표시날짜
    title = Column(String(255), nullable=False)  # #행사명
    event_type = Column(String(50), nullable=False)  # #행사유형
    location = Column(String(255), nullable=True)  # #행사지역
    description = Column(Text, nullable=True)  # #행사설명

    external_id = Column(String(100), nullable=True)  # #외부행사ID
    event_start_date = Column(Date, nullable=True)  # #행사시작일
    event_end_date = Column(Date, nullable=True)  # #행사종료일
    source_name = Column(String(100), nullable=True)  # #데이터출처
    source_url = Column(String(500), nullable=True)  # #원문링크
    road_address = Column(String(255), nullable=True)  # #도로명주소
    jibun_address = Column(String(255), nullable=True)  # #지번주소
    legal_code = Column(String(20), nullable=True)  # #법정동코드
    latitude = Column(DECIMAL(10, 7), nullable=True)  # #위도
    longitude = Column(DECIMAL(10, 7), nullable=True)  # #경도
    is_auto_collected = Column(Integer, nullable=False, default=0)  # #자동수집여부
    last_synced_at = Column(DateTime, nullable=True)  # #마지막동기화시각

    created_at = Column(DateTime, server_default=func.now())  # #생성일시
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # #수정일시일시


class UploadSchedule(Base):
    __tablename__ = "upload_schedules"

    id = Column(Integer, primary_key=True, index=True)  # #예약ID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # #회원ID
    generation_id = Column(Integer, ForeignKey("generations.id", ondelete="CASCADE"), nullable=False)  # #생성건ID

    scheduled_at = Column(DateTime, nullable=False, index=True)  # #예약업로드일시
    channel = Column(String(50), nullable=False)  # #업로드채널
    status = Column(String(50), nullable=False, default="PENDING")  # #예약상태

    created_at = Column(DateTime, server_default=func.now())  # #생성일시
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # #수정일시

    user = relationship("User", back_populates="upload_schedules")
    generation = relationship("Generation", back_populates="upload_schedules")


class RegionAnalytics(Base):
    __tablename__ = "region_analytics"

    id = Column(Integer, primary_key=True, index=True)  # #상권분석ID
    user_profile_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)  # #프로필ID
    analysis_date = Column(Date, nullable=False)  # #분석기준일
    region_name = Column(String(255), nullable=False)  # #분석지역명
    legal_code = Column(String(20), nullable=True)  # #법정동코드
    floating_population = Column(Integer, nullable=True)  # #유동인구
    competitor_count = Column(Integer, nullable=True)  # #경쟁업체수
    top_categories_json = Column(Text, nullable=True)  # #주변업종분포JSON
    summary_text = Column(Text, nullable=True)  # #분석요약문
    source_name = Column(String(100), nullable=True)  # #데이터출처
    raw_payload = Column(Text, nullable=True)  # #원본응답JSON
    created_at = Column(DateTime, server_default=func.now())  # #생성일시
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # #수정일시

    user_profile = relationship("UserProfile", back_populates="region_analytics")
    
class SchedulerJobLog(Base):
    __tablename__ = "scheduler_job_logs"

    id = Column(Integer, primary_key=True, index=True)  # #스케줄러로그ID
    job_name = Column(String(100), nullable=False)  # #작업명
    job_type = Column(String(50), nullable=False)  # #작업유형
    target_region = Column(String(255), nullable=True)  # #대상지역
    run_started_at = Column(DateTime, nullable=False)  # #실행시작시각
    run_finished_at = Column(DateTime, nullable=True)  # #실행종료시각
    status = Column(String(30), nullable=False)  # #실행상태
    processed_count = Column(Integer, nullable=False, default=0)  # #처리건수
    error_message = Column(Text, nullable=True)  # #에러메시지
    created_at = Column(DateTime, server_default=func.now())  # #로그생성일시
    
class WeatherDaily(Base):
    __tablename__ = "weather_daily"

    id = Column(Integer, primary_key=True, index=True)  # #날씨ID
    user_profile_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)  # #프로필ID
    weather_date = Column(Date, nullable=False, index=True)  # #날짜
    region_name = Column(String(255), nullable=False)  # #지역명
    legal_code = Column(String(20), nullable=True)  # #법정동코드
    latitude = Column(DECIMAL(10, 7), nullable=True)  # #위도
    longitude = Column(DECIMAL(10, 7), nullable=True)  # #경도
    weather_code = Column(Integer, nullable=True)  # #날씨코드
    weather_summary = Column(String(255), nullable=True)  # #날씨요약
    temp_min = Column(DECIMAL(5, 2), nullable=True)  # #최저기온
    temp_max = Column(DECIMAL(5, 2), nullable=True)  # #최고기온
    precipitation_probability = Column(DECIMAL(5, 2), nullable=True)  # #강수확률
    forecast_type = Column(String(30), nullable=False, default="forecast")  # #예보유형
    source_name = Column(String(100), nullable=True)  # #데이터출처
    fetched_at = Column(DateTime, server_default=func.now())  # #수집시각
    created_at = Column(DateTime, server_default=func.now())  # #생성일시
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # #수정일시

    user_profile = relationship("UserProfile", back_populates="weather_daily")