from fastapi import FastAPI

from backend.db import Base, engine
from backend import models  # noqa: F401
from backend.auth import router as auth_router
from backend.generations import router as generations_router
from backend.calendar_router import router as calendar_router
from backend.instagram_router import router as instagram_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Team4 Project Backend")

app.include_router(auth_router)
app.include_router(generations_router)
app.include_router(calendar_router)
app.include_router(instagram_router)


@app.get("/")
def root():
    return {"message": "Backend is running"}
