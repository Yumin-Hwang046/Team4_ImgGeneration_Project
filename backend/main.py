from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.db import Base, engine
from backend import models  # noqa: F401
from backend.auth import router as auth_router
from backend.generations import router as generations_router
from backend.calendar_router import router as calendar_router
from backend.instagram_router import router as instagram_router
from backend.analytics_router import router as analytics_router
from backend.scheduler_router import router as scheduler_router
from backend.integrations_router import router as integrations_router
from backend.scheduler_service import start_scheduler, shutdown_scheduler


BASE_DIR = Path("/home/minberry/Team4_BE/backend")
GENERATED_DIR = BASE_DIR / "generated"
UPLOAD_DIR = BASE_DIR / "uploads"

GENERATED_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Team4 Project Backend", lifespan=lifespan)

# 정적 파일 서빙
app.mount("/media/generated", StaticFiles(directory=str(GENERATED_DIR)), name="generated-media")
app.mount("/media/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="upload-media")

# API routers
app.include_router(auth_router)
app.include_router(generations_router)
app.include_router(calendar_router)
app.include_router(instagram_router)
app.include_router(analytics_router)
app.include_router(scheduler_router)
app.include_router(integrations_router)

try:
    from backend.routes.text_router import router as text_router
    app.include_router(text_router)
except ImportError:
    pass

try:
    from backend.routes.image_router import router as image_router
    app.include_router(image_router)
except ImportError:
    pass


@app.get("/")
def root():
    return {"message": "Backend is running"}