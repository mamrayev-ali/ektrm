from __future__ import annotations

import json
from datetime import UTC, datetime
from secrets import randbelow
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.auth import CurrentUser
from app.models.application import CertApplication
from app.repositories.application_repository import ApplicationRepository

ORDER3_STATUSES = frozenset(
    {
        "DRAFT",
        "SUBMITTED",
        "REGISTERED",
        "IN_REVIEW",
        "REVISION_REQUESTED",
        "PROTOCOL_ATTACHED",
        "APPROVED",
        "REJECTED",
        "ARCHIVED",
        "COMPLETED",
    }
)

TRANSITIONS: dict[str, frozenset[str]] = {
    "DRAFT": frozenset({"SUBMITTED"}),
    "SUBMITTED": frozenset({"REGISTERED"}),
    "REGISTERED": frozenset({"IN_REVIEW"}),
    "IN_REVIEW": frozenset({"REVISION_REQUESTED", "PROTOCOL_ATTACHED"}),
    "REVISION_REQUESTED": frozenset({"IN_REVIEW"}),
    "PROTOCOL_ATTACHED": frozenset({"APPROVED", "REJECTED"}),
    "REJECTED": frozenset({"ARCHIVED"}),
    "APPROVED": frozenset({"COMPLETED"}),
    "ARCHIVED": frozenset(),
    "COMPLETED": frozenset(),
}

REQUIRED_SUBMIT_FIELDS = (
    "applicant_name",
    "applicant_bin",
    "applicant_address",
    "ops_code",
    "cert_scheme_code",
    "products",
)

DELETABLE_DRAFT_STATUSES = frozenset({"DRAFT", "REVISION_REQUESTED"})
OPS_REVIEW_STATUSES = frozenset(
    {
        "REGISTERED",
        "IN_REVIEW",
        "REVISION_REQUESTED",
        "PROTOCOL_ATTACHED",
        "APPROVED",
        "REJECTED",
        "ARCHIVED",
        "COMPLETED",
    }
)
DEFAULT_OPS_QUEUE_STATUSES = ("SUBMITTED", "REGISTERED", "IN_REVIEW", "PROTOCOL_ATTACHED")
PROTOCOL_FILE_SLOT = "protocol_test_report"


