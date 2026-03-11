from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.repositories.user_profile_repository import UserProfileRepository
from app.services.user_profile_service import UserProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdateRequest(BaseModel):
    email: str | None = Field(default=None, max_length=320)
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=2000)
    actual_address: str | None = Field(default=None, max_length=2000)


class AvatarUpdateRequest(BaseModel):
    content_base64: str = Field(min_length=4)
    content_type: str = Field(min_length=3, max_length=128)


def _get_service(session: Session = Depends(get_session)) -> UserProfileService:
    return UserProfileService(UserProfileRepository(session))


@router.get("/me")
def get_my_profile(
    current_user: CurrentUser = Depends(get_current_user),
    service: UserProfileService = Depends(_get_service),
) -> dict[str, object]:
    return service.get_me(current_user=current_user)


@router.put("/me")
def update_my_profile(
    request: ProfileUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: UserProfileService = Depends(_get_service),
) -> dict[str, object]:
    return service.update_me(
        current_user=current_user,
        email=request.email,
        full_name=request.full_name,
        phone=request.phone,
        address=request.address,
        actual_address=request.actual_address,
    )


@router.put("/me/avatar")
def update_my_avatar(
    request: AvatarUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: UserProfileService = Depends(_get_service),
) -> dict[str, object]:
    return service.update_avatar(
        current_user=current_user,
        content_base64=request.content_base64,
        content_type=request.content_type,
    )


@router.delete("/me/avatar")
def clear_my_avatar(
    current_user: CurrentUser = Depends(get_current_user),
    service: UserProfileService = Depends(_get_service),
) -> dict[str, object]:
    return service.clear_avatar(current_user=current_user)
