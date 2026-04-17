from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI

from db import Base, engine
from auth import router as auth_router
from generations import router as generations_router
from calendar_router import router as calendar_router
from instagram_router import router as instagram_router
from scheduler import create_scheduler

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Team4 Project Backend", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(generations_router)
app.include_router(calendar_router)
app.include_router(instagram_router)

# dev 브랜치 신규 라우터 (존재하는 경우에만 로드)
try:
    from routes.text_router import router as text_router
    app.include_router(text_router)
except ImportError:
    pass

try:
    from routes.image_router import router as image_router
    app.include_router(image_router)
except ImportError:
    pass

try:
    from analytics_router import router as analytics_router
    app.include_router(analytics_router)
except ImportError:
    pass

try:
    from scheduler_router import router as scheduler_router
    app.include_router(scheduler_router)
except ImportError:
    pass

try:
    from integrations_router import router as integrations_router
    app.include_router(integrations_router)
except ImportError:
    pass


@app.get("/")
def root():
    return {"message": "Backend is running"}
