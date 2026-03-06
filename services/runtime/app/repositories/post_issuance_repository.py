from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.post_issuance import PostIssuanceApplication, PostIssuanceStatusHistory


class PostIssuanceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_application(
        self,
        application_number: str,
        source_certificate_id: int,
        source_certificate_number: str,
        source_application_id: int,
        source_application_number: str,
        action_type: str,
        initiator_role: str,
        applicant_subject: str,
        applicant_username: str,
        payload: dict[str, Any],
    ) -> PostIssuanceApplication:
        application = PostIssuanceApplication(
            application_number=application_number,
            source_certificate_id=source_certificate_id,
            source_certificate_number=source_certificate_number,
            source_application_id=source_application_id,
            source_application_number=source_application_number,
            action_type=action_type,
            status="DRAFT",
            initiator_role=initiator_role,
            applicant_subject=applicant_subject,
            applicant_username=applicant_username,
            payload_json=json.dumps(payload, ensure_ascii=False),
        )
        self._session.add(application)
        self._session.flush()
        return application

    def get_application(self, application_id: int) -> PostIssuanceApplication | None:
        return self._session.get(PostIssuanceApplication, application_id)

    def list_by_subject(self, applicant_subject: str, limit: int, offset: int) -> list[PostIssuanceApplication]:
        stmt = (
            select(PostIssuanceApplication)
            .where(PostIssuanceApplication.applicant_subject == applicant_subject)
            .order_by(
                PostIssuanceApplication.updated_at.desc(),
                PostIssuanceApplication.created_at.desc(),
                PostIssuanceApplication.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.scalars(stmt).all())

    def list_by_statuses(self, statuses: tuple[str, ...], limit: int, offset: int) -> list[PostIssuanceApplication]:
        if not statuses:
            return []
        stmt = (
            select(PostIssuanceApplication)
            .where(PostIssuanceApplication.status.in_(statuses))
            .order_by(
                PostIssuanceApplication.updated_at.desc(),
                PostIssuanceApplication.created_at.desc(),
                PostIssuanceApplication.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.scalars(stmt).all())

    def list_history(self, application_id: int) -> list[PostIssuanceStatusHistory]:
        stmt = (
            select(PostIssuanceStatusHistory)
            .where(PostIssuanceStatusHistory.post_issuance_application_id == application_id)
            .order_by(PostIssuanceStatusHistory.changed_at.asc(), PostIssuanceStatusHistory.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def find_active_by_certificate(self, source_certificate_id: int, statuses: tuple[str, ...]) -> list[PostIssuanceApplication]:
        if not statuses:
            return []
        stmt = (
            select(PostIssuanceApplication)
            .where(
                PostIssuanceApplication.source_certificate_id == source_certificate_id,
                PostIssuanceApplication.status.in_(statuses),
            )
            .order_by(PostIssuanceApplication.created_at.asc(), PostIssuanceApplication.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def update_payload(self, application: PostIssuanceApplication, payload: dict[str, Any]) -> None:
        application.payload_json = json.dumps(payload, ensure_ascii=False)
        application.updated_at = datetime.now(UTC)

    def update_status(self, application: PostIssuanceApplication, new_status: str) -> None:
        application.status = new_status
        application.updated_at = datetime.now(UTC)

    def add_history(
        self,
        application_id: int,
        from_status: str | None,
        to_status: str,
        changed_by_subject: str,
        comment: str | None,
    ) -> None:
        row = PostIssuanceStatusHistory(
            post_issuance_application_id=application_id,
            from_status=from_status,
            to_status=to_status,
            changed_by_subject=changed_by_subject,
            comment=comment,
        )
        self._session.add(row)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
