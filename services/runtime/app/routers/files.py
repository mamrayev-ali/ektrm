from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.services.file_slot_service import FileSlotService, build_file_slot_service

router = APIRouter(prefix="/files", tags=["files"])


class SlotUploadRequest(BaseModel):
    application_id: int | None = Field(default=None, gt=0)
    entity_kind: str | None = Field(default=None, min_length=3, max_length=32)
    entity_id: int | None = Field(default=None, gt=0)
    slot: str = Field(min_length=2, max_length=64)
    file_name: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(min_length=4)
    content_type: str | None = Field(default=None, max_length=255)


@lru_cache(maxsize=1)
def _cached_service() -> FileSlotService:
    return build_file_slot_service()


def get_file_slot_service() -> FileSlotService:
    return _cached_service()


@router.post("/slots/upload")
def upload_slot_file(
    request: SlotUploadRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: FileSlotService = Depends(get_file_slot_service),
) -> dict[str, object]:
    return service.upload_slot_file(
        current_user=current_user,
        slot=request.slot,
        file_name=request.file_name,
        content_base64=request.content_base64,
        content_type=request.content_type,
        application_id=request.application_id,
        entity_kind=request.entity_kind,
        entity_id=request.entity_id,
    )
