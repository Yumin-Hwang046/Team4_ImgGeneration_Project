from contextlib import asynccontextmanager

from fastapi import FastAPI

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Team4 Project Backend", lifespan=lifespan)

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