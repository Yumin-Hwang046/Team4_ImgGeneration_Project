from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# 정적 파일 서빙: /static → backend/assets
app.mount(
    "/static",
    StaticFiles(directory="assets"),
    name="static",
)
