from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status

from app.auth import CurrentUser
from app.models.application import CertApplication
from app.models.certificate import Certificate
from app.repositories.certificate_repository import CertificateRepository


class CertificateService:
    def __init__(self, repository: CertificateRepository) -> None:
        self._repository = repository

    def generate_for_approved_application(
        self,
        application: CertApplication,
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        if application.status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Certificate can be generated only for APPROVED applications",
            )

        existing = self._repository.get_by_source_application(application.id)
        if existing is not None:
            return self._serialize_certificate(existing)

        snapshot = self._build_snapshot(application)
        certificate = self._repository.create_certificate(
            certificate_number=self._new_certificate_number(application.id),
            source_application_id=application.id,
            source_application_number=application.application_number,
            applicant_subject=application.applicant_subject,
            applicant_username=application.applicant_username,
            snapshot=snapshot,
            generated_by_subject=current_user.subject,
        )
        self._repository.add_history(
            certificate_id=certificate.id,
            from_status=None,
            to_status="GENERATED",
            changed_by_subject=current_user.subject,
            comment=f"Certificate generated from application {application.application_number}",
        )
        return self._serialize_certificate(certificate)

    def get_certificate(self, certificate_id: int, current_user: CurrentUser) -> dict[str, Any]:
        certificate = self._repository.get_certificate(certificate_id)
        if certificate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate was not found")
        self._assert_owner_or_ops(certificate, current_user)
        return self._serialize_certificate(certificate)

    def get_certificate_by_application(self, application_id: int, current_user: CurrentUser) -> dict[str, Any]:
        certificate = self._repository.get_by_source_application(application_id)
        if certificate is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificate for the application was not found",
            )
        self._assert_owner_or_ops(certificate, current_user)
        return self._serialize_certificate(certificate)

    def _assert_owner_or_ops(self, certificate: Certificate, current_user: CurrentUser) -> None:
        if "OPS" in current_user.roles:
            return
        if certificate.applicant_subject != current_user.subject:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this certificate")

    def _serialize_certificate(self, certificate: Certificate) -> dict[str, Any]:
        return {
            "id": certificate.id,
            "certificate_number": certificate.certificate_number,
            "source_application_id": certificate.source_application_id,
            "source_application_number": certificate.source_application_number,
            "status": certificate.status,
            "applicant_subject": certificate.applicant_subject,
            "applicant_username": certificate.applicant_username,
            "snapshot": self._decode_snapshot(certificate.snapshot_json),
            "generated_by_subject": certificate.generated_by_subject,
            "generated_at": certificate.generated_at.isoformat(),
            "created_at": certificate.created_at.isoformat(),
            "updated_at": certificate.updated_at.isoformat(),
        }

    def _decode_snapshot(self, snapshot_json: str) -> dict[str, Any]:
        try:
            raw = json.loads(snapshot_json)
        except json.JSONDecodeError:
            return {}
        return raw if isinstance(raw, dict) else {}

    def _build_snapshot(self, application: CertApplication) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if application.payload_json:
            try:
                parsed = json.loads(application.payload_json)
                if isinstance(parsed, dict):
                    payload = parsed
            except json.JSONDecodeError:
                payload = {}

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "application": {
                "id": application.id,
                "application_number": application.application_number,
                "status": application.status,
                "applicant_subject": application.applicant_subject,
                "applicant_username": application.applicant_username,
            },
            "payload": payload,
        }

    def _new_certificate_number(self, application_id: int) -> str:
        now = datetime.now(UTC)
        return f"KZ/CERT/{now:%Y%m%d}/{application_id:06d}"
