from typing import Optional, List
from datetime import datetime, date
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
# Generated Images
# -----------------------------
class GeneratedImageItem(BaseModel):
    id: int
    image_url: str
    final_image_url: Optional[str] = None
    prompt_used: Optional[str] = None
    version_no: int
    image_type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class RegenerateImageResponse(BaseModel):
    generation_id: int
    status: str
    message: str


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

    generated_images: Optional[List[GeneratedImageItem]] = None

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


# -----------------------------
# Calendar / Schedule
# -----------------------------
class CalendarEventCreate(BaseModel):
    event_date: date
    title: str
    event_type: str
    location: Optional[str] = None
    description: Optional[str] = None


class CalendarEventItem(BaseModel):
    id: int
    event_date: date
    title: str
    event_type: str
    location: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class CalendarGenerationItem(BaseModel):
    id: int
    menu_name: Optional[str] = None
    business_category: Optional[str] = None
    generated_image_url: Optional[str] = None
    generation_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UploadScheduleCreate(BaseModel):
    generation_id: int
    scheduled_at: datetime
    channel: str


class UploadScheduleItem(BaseModel):
    id: int
    generation_id: int
    scheduled_at: datetime
    channel: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CalendarMonthDayItem(BaseModel):
    date: str
    weather_summary: Optional[str] = None
    has_event: bool
    has_generation: bool
    has_schedule: bool


class CalendarMonthResponse(BaseModel):
    year: int
    month: int
    days: List[CalendarMonthDayItem]


class CalendarWeatherItem(BaseModel):
    summary: str


class CalendarRecommendationItem(BaseModel):
    recommended_time: str
    recommended_channel: str
    recommended_purpose: str
    recommended_concept: str


class CalendarDayResponse(BaseModel):
    date: str
    weather: CalendarWeatherItem
    recommendation: CalendarRecommendationItem
    events: List[CalendarEventItem]
    generations: List[CalendarGenerationItem]
    schedules: List[UploadScheduleItem]


# -----------------------------
# Instagram OAuth
# -----------------------------
class InstagramCallbackPayload(BaseModel):
    code: str
    existing_token: Optional[str] = None  # 이미 로그인된 유저가 인스타 연동 시 전달


class InstagramAccountOption(BaseModel):
    id: str
    name: str
    username: Optional[str] = None


class InstagramCallbackResponse(BaseModel):
    token: Optional[str] = None
    needs_selection: bool = False
    is_new_user: bool = False           # True면 온보딩으로 라우팅
    selection_token: Optional[str] = None
    accounts: Optional[List[InstagramAccountOption]] = None


class InstagramSelectAccountPayload(BaseModel):
    selection_token: str
    account_id: str
    account_name: str


# -----------------------------
# Instagram
# -----------------------------
class InstagramUploadRequest(BaseModel):
    generation_id: int
    channel: str  # instagram_feed / instagram_story


class InstagramUploadResponse(BaseModel):
    generation_id: int
    channel: str
    status: str
    message: str


class InstagramScheduleUploadRequest(BaseModel):
    generation_id: int
    scheduled_at: datetime
    channel: str  # instagram_feed / instagram_story


class InstagramScheduleStatusResponse(BaseModel):
    schedule_id: int
    generation_id: int
    channel: str
    scheduled_at: datetime
    status: str
    message: str