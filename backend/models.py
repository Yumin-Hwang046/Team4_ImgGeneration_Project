from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, func, DECIMAL
from sqlalchemy.orm import relationship
from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # OAuth 유저는 NULL
    name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    is_active = Column(Integer, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Instagram / Meta OAuth
    instagram_user_id = Column(String(100), unique=True, nullable=True, index=True)
    instagram_account_id = Column(String(100), nullable=True)
    instagram_username = Column(String(100), nullable=True)
    instagram_access_token = Column(String(500), nullable=True)

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

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    store_name = Column(String(255), nullable=False)
    business_category = Column(String(100), nullable=False)
    road_address = Column(String(255), nullable=False)
    jibun_address = Column(String(255), nullable=True)
    detail_address = Column(String(255), nullable=True)
    zipcode = Column(String(20), nullable=True)
    sido = Column(String(100), nullable=True)
    sigungu = Column(String(100), nullable=True)
    emd = Column(String(100), nullable=True)
    legal_code = Column(String(20), nullable=True)
    latitude = Column(DECIMAL(10, 7), nullable=True)
    longitude = Column(DECIMAL(10, 7), nullable=True)
    default_mood = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

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

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    purpose = Column(String(50), nullable=True)
    business_category = Column(String(100), nullable=True)
    menu_name = Column(String(255), nullable=True)
    mood = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    target_datetime = Column(DateTime, nullable=True)

    extra_info = Column(Text, nullable=True)
    generated_copy = Column(Text, nullable=True)
    hashtags = Column(Text, nullable=True)

    weather_summary = Column(String(255), nullable=True)
    recommended_concept = Column(String(255), nullable=True)

    original_image_url = Column(String(500), nullable=True)
    generated_image_url = Column(String(500), nullable=True)
    image_mode = Column(String(50), nullable=True)
    generation_status = Column(String(50), nullable=False, default="SUCCESS")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

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

    id = Column(Integer, primary_key=True, index=True)
    generation_id = Column(Integer, ForeignKey("generations.id", ondelete="CASCADE"), nullable=False)

    image_url = Column(String(500), nullable=False)
    final_image_url = Column(String(500), nullable=True)
    prompt_used = Column(Text, nullable=True)
    version_no = Column(Integer, nullable=False, default=1)
    image_type = Column(String(50), nullable=False, default="generated")
    status = Column(String(50), nullable=False, default="SUCCESS")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    generation = relationship("Generation", back_populates="generated_images")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    event_date = Column(Date, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    event_type = Column(String(50), nullable=False)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    external_id = Column(String(100), nullable=True)
    event_start_date = Column(Date, nullable=True)
    event_end_date = Column(Date, nullable=True)
    source_name = Column(String(100), nullable=True)
    source_url = Column(String(500), nullable=True)
    road_address = Column(String(255), nullable=True)
    jibun_address = Column(String(255), nullable=True)
    legal_code = Column(String(20), nullable=True)
    latitude = Column(DECIMAL(10, 7), nullable=True)
    longitude = Column(DECIMAL(10, 7), nullable=True)
    is_auto_collected = Column(Integer, nullable=False, default=0)
    last_synced_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UploadSchedule(Base):
    __tablename__ = "upload_schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    generation_id = Column(Integer, ForeignKey("generations.id", ondelete="CASCADE"), nullable=False)

    scheduled_at = Column(DateTime, nullable=False, index=True)
    channel = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="upload_schedules")
    generation = relationship("Generation", back_populates="upload_schedules")


class RegionAnalytics(Base):
    __tablename__ = "region_analytics"

    id = Column(Integer, primary_key=True, index=True)
    user_profile_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    analysis_date = Column(Date, nullable=False)
    region_name = Column(String(255), nullable=False)
    legal_code = Column(String(20), nullable=True)
    floating_population = Column(Integer, nullable=True)
    competitor_count = Column(Integer, nullable=True)
    top_categories_json = Column(Text, nullable=True)
    summary_text = Column(Text, nullable=True)
    source_name = Column(String(100), nullable=True)
    raw_payload = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user_profile = relationship("UserProfile", back_populates="region_analytics")


class SchedulerJobLog(Base):
    __tablename__ = "scheduler_job_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(100), nullable=False)
    job_type = Column(String(50), nullable=False)
    target_region = Column(String(255), nullable=True)
    run_started_at = Column(DateTime, nullable=False)
    run_finished_at = Column(DateTime, nullable=True)
    status = Column(String(30), nullable=False)
    processed_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class WeatherDaily(Base):
    __tablename__ = "weather_daily"

    id = Column(Integer, primary_key=True, index=True)
    user_profile_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    weather_date = Column(Date, nullable=False, index=True)
    region_name = Column(String(255), nullable=False)
    legal_code = Column(String(20), nullable=True)
    latitude = Column(DECIMAL(10, 7), nullable=True)
    longitude = Column(DECIMAL(10, 7), nullable=True)
    weather_code = Column(Integer, nullable=True)
    weather_summary = Column(String(255), nullable=True)
    temp_min = Column(DECIMAL(5, 2), nullable=True)
    temp_max = Column(DECIMAL(5, 2), nullable=True)
    precipitation_probability = Column(DECIMAL(5, 2), nullable=True)
    forecast_type = Column(String(30), nullable=False, default="forecast")
    source_name = Column(String(100), nullable=True)
    fetched_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user_profile = relationship("UserProfile", back_populates="weather_daily")
