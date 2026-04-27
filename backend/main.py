from dotenv import load_dotenv                                                                                                
load_dotenv()                                                                                                                 
from contextlib import asynccontextmanager                                                                                  
from pathlib import Path                                                                                                      
import sys              
import os                                                                                                              
from fastapi import FastAPI                              
from fastapi.staticfiles import StaticFiles                                                                                   
from fastapi.middleware.cors import CORSMiddleware

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db import Base, engine
from auth import router as auth_router
from generations import router as generations_router
from calendar_router import router as calendar_router
from instagram_router import router as instagram_router
from observability import report_observability_status
from scheduler import create_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_ready = False
    app.state.db_error = None

    try:
        Base.metadata.create_all(bind=engine)
        app.state.db_ready = True
    except Exception as e:
        app.state.db_error = str(e)
        print(f"[main] database initialization failed: {e}")

    report_observability_status()
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Team4 Project Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://team4-img-generation-project-w6nw.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# media static serving
(BACKEND_DIR / "generated").mkdir(parents=True, exist_ok=True)
(BACKEND_DIR / "uploads").mkdir(parents=True, exist_ok=True)
REFERENCE_PRESETS_DIR = BACKEND_DIR / "image_generator" / "reference_presets"
REFERENCE_PRESETS_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/media/generated",
    StaticFiles(directory=str(BACKEND_DIR / "generated")),
    name="media-generated",
)
app.mount(
    "/media/uploads",
    StaticFiles(directory=str(BACKEND_DIR / "uploads")),
    name="media-uploads",
)
app.mount(
    "/media/reference_presets",
    StaticFiles(directory=str(REFERENCE_PRESETS_DIR)),
    name="media-reference-presets",
)

app.include_router(auth_router)
app.include_router(generations_router)
app.include_router(calendar_router)
app.include_router(instagram_router)

# dev 브랜치 신규 라우터 (존재하는 경우에만 로드)
try:
    from routes.text_router import router as text_router
    app.include_router(text_router)
except ImportError as e:
    print(f"[main] text_router not loaded: {e}")

try:
    from analytics_router import router as analytics_router
    app.include_router(analytics_router)
except ImportError as e:
    print(f"[main] analytics_router not loaded: {e}")

try:
    from scheduler_router import router as scheduler_router
    app.include_router(scheduler_router)
except ImportError as e:
    print(f"[main] scheduler_router not loaded: {e}")

try:
    from integrations_router import router as integrations_router
    app.include_router(integrations_router)
except ImportError as e:
    print(f"[main] integrations_router not loaded: {e}")


@app.get("/")
def root():
    return {
        "message": "Backend is running",
        "db_ready": getattr(app.state, "db_ready", False),
        "db_error": getattr(app.state, "db_error", None),
    }
