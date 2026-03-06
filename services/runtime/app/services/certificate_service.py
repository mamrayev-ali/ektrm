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

    def sign_and_publish(
        self,
        certificate_id: int,
        current_user: CurrentUser,
        comment: str | None = None,
    ) -> dict[str, Any]:
        self._require_ops(current_user)
        certificate = self._repository.get_certificate(certificate_id)
        if certificate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate was not found")
        if certificate.status != "GENERATED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only GENERATED certificate can be signed and published",
            )

        now = datetime.now(UTC)
        certificate.signed_by_subject = current_user.subject
        certificate.signed_at = now

        self._repository.add_history(
            certificate_id=certificate.id,
            from_status="GENERATED",
            to_status="SIGNED",
            changed_by_subject=current_user.subject,
            comment=comment or "Certificate mock-signed by OPS",
        )
        certificate.status = "SIGNED"

        self._repository.add_history(
            certificate_id=certificate.id,
            from_status="SIGNED",
            to_status="PUBLISHED",
            changed_by_subject=current_user.subject,
            comment="Certificate published to internal and public registries",
        )
        certificate.status = "PUBLISHED"
        certificate.published_at = now

        self._repository.add_publication(
            certificate_id=certificate.id,
            visibility="INTERNAL",
            is_public=False,
            published_by_subject=current_user.subject,
            comment="Internal registry publication event",
        )
        self._repository.add_publication(
            certificate_id=certificate.id,
            visibility="PUBLIC",
            is_public=True,
            published_by_subject=current_user.subject,
            comment="Public read-only registry publication event",
        )

        self._repository.add_history(
            certificate_id=certificate.id,
            from_status="PUBLISHED",
            to_status="ACTIVE",
            changed_by_subject=current_user.subject,
            comment="Certificate is active after publication",
        )
        certificate.status = "ACTIVE"

        try:
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise
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

    def list_internal_registry(
        self,
        current_user: CurrentUser,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
    ) -> dict[str, Any]:
        if "OPS" in current_user.roles:
            applicant_subject = None
        elif "Applicant" in current_user.roles:
            applicant_subject = current_user.subject
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Applicant or OPS role can view internal registry",
            )

        certificates = self._repository.list_internal_registry(
            limit=limit,
            offset=offset,
            search=search,
            applicant_subject=applicant_subject,
        )
        items = [self._serialize_registry_item(certificate, include_subject=True) for certificate in certificates]
        return {
            "total": len(items),
            "limit": limit,
            "offset": offset,
            "items": items,
        }

    def list_public_registry(
        self,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
    ) -> dict[str, Any]:
        certificates = self._repository.list_public_registry(limit=limit, offset=offset, search=search)
        items = [self._serialize_registry_item(certificate, include_subject=False) for certificate in certificates]
        return {
            "total": len(items),
            "limit": limit,
            "offset": offset,
            "items": items,
        }

    def _assert_owner_or_ops(self, certificate: Certificate, current_user: CurrentUser) -> None:
        if "OPS" in current_user.roles:
            return
        if certificate.applicant_subject != current_user.subject:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this certificate")

    def _require_ops(self, current_user: CurrentUser) -> None:
        if "OPS" not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only OPS role can sign and publish certificates",
            )

    def _serialize_certificate(self, certificate: Certificate) -> dict[str, Any]:
        return {
            "id": certificate.id,
            "certificate_number": certificate.certificate_number,
            "source_application_id": certificate.source_application_id,
            "source_application_number": certificate.source_application_number,
            "status": certificate.status,
            "is_dangerous_product": certificate.is_dangerous_product,
            "applicant_subject": certificate.applicant_subject,
            "applicant_username": certificate.applicant_username,
            "snapshot": self._decode_snapshot(certificate.snapshot_json),
            "generated_by_subject": certificate.generated_by_subject,
            "generated_at": certificate.generated_at.isoformat(),
            "signed_by_subject": certificate.signed_by_subject,
            "signed_at": certificate.signed_at.isoformat() if certificate.signed_at else None,
            "published_at": certificate.published_at.isoformat() if certificate.published_at else None,
            "created_at": certificate.created_at.isoformat(),
            "updated_at": certificate.updated_at.isoformat(),
        }

    def _serialize_registry_item(self, certificate: Certificate, include_subject: bool) -> dict[str, Any]:
        snapshot = self._decode_snapshot(certificate.snapshot_json)
        payload = snapshot.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}

        product_name = None
        products = payload.get("products")
        if isinstance(products, list) and products and isinstance(products[0], dict):
            product_name = products[0].get("name")

        item: dict[str, Any] = {
            "id": certificate.id,
            "certificate_number": certificate.certificate_number,
            "source_application_id": certificate.source_application_id,
            "source_application_number": certificate.source_application_number,
            "status": certificate.status,
            "applicant_username": certificate.applicant_username,
            "applicant_name": payload.get("applicant_name"),
            "ops_code": payload.get("ops_code"),
            "product_name": product_name,
            "signed_at": certificate.signed_at.isoformat() if certificate.signed_at else None,
            "published_at": certificate.published_at.isoformat() if certificate.published_at else None,
            "is_dangerous_product": certificate.is_dangerous_product,
            "generated_at": certificate.generated_at.isoformat(),
            "updated_at": certificate.updated_at.isoformat(),
        }
        if include_subject:
            item["applicant_subject"] = certificate.applicant_subject
        return item

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
