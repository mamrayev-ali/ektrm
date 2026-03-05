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
ALLOWED_SLOTS = frozenset({PROTOCOL_FILE_SLOT})
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
        application_id: int,
        slot: str,
        file_name: str,
        content_base64: str,
        content_type: str | None = None,
    ) -> dict[str, object]:
        if "OPS" not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only OPS role can upload protocol files",
            )

        normalized_slot = slot.strip()
        if normalized_slot not in ALLOWED_SLOTS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported slot '{normalized_slot}'",
            )

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
        object_key = f"applications/{application_id}/{normalized_slot}/{timestamp}-{token_hex(6)}-{safe_file_name}"
        resolved_content_type = (content_type or DEFAULT_CONTENT_TYPE).strip() or DEFAULT_CONTENT_TYPE
        etag = self._storage.put_object(object_key, content, resolved_content_type)

        return {
            "application_id": application_id,
            "slot": normalized_slot,
            "object_key": object_key,
            "file_name": normalized_name,
            "content_type": resolved_content_type,
            "size_bytes": len(content),
            "etag": etag,
            "uploaded_by_subject": current_user.subject,
            "uploaded_at": datetime.now(UTC).isoformat(),
        }


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
