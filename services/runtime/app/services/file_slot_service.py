from __future__ import annotations

import base64
import os
import re
from datetime import UTC, datetime
from io import BytesIO
from secrets import token_hex
from typing import Protocol

from fastapi import HTTPException, status

from app.auth import CurrentUser

PROTOCOL_FILE_SLOT = "protocol_test_report"
POST_ISSUANCE_BASIS_FILE_SLOT = "post_issuance_basis"
APPLICATION_SCAN_FILE_SLOT = "application_scan"
TECHNICAL_DOCUMENTATION_FILE_SLOT = "technical_documentation"
STANDARDS_LIST_FILE_SLOT = "standards_list"
MANUFACTURE_DOCUMENTS_FILE_SLOT = "manufacture_documents"
QMS_CERTIFICATE_FILE_SLOT = "qms_certificate"
REPORTS_FILE_SLOT = "reports"
CRITICAL_COMPONENTS_CERTIFICATE_FILE_SLOT = "critical_components_certificate"
FOREIGN_MANUFACTURER_CONTRACT_FILE_SLOT = "foreign_manufacturer_contract"
PRODUCT_COMPLIANCE_DOCUMENTS_FILE_SLOT = "product_compliance_documents"
OTHER_DOCUMENTS_FILE_SLOT = "other_documents"
APPLICATION_ENTITY_KIND = "application"
POST_ISSUANCE_ENTITY_KIND = "post_issuance"
APPLICATION_FILE_SLOTS = frozenset(
    {
        PROTOCOL_FILE_SLOT,
        APPLICATION_SCAN_FILE_SLOT,
        TECHNICAL_DOCUMENTATION_FILE_SLOT,
        STANDARDS_LIST_FILE_SLOT,
        MANUFACTURE_DOCUMENTS_FILE_SLOT,
        QMS_CERTIFICATE_FILE_SLOT,
        REPORTS_FILE_SLOT,
        CRITICAL_COMPONENTS_CERTIFICATE_FILE_SLOT,
        FOREIGN_MANUFACTURER_CONTRACT_FILE_SLOT,
        PRODUCT_COMPLIANCE_DOCUMENTS_FILE_SLOT,
        OTHER_DOCUMENTS_FILE_SLOT,
    }
)
APPLICANT_DOCUMENT_FILE_SLOTS = frozenset(APPLICATION_FILE_SLOTS - {PROTOCOL_FILE_SLOT})
ALLOWED_SLOTS = frozenset(APPLICATION_FILE_SLOTS | {POST_ISSUANCE_BASIS_FILE_SLOT})
ALLOWED_EXTENSIONS = frozenset({".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"})
DEFAULT_CONTENT_TYPE = "application/octet-stream"


class ObjectStorage(Protocol):
    def put_object(self, key: str, content: bytes, content_type: str) -> str | None:
        ...


class MinioObjectStorage:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool,
    ) -> None:
        from minio import Minio
        from minio.error import S3Error

        self._s3_error_class = S3Error
        self._bucket = bucket
        self._client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def put_object(self, key: str, content: bytes, content_type: str) -> str | None:
        try:
            result = self._client.put_object(
                bucket_name=self._bucket,
                object_name=key,
                data=BytesIO(content),
                length=len(content),
                content_type=content_type,
            )
        except self._s3_error_class as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File storage is temporarily unavailable",
            ) from exc
        return result.etag


