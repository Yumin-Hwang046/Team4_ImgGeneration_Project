from fastapi import FastAPI

from db import Base, engine
from auth import router as auth_router
from generations import router as generations_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Team4 Project Backend")

app.include_router(auth_router)
app.include_router(generations_router)


@app.get("/")
def root():
    return {"message": "Backend is running"}