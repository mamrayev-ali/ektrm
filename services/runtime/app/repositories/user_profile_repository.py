from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_profile import UserProfile


class UserProfileRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_subject(self, subject: str) -> UserProfile | None:
        stmt = select(UserProfile).where(UserProfile.subject == subject)
        return self._session.scalar(stmt)

    def create_profile(
        self,
        subject: str,
        username_snapshot: str,
        email: str | None,
        full_name: str | None,
    ) -> UserProfile:
        profile = UserProfile(
            subject=subject,
            username_snapshot=username_snapshot,
            email=email,
            full_name=full_name,
        )
        self._session.add(profile)
        self._session.flush()
        return profile

    def touch_from_identity(
        self,
        profile: UserProfile,
        username_snapshot: str,
        email: str | None,
        full_name: str | None,
    ) -> None:
        profile.username_snapshot = username_snapshot
        if not profile.email and email:
            profile.email = email
        if not profile.full_name and full_name:
            profile.full_name = full_name
        profile.updated_at = datetime.now(UTC)

    def update_profile(
        self,
        profile: UserProfile,
        *,
        email: str | None,
        full_name: str | None,
        phone: str | None,
        address: str | None,
        actual_address: str | None,
    ) -> None:
        profile.email = email
        profile.full_name = full_name
        profile.phone = phone
        profile.address = address
        profile.actual_address = actual_address
        profile.updated_at = datetime.now(UTC)

    def update_avatar(self, profile: UserProfile, avatar_data_url: str | None) -> None:
        profile.avatar_data_url = avatar_data_url
        profile.updated_at = datetime.now(UTC)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
