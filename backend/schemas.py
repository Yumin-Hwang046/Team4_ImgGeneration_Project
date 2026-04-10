from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr


# -----------------------------
# Auth
# -----------------------------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# -----------------------------
# Generation CRUD
# -----------------------------
class GenerationCreate(BaseModel):
    purpose: Optional[str] = None
    mood: Optional[str] = None
    extra_info: Optional[str] = None
    generated_copy: Optional[str] = None
    hashtags: Optional[List[str]] = None


class GenerationUpdate(BaseModel):
    purpose: Optional[str] = None
    mood: Optional[str] = None
    extra_info: Optional[str] = None
    generated_copy: Optional[str] = None
    hashtags: Optional[List[str]] = None


class GenerationResponse(BaseModel):
    id: int
    user_id: int
    purpose: Optional[str] = None
    mood: Optional[str] = None
    extra_info: Optional[str] = None
    generated_copy: Optional[str] = None
    hashtags: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# -----------------------------
# Run API
# -----------------------------
class GenerationRunResponse(BaseModel):
    generation_id: int
    user_id: int

    purpose: str
    business_category: str
    menu_name: str
    location: str
    target_datetime: datetime

    weather_summary: str
    season_context: str
    recommended_concept: str

    image_mode: str
    original_image_url: Optional[str] = None
    generated_image_url: Optional[str] = None

    generated_copy: str
    hashtags: List[str]

    status: str
    created_at: datetime

# -----------------------------
# Generation Detail (조회용)
# -----------------------------
class GenerationDetailResponse(BaseModel):
    id: int
    user_id: int

    purpose: Optional[str] = None
    business_category: Optional[str] = None
    menu_name: Optional[str] = None
    mood: Optional[str] = None
    location: Optional[str] = None
    target_datetime: Optional[datetime] = None

    extra_info: Optional[str] = None
    generated_copy: Optional[str] = None
    hashtags: Optional[List[str]] = None

    weather_summary: Optional[str] = None
    recommended_concept: Optional[str] = None

    original_image_url: Optional[str] = None
    generated_image_url: Optional[str] = None
    image_mode: Optional[str] = None
    generation_status: Optional[str] = None

    created_at: datetime

    class Config:
        from_attributes = True

# -----------------------------
# Generation List (보관함 목록용)
# -----------------------------
class GenerationListItem(BaseModel):
    id: int
    menu_name: Optional[str] = None
    business_category: Optional[str] = None
    generated_image_url: Optional[str] = None
    generation_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True