class FileSlotService:
    def __init__(self, storage: ObjectStorage, max_file_size_bytes: int) -> None:
        self._storage = storage
        self._max_file_size_bytes = max_file_size_bytes

    def upload_slot_file(
        self,
        current_user: CurrentUser,
        slot: str,
        file_name: str,
        content_base64: str,
        content_type: str | None = None,
        application_id: int | None = None,
        entity_kind: str | None = None,
        entity_id: int | None = None,
    ) -> dict[str, object]:
        normalized_slot = slot.strip()
        if normalized_slot not in ALLOWED_SLOTS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported slot '{normalized_slot}'",
            )
        if normalized_slot == PROTOCOL_FILE_SLOT:
            if "OPS" not in current_user.roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only OPS role can upload protocol files",
                )
        elif "OPS" not in current_user.roles and "Applicant" not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Applicant or OPS role can upload supported application or post-issuance files",
            )

        resolved_entity_kind, resolved_entity_id, object_prefix = self._resolve_target(
            application_id=application_id,
            entity_kind=entity_kind,
            entity_id=entity_id,
        )
        self._validate_slot_target(normalized_slot, resolved_entity_kind)

        normalized_name = file_name.strip()
        if not normalized_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="file_name is required",
            )

        extension = os.path.splitext(normalized_name.lower())[1]
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File extension '{extension}' is not allowed",
            )

        try:
            content = base64.b64decode(content_base64, validate=True)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="content_base64 is invalid",
            ) from exc

        if not content:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded content is empty",
            )
        if len(content) > self._max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds max size {self._max_file_size_bytes} bytes",
            )

        safe_file_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", normalized_name)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        object_key = f"{object_prefix}/{resolved_entity_id}/{normalized_slot}/{timestamp}-{token_hex(6)}-{safe_file_name}"
        resolved_content_type = (content_type or DEFAULT_CONTENT_TYPE).strip() or DEFAULT_CONTENT_TYPE
        etag = self._storage.put_object(object_key, content, resolved_content_type)

        response: dict[str, object] = {
            "entity_kind": resolved_entity_kind,
            "entity_id": resolved_entity_id,
            "slot": normalized_slot,
            "object_key": object_key,
            "file_name": normalized_name,
            "content_type": resolved_content_type,
            "size_bytes": len(content),
            "etag": etag,
            "uploaded_by_subject": current_user.subject,
            "uploaded_at": datetime.now(UTC).isoformat(),
        }
        if resolved_entity_kind == APPLICATION_ENTITY_KIND:
            response["application_id"] = resolved_entity_id
        if resolved_entity_kind == POST_ISSUANCE_ENTITY_KIND:
            response["post_issuance_id"] = resolved_entity_id
        return response

    def _resolve_target(
        self,
        application_id: int | None,
        entity_kind: str | None,
        entity_id: int | None,
    ) -> tuple[str, int, str]:
        if application_id is not None:
            return APPLICATION_ENTITY_KIND, application_id, "applications"
        normalized_kind = str(entity_kind or "").strip().lower()
        if normalized_kind not in {APPLICATION_ENTITY_KIND, POST_ISSUANCE_ENTITY_KIND}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="entity_kind must be 'application' or 'post_issuance'",
            )
        if entity_id is None or entity_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="entity_id must be a positive integer",
            )
        object_prefix = "applications" if normalized_kind == APPLICATION_ENTITY_KIND else "post-issuance"
        return normalized_kind, entity_id, object_prefix

    def _validate_slot_target(self, slot: str, entity_kind: str) -> None:
        if slot in APPLICATION_FILE_SLOTS and entity_kind != APPLICATION_ENTITY_KIND:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Slot '{slot}' requires entity_kind 'application'",
            )
        if slot == POST_ISSUANCE_BASIS_FILE_SLOT and entity_kind != POST_ISSUANCE_ENTITY_KIND:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Slot '{slot}' requires entity_kind 'post_issuance'",
            )


def build_file_slot_service() -> FileSlotService:
    endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    bucket = os.getenv("MINIO_BUCKET_FILES", "ektrm-files")
    secure = os.getenv("MINIO_SECURE", "false").strip().lower() in {"1", "true", "yes", "on"}
    max_size = int(os.getenv("FILE_UPLOAD_MAX_BYTES", str(25 * 1024 * 1024)))
    storage = MinioObjectStorage(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        bucket=bucket,
        secure=secure,
    )
    return FileSlotService(storage=storage, max_file_size_bytes=max_size)
