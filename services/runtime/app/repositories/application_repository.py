from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import CertApplication, CertApplicationStatusHistory


class ApplicationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_application(
        self,
        application_number: str,
        applicant_subject: str,
        applicant_username: str,
        payload: dict[str, Any],
    ) -> CertApplication:
        application = CertApplication(
            application_number=application_number,
            status="DRAFT",
            applicant_subject=applicant_subject,
            applicant_username=applicant_username,
            payload_json=json.dumps(payload, ensure_ascii=False),
        )
        self._session.add(application)
        self._session.flush()
        return application

    def get_application(self, application_id: int) -> CertApplication | None:
        return self._session.get(CertApplication, application_id)

    def list_history(self, application_id: int) -> list[CertApplicationStatusHistory]:
        stmt = (
            select(CertApplicationStatusHistory)
            .where(CertApplicationStatusHistory.application_id == application_id)
            .order_by(CertApplicationStatusHistory.changed_at.asc(), CertApplicationStatusHistory.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def update_payload(self, application: CertApplication, payload: dict[str, Any]) -> None:
        application.payload_json = json.dumps(payload, ensure_ascii=False)
        application.updated_at = datetime.now(UTC)

    def update_status(self, application: CertApplication, new_status: str) -> None:
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
        row = CertApplicationStatusHistory(
            application_id=application_id,
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
