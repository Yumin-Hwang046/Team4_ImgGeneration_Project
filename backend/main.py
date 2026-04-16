from fastapi import FastAPI

from routes.image_router import router as image_router

app = FastAPI(title="Team4 Project Backend")

app.include_router(image_router)


@app.get("/")
def root():
    return {"message": "Backend is running"}
