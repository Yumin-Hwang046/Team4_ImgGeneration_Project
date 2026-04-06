from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes.image_router import router as image_router
from routes.text_router import router as text_router
from routes.analyzer_router import router as analyzer_router

app = FastAPI()

# 정적 파일 서빙: /static → backend/assets
app.mount(
    "/static",
    StaticFiles(directory="assets"),
    name="static",
)

app.include_router(image_router)
app.include_router(text_router)
app.include_router(analyzer_router)
