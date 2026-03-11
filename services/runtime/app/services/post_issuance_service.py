from __future__ import annotations

import json
from datetime import UTC, datetime
from secrets import randbelow
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.auth import CurrentUser
from app.models.certificate import Certificate
from app.models.post_issuance import PostIssuanceApplication
from app.repositories.certificate_repository import CertificateRepository
from app.repositories.post_issuance_repository import PostIssuanceRepository
from app.repositories.reference_data_repository import ReferenceDataRepository
from app.seed.reference_data_seed import TERMINATION_REASON_APPLICANT_CODES, TERMINATION_REASON_OPS_CODES
from app.services.file_slot_service import POST_ISSUANCE_BASIS_FILE_SLOT

POST_ISSUANCE_STATUSES = frozenset(
    {
        "DRAFT",
        "SUBMITTED",
        "REGISTERED",
        "IN_REVIEW",
        "REVISION_REQUESTED",
        "APPROVED",
        "REJECTED",
        "ARCHIVED",
        "REGISTRY_UPDATED",
        "COMPLETED",
    }
)
EDITABLE_STATUSES = frozenset({"DRAFT", "REVISION_REQUESTED"})
OPS_REVIEW_STATUSES = frozenset({"IN_REVIEW", "REVISION_REQUESTED", "APPROVED", "REJECTED"})
OPS_QUEUE_DEFAULT_STATUSES = ("REGISTERED", "IN_REVIEW", "REVISION_REQUESTED")
ACTIVE_CONFLICT_STATUSES = ("DRAFT", "SUBMITTED", "REGISTERED", "IN_REVIEW", "REVISION_REQUESTED")
ACTION_TYPES = frozenset({"SUSPEND", "TERMINATE"})
ACTION_DICTIONARY_BY_TYPE = {
    "SUSPEND": "suspension_reason",
    "TERMINATE": "termination_reason",
}
CERTIFICATE_STATUS_BY_ACTION = {
    "SUSPEND": "SUSPENDED",
    "TERMINATE": "TERMINATED",
}
ALLOWED_CERTIFICATE_STATUSES_BY_ACTION = {
    "SUSPEND": frozenset({"ACTIVE"}),
    "TERMINATE": frozenset({"ACTIVE", "SUSPENDED"}),
}


