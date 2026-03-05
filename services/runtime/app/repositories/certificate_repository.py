from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.certificate import Certificate, CertificateStatusHistory


class CertificateRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_certificate(self, certificate_id: int) -> Certificate | None:
        return self._session.get(Certificate, certificate_id)

    def get_by_source_application(self, application_id: int) -> Certificate | None:
        stmt = select(Certificate).where(Certificate.source_application_id == application_id)
        return self._session.scalar(stmt)

    def create_certificate(
        self,
        certificate_number: str,
        source_application_id: int,
        source_application_number: str,
        applicant_subject: str,
        applicant_username: str,
        snapshot: dict[str, Any],
        generated_by_subject: str,
    ) -> Certificate:
        certificate = Certificate(
            certificate_number=certificate_number,
            source_application_id=source_application_id,
            source_application_number=source_application_number,
            status="GENERATED",
            applicant_subject=applicant_subject,
            applicant_username=applicant_username,
            snapshot_json=json.dumps(snapshot, ensure_ascii=False),
            generated_by_subject=generated_by_subject,
        )
        self._session.add(certificate)
        self._session.flush()
        return certificate

    def add_history(
        self,
        certificate_id: int,
        from_status: str | None,
        to_status: str,
        changed_by_subject: str,
        comment: str | None,
    ) -> None:
        row = CertificateStatusHistory(
            certificate_id=certificate_id,
            from_status=from_status,
            to_status=to_status,
            changed_by_subject=changed_by_subject,
            comment=comment,
        )
        self._session.add(row)
