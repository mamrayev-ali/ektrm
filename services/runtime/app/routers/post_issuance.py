from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.repositories.certificate_repository import CertificateRepository
from app.repositories.post_issuance_repository import PostIssuanceRepository
from app.repositories.reference_data_repository import ReferenceDataRepository
from app.services.post_issuance_service import PostIssuanceService

router = APIRouter(prefix="/post-issuance", tags=["post-issuance"])


class CreateDraftRequest(BaseModel):
    source_certificate_id: int = Field(gt=0)
    action_type: str = Field(min_length=7, max_length=16)


class TransitionRequest(BaseModel):
    to_status: str = Field(min_length=2, max_length=32)
    comment: str | None = Field(default=None, max_length=2000)


class BasisAttachRequest(BaseModel):
    slot: str = Field(min_length=2, max_length=64)
    object_key: str = Field(min_length=5, max_length=1024)
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=255)
    size_bytes: int = Field(ge=1, le=25 * 1024 * 1024)
    etag: str | None = Field(default=None, max_length=128)


def _get_service(session: Session = Depends(get_session)) -> PostIssuanceService:
    return PostIssuanceService(
        repository=PostIssuanceRepository(session),
        certificate_repository=CertificateRepository(session),
        reference_data_repository=ReferenceDataRepository(session),
    )


@router.post("/drafts")
def create_draft(
    request: CreateDraftRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: PostIssuanceService = Depends(_get_service),
) -> dict[str, Any]:
    return service.create_draft(
        source_certificate_id=request.source_certificate_id,
        action_type=request.action_type,
        current_user=current_user,
    )


@router.put("/{application_id}/draft")
def update_draft(
    application_id: int,
    payload: dict[str, Any] = Body(default_factory=dict),
    current_user: CurrentUser = Depends(get_current_user),
    service: PostIssuanceService = Depends(_get_service),
) -> dict[str, Any]:
    return service.update_draft(application_id=application_id, payload=payload, current_user=current_user)


@router.post("/{application_id}/submit")
def submit_application(
    application_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: PostIssuanceService = Depends(_get_service),
) -> dict[str, Any]:
    return service.submit(application_id=application_id, current_user=current_user)


@router.post("/{application_id}/transitions")
def transition_application(
    application_id: int,
    request: TransitionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: PostIssuanceService = Depends(_get_service),
) -> dict[str, Any]:
    return service.transition(
        application_id=application_id,
        to_status=request.to_status,
        current_user=current_user,
        comment=request.comment,
    )


@router.post("/{application_id}/basis/attach")
def attach_basis(
    application_id: int,
    request: BasisAttachRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: PostIssuanceService = Depends(_get_service),
) -> dict[str, Any]:
    return service.attach_basis(
        application_id=application_id,
        current_user=current_user,
        metadata=request.model_dump(),
    )


@router.get("/mine")
def get_my_applications(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    service: PostIssuanceService = Depends(_get_service),
) -> dict[str, Any]:
    return service.list_my_applications(current_user=current_user, limit=limit, offset=offset)


@router.get("/ops/queue")
def get_ops_queue(
    statuses: str | None = Query(default=None, description="CSV statuses for OPS queue filter"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    service: PostIssuanceService = Depends(_get_service),
) -> dict[str, Any]:
    parsed_statuses = tuple(item for item in (statuses or "").split(",") if item.strip()) or None
    return service.get_ops_queue(
        current_user=current_user,
        statuses=parsed_statuses,
        limit=limit,
        offset=offset,
    )


@router.get("/{application_id}")
def get_application(
    application_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: PostIssuanceService = Depends(_get_service),
) -> dict[str, Any]:
    return service.get_application(application_id=application_id, current_user=current_user)


@router.get("/{application_id}/history")
def get_application_history(
    application_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: PostIssuanceService = Depends(_get_service),
) -> dict[str, Any]:
    return service.get_history(application_id=application_id, current_user=current_user)