class PostIssuanceService:
    def __init__(
        self,
        repository: PostIssuanceRepository,
        certificate_repository: CertificateRepository,
        reference_data_repository: ReferenceDataRepository,
    ) -> None:
        self._repository = repository
        self._certificate_repository = certificate_repository
        self._reference_data_repository = reference_data_repository

    def create_draft(
        self,
        source_certificate_id: int,
        action_type: str,
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        normalized_action = self._normalize_action_type(action_type)
        certificate = self._require_certificate(source_certificate_id)
        self._assert_owner_or_ops_for_certificate(certificate, current_user)
        conflicting = self._find_conflicting_process(certificate.id)
        reusable = self._find_reusable_editable_process(conflicting, normalized_action)
        if reusable is not None:
            return self._serialize_application(reusable)
        self._assert_no_conflicting_process(certificate.id, active_processes=conflicting)
        self._assert_certificate_eligible(certificate, normalized_action)

        payload = self._build_initial_payload(certificate, normalized_action, current_user)
        try:
            application = self._repository.create_application(
                application_number=self._new_application_number(),
                source_certificate_id=certificate.id,
                source_certificate_number=certificate.certificate_number,
                source_application_id=certificate.source_application_id,
                source_application_number=certificate.source_application_number,
                action_type=normalized_action,
                initiator_role=self._resolve_request_source(current_user),
                applicant_subject=certificate.applicant_subject,
                applicant_username=certificate.applicant_username,
                payload=payload,
            )
            self._repository.add_history(
                application_id=application.id,
                from_status=None,
                to_status="DRAFT",
                changed_by_subject=current_user.subject,
                comment=f"Post-issuance draft created for {normalized_action}",
            )
            self._repository.commit()
            return self._serialize_application(application)
        except IntegrityError as exc:
            self._repository.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Post-issuance application number must be unique",
            ) from exc

    def update_draft(
        self,
        application_id: int,
        payload: dict[str, Any],
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        application = self._require_application(application_id)
        self._assert_owner_or_ops(application, current_user)
        if application.status not in EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Post-issuance draft can only be edited in DRAFT or REVISION_REQUESTED status",
            )
        normalized_payload = self._normalize_payload(application, payload)
        self._repository.update_payload(application, normalized_payload)
        self._repository.commit()
        return self._serialize_application(application)

    def delete_draft(self, application_id: int, current_user: CurrentUser) -> dict[str, Any]:
        application = self._require_application(application_id)
        self._assert_owner_or_ops(application, current_user)
        if application.status not in EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only DRAFT or REVISION_REQUESTED post-issuance applications can be deleted",
            )
        previous = application.status
        self._repository.update_status(application, "ARCHIVED")
        self._repository.add_history(
            application_id=application.id,
            from_status=previous,
            to_status="ARCHIVED",
            changed_by_subject=current_user.subject,
            comment="Post-issuance draft deleted by user action",
        )
        self._repository.commit()
        return self._serialize_application(application)

    def submit(self, application_id: int, current_user: CurrentUser) -> dict[str, Any]:
        application = self._require_application(application_id)
        self._assert_owner_or_ops(application, current_user)
        if application.status not in EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only DRAFT or REVISION_REQUESTED post-issuance applications can be submitted",
            )
        certificate = self._require_certificate(application.source_certificate_id)
        self._assert_owner_or_ops_for_certificate(certificate, current_user)
        self._assert_no_conflicting_process(certificate.id, ignore_application_id=application.id)
        self._assert_certificate_eligible(certificate, application.action_type)
        payload = self._decode_payload(application.payload_json)
        self._validate_submit_payload(application, payload)
        self._repository.update_payload(application, payload)

        previous = application.status
        self._repository.update_status(application, "SUBMITTED")
        self._repository.add_history(
            application_id=application.id,
            from_status=previous,
            to_status="SUBMITTED",
            changed_by_subject=current_user.subject,
            comment="Post-issuance application submitted",
        )
        self._repository.update_status(application, "REGISTERED")
        self._repository.add_history(
            application_id=application.id,
            from_status="SUBMITTED",
            to_status="REGISTERED",
            changed_by_subject=current_user.subject,
            comment="Post-issuance application registered automatically",
        )
        self._repository.commit()
        return self._serialize_application(application)

    def transition(
        self,
        application_id: int,
        to_status: str,
        current_user: CurrentUser,
        comment: str | None = None,
    ) -> dict[str, Any]:
        normalized_status = to_status.strip().upper()
        if normalized_status not in POST_ISSUANCE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unsupported post-issuance status",
            )

        application = self._require_application(application_id)
        self._assert_owner_or_ops(application, current_user)
        self._assert_transition_actor(normalized_status, current_user)
        allowed = self._allowed_transitions(application.status)
        if normalized_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Transition '{application.status} -> {normalized_status}' is not allowed",
            )

        if normalized_status == "APPROVED":
            certificate = self._require_certificate(application.source_certificate_id)
            self._assert_certificate_eligible(certificate, application.action_type)
            self._apply_approved_action(application, certificate, current_user, comment)
            return self._serialize_application(application)

        if normalized_status == "REJECTED":
            previous = application.status
            self._repository.update_status(application, "REJECTED")
            self._repository.add_history(
                application_id=application.id,
                from_status=previous,
                to_status="REJECTED",
                changed_by_subject=current_user.subject,
                comment=comment or "Post-issuance request rejected by OPS",
            )
            self._repository.update_status(application, "ARCHIVED")
            self._repository.add_history(
                application_id=application.id,
                from_status="REJECTED",
                to_status="ARCHIVED",
                changed_by_subject=current_user.subject,
                comment="Post-issuance application archived after rejection; applicant notification queued",
            )
            self._repository.commit()
            return self._serialize_application(application)

        previous = application.status
        self._repository.update_status(application, normalized_status)
        self._repository.add_history(
            application_id=application.id,
            from_status=previous,
            to_status=normalized_status,
            changed_by_subject=current_user.subject,
            comment=comment,
        )
        self._repository.commit()
        return self._serialize_application(application)

    def attach_basis(
        self,
        application_id: int,
        current_user: CurrentUser,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        application = self._require_application(application_id)
        self._assert_owner_or_ops(application, current_user)
        if application.status not in EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Basis file can only be attached in DRAFT or REVISION_REQUESTED status",
            )
        slot = str(metadata.get("slot", "")).strip()
        if slot != POST_ISSUANCE_BASIS_FILE_SLOT:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Only '{POST_ISSUANCE_BASIS_FILE_SLOT}' slot is supported for post-issuance basis attachment",
            )
        object_key = str(metadata.get("object_key", "")).strip()
        expected_prefix = f"post-issuance/{application_id}/{POST_ISSUANCE_BASIS_FILE_SLOT}/"
        if not object_key.startswith(expected_prefix):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Basis file object_key does not match post-issuance application or slot",
            )

        payload = self._decode_payload(application.payload_json)
        file_slots_raw = payload.get("file_slots", {})
        file_slots = dict(file_slots_raw) if isinstance(file_slots_raw, dict) else {}
        file_slots[POST_ISSUANCE_BASIS_FILE_SLOT] = {
            "slot": POST_ISSUANCE_BASIS_FILE_SLOT,
            "object_key": object_key,
            "file_name": str(metadata.get("file_name", "")).strip(),
            "content_type": str(metadata.get("content_type", "")).strip(),
            "size_bytes": int(metadata.get("size_bytes", 0) or 0),
            "etag": str(metadata.get("etag", "")).strip() or None,
            "attached_at": datetime.now(UTC).isoformat(),
            "attached_by_subject": current_user.subject,
        }
        payload["file_slots"] = file_slots
        self._repository.update_payload(application, payload)
        self._repository.commit()
        return self._serialize_application(application)

    def get_application(self, application_id: int, current_user: CurrentUser) -> dict[str, Any]:
        application = self._require_application(application_id)
        self._assert_owner_or_ops(application, current_user)
        return self._serialize_application(application)

    def get_history(self, application_id: int, current_user: CurrentUser) -> dict[str, Any]:
        application = self._require_application(application_id)
        self._assert_owner_or_ops(application, current_user)
        items = [
            {
                "id": row.id,
                "from_status": row.from_status,
                "to_status": row.to_status,
                "changed_by_subject": row.changed_by_subject,
                "comment": row.comment,
                "changed_at": row.changed_at.isoformat(),
            }
            for row in self._repository.list_history(application_id)
        ]
        return {"application_id": application_id, "total": len(items), "items": items}

    def list_my_applications(self, current_user: CurrentUser, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        applications = self._repository.list_by_subject(current_user.subject, limit=limit, offset=offset)
        items = [self._serialize_application(application) for application in applications]
        return {"total": len(items), "limit": limit, "offset": offset, "items": items}

    def get_ops_queue(
        self,
        current_user: CurrentUser,
        statuses: tuple[str, ...] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        self._require_ops(current_user)
        normalized_statuses = self._normalize_queue_statuses(statuses)
        applications = self._repository.list_by_statuses(normalized_statuses, limit=limit, offset=offset)
        items = [self._serialize_application(application) for application in applications]
        return {
            "total": len(items),
            "limit": limit,
            "offset": offset,
            "statuses": list(normalized_statuses),
            "items": items,
        }

    def _allowed_transitions(self, current_status: str) -> frozenset[str]:
        mapping = {
            "REGISTERED": frozenset({"IN_REVIEW", "APPROVED", "REJECTED"}),
            "IN_REVIEW": frozenset({"REVISION_REQUESTED", "APPROVED", "REJECTED"}),
            "REVISION_REQUESTED": frozenset(),
            "DRAFT": frozenset(),
            "SUBMITTED": frozenset(),
            "APPROVED": frozenset(),
            "REJECTED": frozenset(),
            "ARCHIVED": frozenset(),
            "REGISTRY_UPDATED": frozenset(),
            "COMPLETED": frozenset(),
        }
        return mapping.get(current_status, frozenset())

    def _apply_approved_action(
        self,
        application: PostIssuanceApplication,
        certificate: Certificate,
        current_user: CurrentUser,
        comment: str | None,
    ) -> None:
        previous_application_status = application.status
        self._repository.update_status(application, "APPROVED")
        self._repository.add_history(
            application_id=application.id,
            from_status=previous_application_status,
            to_status="APPROVED",
            changed_by_subject=current_user.subject,
            comment=comment or "Post-issuance request approved by OPS",
        )

        next_certificate_status = CERTIFICATE_STATUS_BY_ACTION[application.action_type]
        self._certificate_repository.add_history(
            certificate_id=certificate.id,
            from_status=certificate.status,
            to_status=next_certificate_status,
            changed_by_subject=current_user.subject,
            comment=f"{self._action_label(application.action_type)} applied by post-issuance #{application.application_number}",
        )
        certificate.status = next_certificate_status
        certificate.updated_at = datetime.now(UTC)
        if application.action_type == "TERMINATE":
            certificate.is_dangerous_product = True

        self._repository.update_status(application, "REGISTRY_UPDATED")
        self._repository.add_history(
            application_id=application.id,
            from_status="APPROVED",
            to_status="REGISTRY_UPDATED",
            changed_by_subject=current_user.subject,
            comment=f"Certificate status changed to {next_certificate_status} and registry updated",
        )
        self._repository.update_status(application, "COMPLETED")
        self._repository.add_history(
            application_id=application.id,
            from_status="REGISTRY_UPDATED",
            to_status="COMPLETED",
            changed_by_subject=current_user.subject,
            comment="Post-issuance process completed; applicant notification queued",
        )
        self._repository.commit()

    def _require_application(self, application_id: int) -> PostIssuanceApplication:
        application = self._repository.get_application(application_id)
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post-issuance application was not found")
        return application

    def _require_certificate(self, certificate_id: int) -> Certificate:
        certificate = self._certificate_repository.get_certificate(certificate_id)
        if certificate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate was not found")
        return certificate

    def _assert_owner_or_ops_for_certificate(self, certificate: Certificate, current_user: CurrentUser) -> None:
        if "OPS" in current_user.roles:
            return
        if certificate.applicant_subject != current_user.subject:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this certificate")

    def _assert_owner_or_ops(self, application: PostIssuanceApplication, current_user: CurrentUser) -> None:
        if "OPS" in current_user.roles:
            return
        if application.applicant_subject != current_user.subject:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied for this post-issuance application",
            )

    def _assert_transition_actor(self, to_status: str, current_user: CurrentUser) -> None:
        if to_status in OPS_REVIEW_STATUSES and "OPS" not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Transition to '{to_status}' requires OPS role",
            )

    def _assert_no_conflicting_process(
        self,
        certificate_id: int,
        ignore_application_id: int | None = None,
        active_processes: list[PostIssuanceApplication] | None = None,
    ) -> None:
        active_processes = active_processes or self._repository.find_active_by_certificate(
            certificate_id,
            ACTIVE_CONFLICT_STATUSES,
        )
        if ignore_application_id is not None:
            active_processes = [item for item in active_processes if item.id != ignore_application_id]
        if active_processes:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="There is already an active post-issuance process for this certificate",
            )

    def _find_conflicting_process(self, certificate_id: int) -> list[PostIssuanceApplication]:
        return self._repository.find_active_by_certificate(certificate_id, ACTIVE_CONFLICT_STATUSES)

    def _find_reusable_editable_process(
        self,
        active_processes: list[PostIssuanceApplication],
        action_type: str,
    ) -> PostIssuanceApplication | None:
        for application in active_processes:
            if application.action_type == action_type and application.status in EDITABLE_STATUSES:
                return application
        return None

    def _assert_certificate_eligible(self, certificate: Certificate, action_type: str) -> None:
        allowed_statuses = ALLOWED_CERTIFICATE_STATUSES_BY_ACTION[action_type]
        if certificate.status not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Certificate status '{certificate.status}' does not allow action '{action_type}'",
            )

    def _normalize_payload(self, application: PostIssuanceApplication, payload: dict[str, Any]) -> dict[str, Any]:
        current_payload = self._decode_payload(application.payload_json)
        merged = {**current_payload, **(payload or {})}
        merged["action_type"] = application.action_type
        merged["request_source"] = application.initiator_role
        merged["source_certificate_id"] = application.source_certificate_id
        merged["source_certificate_number"] = application.source_certificate_number
        merged["source_application_id"] = application.source_application_id
        merged["source_application_number"] = application.source_application_number
        return merged

    def _validate_submit_payload(self, application: PostIssuanceApplication, payload: dict[str, Any]) -> None:
        reason_field = "suspension_reason_code" if application.action_type == "SUSPEND" else "termination_reason_code"
        required_fields = (
            "request_source",
            "reason_detail",
            "note",
            "remediation_deadline",
            "source_certificate_id",
            "source_certificate_number",
            reason_field,
        )
        missing = [field for field in required_fields if payload.get(field) in (None, "", [])]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "Post-issuance payload is incomplete", "missing_fields": missing},
            )
        if int(payload.get("source_certificate_id", 0) or 0) != application.source_certificate_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="source_certificate_id does not match the selected certificate",
            )
        if str(payload.get("source_certificate_number", "")).strip() != application.source_certificate_number:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="source_certificate_number does not match the selected certificate",
            )
        request_source = str(payload.get("request_source", "")).strip()
        if request_source not in {"Applicant", "OPS"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="request_source must be 'Applicant' or 'OPS'",
            )
        if request_source != application.initiator_role:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="request_source does not match the initiator role of this post-issuance application",
            )
        self._validate_reason(application.action_type, str(payload.get(reason_field, "")).strip(), payload)
        self._validate_deadline(str(payload.get("remediation_deadline", "")).strip())
        file_slots = payload.get("file_slots")
        if not isinstance(file_slots, dict) or POST_ISSUANCE_BASIS_FILE_SLOT not in file_slots:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Basis file is required before submitting post-issuance application",
            )

    def _validate_reason(self, action_type: str, reason_code: str, payload: dict[str, Any]) -> None:
        dictionary_code = ACTION_DICTIONARY_BY_TYPE[action_type]
        item = self._reference_data_repository.get_dictionary_item(dictionary_code, reason_code)
        if item is None or not item.get("is_active", False):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Reason '{reason_code}' was not found in dictionary '{dictionary_code}'",
            )
        if action_type == "TERMINATE":
            request_source = str(payload.get("request_source", "")).strip()
            allowed_reason_codes = (
                TERMINATION_REASON_APPLICANT_CODES if request_source == "Applicant" else TERMINATION_REASON_OPS_CODES
            )
            if reason_code not in allowed_reason_codes:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Termination reason '{reason_code}' is not available for request_source '{request_source}'",
                )
        label_field = "suspension_reason_label" if action_type == "SUSPEND" else "termination_reason_label"
        payload[label_field] = item["name"]

    def _validate_deadline(self, value: str) -> None:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="remediation_deadline must be a valid ISO datetime",
            ) from exc

    def _decode_payload(self, payload_json: str | None) -> dict[str, Any]:
        if not payload_json:
            return {}
        try:
            raw = json.loads(payload_json)
        except json.JSONDecodeError:
            return {}
        return raw if isinstance(raw, dict) else {}

    def _build_initial_payload(self, certificate: Certificate, action_type: str, current_user: CurrentUser) -> dict[str, Any]:
        snapshot = self._decode_payload(certificate.snapshot_json)
        payload = snapshot.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        products = payload.get("products")
        product_name = products[0].get("name") if isinstance(products, list) and products and isinstance(products[0], dict) else None
        return {
            "action_type": action_type,
            "request_source": self._resolve_request_source(current_user),
            "source_certificate_id": certificate.id,
            "source_certificate_number": certificate.certificate_number,
            "source_application_id": certificate.source_application_id,
            "source_application_number": certificate.source_application_number,
            "certificate_status": certificate.status,
            "certificate_generated_at": certificate.generated_at.isoformat() if certificate.generated_at else None,
            "applicant_name": payload.get("applicant_name"),
            "applicant_bin": payload.get("applicant_bin"),
            "applicant_address": payload.get("applicant_address"),
            "phone": payload.get("phone"),
            "email": payload.get("email"),
            "actual_address": payload.get("actual_address"),
            "ops_code": payload.get("ops_code"),
            "accreditation_no": payload.get("accreditation_no"),
            "ops_manager": payload.get("ops_manager"),
            "product_name": product_name,
            "suspension_reason_code": "",
            "suspension_reason_label": None,
            "termination_reason_code": "",
            "termination_reason_label": None,
            "reason_detail": "",
            "note": "",
            "remediation_deadline": "",
            "file_slots": {},
        }

    def _serialize_application(self, application: PostIssuanceApplication) -> dict[str, Any]:
        payload = self._decode_payload(application.payload_json)
        certificate = self._require_certificate(application.source_certificate_id)
        return {
            "id": application.id,
            "application_number": application.application_number,
            "source_certificate_id": application.source_certificate_id,
            "source_certificate_number": application.source_certificate_number,
            "source_application_id": application.source_application_id,
            "source_application_number": application.source_application_number,
            "action_type": application.action_type,
            "initiator_role": application.initiator_role,
            "status": application.status,
            "applicant_subject": application.applicant_subject,
            "applicant_username": application.applicant_username,
            "payload": payload,
            "certificate": {
                "id": certificate.id,
                "certificate_number": certificate.certificate_number,
                "status": certificate.status,
                "published_at": certificate.published_at.isoformat() if certificate.published_at else None,
                "is_dangerous_product": certificate.is_dangerous_product,
            },
            "created_at": application.created_at.isoformat(),
            "updated_at": application.updated_at.isoformat(),
        }

    def _normalize_queue_statuses(self, raw_statuses: tuple[str, ...] | None) -> tuple[str, ...]:
        base = raw_statuses or OPS_QUEUE_DEFAULT_STATUSES
        normalized: list[str] = []
        for item in base:
            status_name = item.strip().upper()
            if not status_name:
                continue
            if status_name not in POST_ISSUANCE_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Queue status '{status_name}' is not supported",
                )
            normalized.append(status_name)
        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one post-issuance queue status must be provided",
            )
        return tuple(dict.fromkeys(normalized))

    def _normalize_action_type(self, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in ACTION_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="action_type must be SUSPEND or TERMINATE",
            )
        return normalized

    def _resolve_request_source(self, current_user: CurrentUser) -> str:
        if "OPS" in current_user.roles:
            return "OPS"
        return "Applicant"

    def _require_ops(self, current_user: CurrentUser) -> None:
        if "OPS" not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only OPS role can perform this action",
            )

    def _new_application_number(self) -> str:
        now = datetime.now(UTC)
        return f"KZ/PI/{now:%Y%m%d}/{randbelow(10000):04d}"

    def _action_label(self, action_type: str) -> str:
        return "Приостановление" if action_type == "SUSPEND" else "Прекращение"
