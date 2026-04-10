from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    is_active = Column(Integer, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    generations = relationship("Generation", back_populates="user")


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
    hashtags = Column(Text, nullable=True)  # JSON 문자열로 저장

    weather_summary = Column(String(255), nullable=True)
    recommended_concept = Column(String(255), nullable=True)

    original_image_url = Column(String(500), nullable=True)
    generated_image_url = Column(String(500), nullable=True)
    image_mode = Column(String(50), nullable=True)
    generation_status = Column(String(50), nullable=False, default="SUCCESS")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="generations")