class ApplicationStateService:
    def __init__(self, repository: ApplicationRepository) -> None:
        self._repository = repository

    def create_draft(self, payload: dict[str, Any], current_user: CurrentUser) -> dict[str, Any]:
        application_number = self._new_application_number()
        try:
            application = self._repository.create_application(
                application_number=application_number,
                applicant_subject=current_user.subject,
                applicant_username=current_user.username,
                payload=payload,
            )
            self._repository.add_history(
                application_id=application.id,
                from_status=None,
                to_status="DRAFT",
                changed_by_subject=current_user.subject,
                comment="Draft created",
            )
            self._repository.commit()
            return self._serialize_application(application)
        except IntegrityError as exc:
            self._repository.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Application number must be unique",
            ) from exc

    def update_draft(self, application_id: int, payload: dict[str, Any], current_user: CurrentUser) -> dict[str, Any]:
        application = self._require_application(application_id)
        if application.status not in {"DRAFT", "REVISION_REQUESTED"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Draft can only be edited in DRAFT or REVISION_REQUESTED status",
            )
        self._assert_owner_or_ops(application, current_user)
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
        history = self._repository.list_history(application_id)
        items = [
            {
                "id": row.id,
                "from_status": row.from_status,
                "to_status": row.to_status,
                "changed_by_subject": row.changed_by_subject,
                "comment": row.comment,
                "changed_at": row.changed_at.isoformat(),
            }
            for row in history
        ]
        return {"application_id": application_id, "total": len(items), "items": items}

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

    def delete_draft(self, application_id: int, current_user: CurrentUser) -> dict[str, Any]:
        application = self._require_application(application_id)
        self._assert_owner_or_ops(application, current_user)
        if application.status not in DELETABLE_DRAFT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft applications can be deleted",
            )
        previous = application.status
        self._repository.update_status(application, "ARCHIVED")
        self._repository.add_history(
            application_id=application.id,
            from_status=previous,
            to_status="ARCHIVED",
            changed_by_subject=current_user.subject,
            comment="Draft deleted",
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
        normalized = to_status.strip().upper()
        if normalized not in ORDER3_STATUSES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported status")

        application = self._require_application(application_id)
        self._assert_owner_or_ops(application, current_user)
        self._assert_transition_actor(normalized, current_user)
        allowed = TRANSITIONS[application.status]
        if normalized not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Transition '{application.status} -> {normalized}' is not allowed",
            )

        payload = self._decode_payload(application.payload_json)
        if normalized == "SUBMITTED":
            self._validate_submit_payload(payload)

        previous = application.status
        self._repository.update_status(application, normalized)
        self._repository.add_history(
            application_id=application.id,
            from_status=previous,
            to_status=normalized,
            changed_by_subject=current_user.subject,
            comment=comment,
        )
        if normalized == "REJECTED":
            self._repository.update_status(application, "ARCHIVED")
            self._repository.add_history(
                application_id=application.id,
                from_status="REJECTED",
                to_status="ARCHIVED",
                changed_by_subject=current_user.subject,
                comment="Application archived after rejection; applicant notification queued",
            )
        self._repository.commit()
        return self._serialize_application(application)

    def attach_protocol(
        self,
        application_id: int,
        current_user: CurrentUser,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_ops(current_user)
        application = self._require_application(application_id)
        if application.status != "IN_REVIEW":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Protocol can only be attached when application is IN_REVIEW",
            )

        slot = str(metadata.get("slot", "")).strip()
        if slot != PROTOCOL_FILE_SLOT:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Only '{PROTOCOL_FILE_SLOT}' slot is supported for protocol attachment",
            )

        object_key = str(metadata.get("object_key", "")).strip()
        expected_prefix = f"applications/{application_id}/{PROTOCOL_FILE_SLOT}/"
        if not object_key.startswith(expected_prefix):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Protocol file object_key does not match application or slot",
            )

        payload = self._decode_payload(application.payload_json)
        file_slots_raw = payload.get("file_slots", {})
        file_slots = dict(file_slots_raw) if isinstance(file_slots_raw, dict) else {}
        file_slots[PROTOCOL_FILE_SLOT] = {
            "slot": PROTOCOL_FILE_SLOT,
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
        self._repository.update_status(application, "PROTOCOL_ATTACHED")
        self._repository.add_history(
            application_id=application.id,
            from_status="IN_REVIEW",
            to_status="PROTOCOL_ATTACHED",
            changed_by_subject=current_user.subject,
            comment=f"Protocol attached: {file_slots[PROTOCOL_FILE_SLOT]['file_name']}",
        )
        self._repository.commit()
        return self._serialize_application(application)

    def _require_application(self, application_id: int) -> CertApplication:
        application = self._repository.get_application(application_id)
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application was not found")
        return application

    def _assert_owner_or_ops(self, application: CertApplication, current_user: CurrentUser) -> None:
        if "OPS" in current_user.roles:
            return
        if application.applicant_subject != current_user.subject:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this application")

    def _require_ops(self, current_user: CurrentUser) -> None:
        if "OPS" not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only OPS role can perform this action",
            )

    def _assert_transition_actor(self, to_status: str, current_user: CurrentUser) -> None:
        if to_status in OPS_REVIEW_STATUSES and "OPS" not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Transition to '{to_status}' requires OPS role",
            )

    def _validate_submit_payload(self, payload: dict[str, Any]) -> None:
        missing = [field for field in REQUIRED_SUBMIT_FIELDS if field not in payload or payload[field] in (None, "", [])]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Submit payload is incomplete",
                    "missing_fields": missing,
                },
            )

    def _serialize_application(self, application: CertApplication) -> dict[str, Any]:
        return {
            "id": application.id,
            "application_number": application.application_number,
            "status": application.status,
            "applicant_subject": application.applicant_subject,
            "applicant_username": application.applicant_username,
            "payload": self._decode_payload(application.payload_json),
            "created_at": application.created_at.isoformat(),
            "updated_at": application.updated_at.isoformat(),
        }

    def _decode_payload(self, payload_json: str | None) -> dict[str, Any]:
        if not payload_json:
            return {}
        try:
            data = json.loads(payload_json)
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        return data

    def _normalize_queue_statuses(self, raw_statuses: tuple[str, ...] | None) -> tuple[str, ...]:
        base = raw_statuses or DEFAULT_OPS_QUEUE_STATUSES
        normalized: list[str] = []
        for item in base:
            status_name = item.strip().upper()
            if not status_name:
                continue
            if status_name not in ORDER3_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Queue status '{status_name}' is not supported",
                )
            normalized.append(status_name)

        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one queue status must be provided",
            )
        return tuple(dict.fromkeys(normalized))

    def _new_application_number(self) -> str:
        now = datetime.now(UTC)
        suffix = randbelow(10000)
        return f"KZ/{now:%Y%m%d}/{suffix:04d}"
