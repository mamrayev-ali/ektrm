from __future__ import annotations

import base64
from typing import Any

from fastapi import HTTPException, status

from app.auth import CurrentUser
from app.models.user_profile import UserProfile
from app.repositories.user_profile_repository import UserProfileRepository

ALLOWED_AVATAR_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/svg+xml"})
MAX_AVATAR_SIZE_BYTES = 1024 * 1024


class UserProfileService:
    def __init__(self, repository: UserProfileRepository) -> None:
        self._repository = repository

    def get_me(self, current_user: CurrentUser) -> dict[str, Any]:
        profile = self._ensure_profile(current_user)
        return self._serialize_profile(profile, current_user)

    def update_me(
        self,
        current_user: CurrentUser,
        *,
        email: str | None,
        full_name: str | None,
        phone: str | None,
        address: str | None,
        actual_address: str | None,
    ) -> dict[str, Any]:
        profile = self._ensure_profile(current_user)
        self._repository.update_profile(
            profile,
            email=self._clean_optional(email, 320),
            full_name=self._clean_optional(full_name, 255),
            phone=self._clean_optional(phone, 32),
            address=self._clean_optional(address, 2000),
            actual_address=self._clean_optional(actual_address, 2000),
        )
        try:
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise
        return self._serialize_profile(profile, current_user)

    def update_avatar(
        self,
        current_user: CurrentUser,
        *,
        content_base64: str,
        content_type: str,
    ) -> dict[str, Any]:
        profile = self._ensure_profile(current_user)
        normalized_content_type = self._clean_required(content_type, 128)
        if normalized_content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported avatar content type '{normalized_content_type}'",
            )
        raw_content = self._decode_base64(content_base64)
        if len(raw_content) > MAX_AVATAR_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Avatar exceeds max size {MAX_AVATAR_SIZE_BYTES} bytes",
            )
        avatar_data_url = f"data:{normalized_content_type};base64,{content_base64.strip()}"
        self._repository.update_avatar(profile, avatar_data_url)
        try:
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise
        return self._serialize_profile(profile, current_user)

    def clear_avatar(self, current_user: CurrentUser) -> dict[str, Any]:
        profile = self._ensure_profile(current_user)
        self._repository.update_avatar(profile, None)
        try:
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise
        return self._serialize_profile(profile, current_user)

    def _ensure_profile(self, current_user: CurrentUser) -> UserProfile:
        profile = self._repository.get_by_subject(current_user.subject)
        full_name = self._resolve_full_name(current_user)
        if profile is None:
            profile = self._repository.create_profile(
                subject=current_user.subject,
                username_snapshot=current_user.username,
                email=current_user.email,
                full_name=full_name,
            )
            try:
                self._repository.commit()
            except Exception:
                self._repository.rollback()
                raise
            return profile

        self._repository.touch_from_identity(
            profile,
            username_snapshot=current_user.username,
            email=current_user.email,
            full_name=full_name,
        )
        try:
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise
        return profile

    def _serialize_profile(self, profile: UserProfile, current_user: CurrentUser) -> dict[str, Any]:
        display_name = (profile.full_name or current_user.username or current_user.subject).strip()
        primary_role = self._resolve_primary_role(current_user.roles)
        return {
            "id": profile.id,
            "subject": profile.subject,
            "username": current_user.username,
            "email": profile.email,
            "full_name": profile.full_name,
            "display_name": display_name,
            "phone": profile.phone,
            "address": profile.address,
            "actual_address": profile.actual_address,
            "avatar_data_url": profile.avatar_data_url,
            "roles": sorted(current_user.roles),
            "primary_role": primary_role,
            "role_label": self._role_label(primary_role),
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
        }

    def _resolve_full_name(self, current_user: CurrentUser) -> str | None:
        claims = current_user.claims
        direct_name = claims.get("name")
        if isinstance(direct_name, str) and direct_name.strip():
            return direct_name.strip()
        given_name = claims.get("given_name")
        family_name = claims.get("family_name")
        if isinstance(given_name, str) and isinstance(family_name, str):
            full_name = f"{given_name.strip()} {family_name.strip()}".strip()
            return full_name or None
        return None

    def _resolve_primary_role(self, roles: frozenset[str]) -> str:
        if "OPS" in roles:
            return "OPS"
        if "Applicant" in roles:
            return "Applicant"
        return "User"

    def _role_label(self, role: str) -> str:
        if role == "OPS":
            return "ОПС"
        if role == "Applicant":
            return "Заявитель"
        return "Пользователь"

    def _decode_base64(self, content_base64: str) -> bytes:
        try:
            return base64.b64decode(content_base64, validate=True)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="content_base64 is invalid",
            ) from exc

    def _clean_required(self, value: str | None, limit: int) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Required value is missing",
            )
        if len(cleaned) > limit:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Value exceeds max length {limit}",
            )
        return cleaned

    def _clean_optional(self, value: str | None, limit: int) -> str | None:
        cleaned = (value or "").strip()
        if not cleaned:
            return None
        if len(cleaned) > limit:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Value exceeds max length {limit}",
            )
        return cleaned
