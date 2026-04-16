from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import User, UserProfile
from backend.schemas import UserResponse, Token
from backend.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

bearer_scheme = HTTPBearer()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    return user


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(
    name: Annotated[str, Form(...)],
    email: Annotated[str, Form(...)],
    password: Annotated[str, Form(...)],
    store_name: Annotated[str, Form(...)],
    road_address: Annotated[str, Form(...)],
    business_category: Annotated[str, Form(...)],
    detail_address: Annotated[Optional[str], Form()] = None,
    default_mood: Annotated[Optional[str], Form()] = None,
    jibun_address: Annotated[Optional[str], Form()] = None,
    zipcode: Annotated[Optional[str], Form()] = None,
    sido: Annotated[Optional[str], Form()] = None,
    sigungu: Annotated[Optional[str], Form()] = None,
    emd: Annotated[Optional[str], Form()] = None,
    legal_code: Annotated[Optional[str], Form()] = None,
    latitude: Annotated[Optional[float], Form()] = None,
    longitude: Annotated[Optional[float], Form()] = None,
    db: Session = Depends(get_db),
):
    if not road_address.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="기본주소는 주소검색을 통해 선택해야 합니다.",
        )

    if not business_category.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="업종을 선택해주세요.",
        )

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 이메일입니다.",
        )

    new_user = User(
        email=email,
        password_hash=hash_password(password),
        name=name,
        role="user",
        is_active=True,
    )

    db.add(new_user)
    db.flush()

    new_profile = UserProfile(
        user_id=new_user.id,
        store_name=store_name,
        business_category=business_category,
        road_address=road_address,
        jibun_address=jibun_address,
        detail_address=detail_address,
        zipcode=zipcode,
        sido=sido,
        sigungu=sigungu,
        emd=emd,
        legal_code=legal_code,
        latitude=latitude,
        longitude=longitude,
        default_mood=default_mood,
    )

    db.add(new_profile)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
def read_me(
    current_user: User = Depends(get_current_user),
):
    return current_user