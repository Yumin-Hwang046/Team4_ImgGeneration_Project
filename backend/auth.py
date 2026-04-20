import os
from typing import Annotated, Optional

import requests as http_requests
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from db import get_db
from models import User
from datetime import timedelta
from schemas import (
    UserResponse, Token,
    InstagramCallbackPayload, InstagramCallbackResponse,
    InstagramAccountOption, InstagramSelectAccountPayload,
)
from security import hash_password, verify_password, create_access_token, decode_access_token

META_APP_ID = os.getenv("META_APP_ID", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
META_REDIRECT_URI = os.getenv("META_REDIRECT_URI", "")

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
    email: Annotated[str, Form(..., title="아이디 (E-mail)")],
    password: Annotated[str, Form(..., title="비밀번호")],
    name: Annotated[str, Form(..., title="이름")],
    db: Session = Depends(get_db),
):
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
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/instagram/callback", response_model=InstagramCallbackResponse)
def instagram_callback(payload: InstagramCallbackPayload, db: Session = Depends(get_db)):
    if not META_APP_ID or not META_APP_SECRET or not META_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Meta 앱 환경변수가 설정되지 않았습니다.")

    try:
        # 1. code → Facebook short-lived token
        token_res = http_requests.get(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "redirect_uri": META_REDIRECT_URI,
                "code": payload.code,
            },
            timeout=10,
        )
        token_data = token_res.json()
        short_token = token_data.get("access_token")
        if not short_token:
            raise HTTPException(status_code=400, detail="Facebook 인증 코드 교환 실패: " + str(token_data))

        # 2. short-lived → long-lived token (60일)
        long_res = http_requests.get(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "fb_exchange_token": short_token,
            },
            timeout=10,
        )
        long_token = long_res.json().get("access_token", short_token)

        # 3. Facebook 유저 정보
        me_res = http_requests.get(
            "https://graph.facebook.com/v19.0/me",
            params={"fields": "id,name,email", "access_token": long_token},
            timeout=10,
        )
        me_data = me_res.json()
        fb_user_id = me_data.get("id", "")
        fb_name = me_data.get("name", "Facebook 사용자")
        fb_email = me_data.get("email") or f"fb_{fb_user_id}@facebook.local"

        # 4. Instagram Business 계정 조회
        instagram_accounts = []

        pages_res = http_requests.get(
            "https://graph.facebook.com/v19.0/me/accounts",
            params={
                "fields": "instagram_business_account{id,name,username}",
                "access_token": long_token,
            },
            timeout=10,
        )
        for page in pages_res.json().get("data", []):
            ig = page.get("instagram_business_account")
            if ig:
                instagram_accounts.append({
                    "id": ig["id"],
                    "name": ig.get("name", ""),
                    "username": ig.get("username"),
                })

        if not instagram_accounts:
            biz_res = http_requests.get(
                "https://graph.facebook.com/v19.0/me/businesses",
                params={
                    "fields": "id,name,instagram_accounts{id,name,username}",
                    "access_token": long_token,
                },
                timeout=10,
            )
            for biz in biz_res.json().get("data", []):
                for ig in biz.get("instagram_accounts", {}).get("data", []):
                    instagram_accounts.append({
                        "id": ig["id"],
                        "name": ig.get("name", ""),
                        "username": ig.get("username"),
                    })

        if not instagram_accounts:
            raise HTTPException(
                status_code=400,
                detail="연결된 Instagram Business 계정이 없습니다. Facebook 페이지에 Instagram 비즈니스 계정을 연결해주세요.",
            )

        ig_user_id = instagram_accounts[0]["id"]
        ig_email = fb_email

        # 5. 유저 생성 또는 조회
        user = None

        if payload.existing_token:
            try:
                existing_payload = decode_access_token(payload.existing_token)
                user_id = existing_payload.get("sub")
                user = db.query(User).filter(User.id == int(user_id)).first()
            except Exception:
                user = None

        if not user:
            user = db.query(User).filter(User.instagram_user_id == ig_user_id).first()

        if not user:
            user = db.query(User).filter(User.email == ig_email).first()

        is_new_user = False
        if not user:
            is_new_user = True
            user = User(
                email=ig_email,
                password_hash=None,
                name=fb_name,
                role="user",
                is_active=True,
            )
            db.add(user)
            db.flush()

        user.instagram_user_id = ig_user_id
        user.instagram_access_token = long_token

        if len(instagram_accounts) == 1:
            user.instagram_account_id = instagram_accounts[0]["id"]
            if instagram_accounts[0].get("username"):
                user.instagram_username = instagram_accounts[0]["username"]

        db.commit()
        db.refresh(user)

        if len(instagram_accounts) > 1:
            selection_token = create_access_token(
                data={"sub": str(user.id), "purpose": "ig_select"},
                expires_delta=timedelta(minutes=10),
            )
            return InstagramCallbackResponse(
                needs_selection=True,
                is_new_user=is_new_user,
                selection_token=selection_token,
                accounts=[InstagramAccountOption(**a) for a in instagram_accounts],
            )

        access_token = create_access_token(data={"sub": str(user.id)})
        return InstagramCallbackResponse(token=access_token, is_new_user=is_new_user)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Instagram 로그인 처리 중 오류: {str(e)}")


@router.post("/instagram/select-account")
def select_instagram_account(
    payload: InstagramSelectAccountPayload,
    db: Session = Depends(get_db),
):
    try:
        token_data = decode_access_token(payload.selection_token)
        if token_data.get("purpose") != "ig_select":
            raise HTTPException(status_code=400, detail="유효하지 않은 선택 토큰입니다.")
        user_id = int(token_data["sub"])
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="선택 토큰이 만료되었거나 유효하지 않습니다.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    user.instagram_account_id = payload.account_id
    db.commit()

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"token": access_token}


@router.post("/login", response_model=Token)
def login(
    email: str = Form(..., description="아이디(E-mail)"),
    password: str = Form(..., description="비밀번호"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()

    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
def read_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "instagram_username": current_user.instagram_username,
        "created_at": str(current_user.created_at),
        "updated_at": str(current_user.updated_at),
    }
