from typing import Any, List

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi_pagination import Page, paginate
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_active_superuser
from app.core.security import get_password_hash
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, User as UserSchema

router = APIRouter()


@router.get("/", response_model=Page[UserSchema])
def read_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    모든 사용자 목록을 가져옵니다. (관리자 전용)
    """
    users = db.query(User).all()
    return paginate(users)


@router.post("/", response_model=UserSchema)
def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    새 사용자를 생성합니다. (관리자 전용)
    """
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다.",
        )
    
    user = db.query(User).filter(User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 사용자 이름입니다.",
        )
    
    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        is_superuser=user_in.is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserSchema)
def read_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    특정 사용자 정보를 가져옵니다.
    관리자는 모든 사용자 정보를, 일반 사용자는 자신의 정보만 볼 수 있습니다.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )
    
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 충분하지 않습니다.",
        )
    
    return user


@router.put("/{user_id}", response_model=UserSchema)
def update_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    사용자 정보를 업데이트합니다.
    관리자는 모든 사용자 정보를, 일반 사용자는 자신의 정보만 업데이트할 수 있습니다.
    """
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 충분하지 않습니다.",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )
    
    if user_in.username and user_in.username != user.username:
        user_exists = db.query(User).filter(User.username == user_in.username).first()
        if user_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 등록된 사용자 이름입니다.",
            )
        user.username = user_in.username
    
    if user_in.email and user_in.email != user.email:
        user_exists = db.query(User).filter(User.email == user_in.email).first()
        if user_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 등록된 이메일입니다.",
            )
        user.email = user_in.email
    
    if user_in.password:
        user.hashed_password = get_password_hash(user_in.password)
    
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    
    if current_user.is_superuser and user_in.is_superuser is not None:
        user.is_superuser = user_in.is_superuser
    
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=UserSchema)
def delete_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    사용자를 삭제합니다. (관리자 전용)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )
    
    db.delete(user)
    db.commit()
    return user 