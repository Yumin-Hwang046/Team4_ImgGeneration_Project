from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/analyzer", tags=["analyzer"])


@router.post("/analyze")
def analyze_image():
    raise HTTPException(status_code=501, detail="image_analyzer가 아직 구현되지 않았습니다.")
