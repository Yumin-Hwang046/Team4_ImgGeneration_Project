from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, func
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
    instagram_account_id = Column(String(100), nullable=True)    # IG Business Account ID
    instagram_username = Column(String(100), nullable=True)      # @username
    instagram_access_token = Column(String(500), nullable=True)  # long-lived token

    generations = relationship("Generation", back_populates="user")
    upload_schedules = relationship("UploadSchedule", back_populates="user", cascade="all, delete-orphan")


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
    event_type = Column(String(50), nullable=False)  # holiday / festival / local_event
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UploadSchedule(Base):
    __tablename__ = "upload_schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    generation_id = Column(Integer, ForeignKey("generations.id", ondelete="CASCADE"), nullable=False)

    scheduled_at = Column(DateTime, nullable=False, index=True)
    channel = Column(String(50), nullable=False)  # instagram_feed / instagram_story
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING / SUCCESS / FAILED / CANCELED

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="upload_schedules")
    generation = relationship("Generation", back_populates="upload_schedules")