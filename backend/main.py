from fastapi import FastAPI

from db import Base, engine
from auth import router as auth_router
from generations import router as generations_router
from calendar_router import router as calendar_router
from instagram_router import router as instagram_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Team4 Project Backend")

app.include_router(auth_router)
app.include_router(generations_router)
app.include_router(calendar_router)
app.include_router(instagram_router)


@app.get("/")
def root():
    return {"message": "Backend is running"}