from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI

from db import Base, engine
from auth import router as auth_router
from generations import router as generations_router
from calendar_router import router as calendar_router
from instagram_router import router as instagram_router
from routes.text_router import router as text_router
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
app.include_router(text_router)

# image_router는 GPU 환경(VM)에서만 로드됩니다.
# torch/diffusers가 설치된 환경에서만 /image/case4 엔드포인트가 활성화됩니다.
try:
    from routes.image_router import router as image_router
    app.include_router(image_router)
except ImportError:
    pass


@app.get("/")
def root():
    return {"message": "Backend is running"}