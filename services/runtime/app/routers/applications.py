from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.repositories.application_repository import ApplicationRepository
from app.services.application_state_service import ApplicationStateService

router = APIRouter(prefix="/applications", tags=["applications"])


class TransitionRequest(BaseModel):
    to_status: str = Field(min_length=2, max_length=32)
    comment: str | None = Field(default=None, max_length=2000)


def _get_service(session: Session = Depends(get_session)) -> ApplicationStateService:
    return ApplicationStateService(ApplicationRepository(session))


@router.post("/drafts")
def create_draft(
    payload: dict[str, Any] = Body(default_factory=dict),
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationStateService = Depends(_get_service),
) -> dict[str, Any]:
    return service.create_draft(payload=payload, current_user=current_user)


@router.put("/{application_id}/draft")
def update_draft(
    application_id: int,
    payload: dict[str, Any] = Body(default_factory=dict),
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationStateService = Depends(_get_service),
) -> dict[str, Any]:
    return service.update_draft(application_id=application_id, payload=payload, current_user=current_user)


@router.post("/{application_id}/submit")
def submit_application(
    application_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationStateService = Depends(_get_service),
) -> dict[str, Any]:
    return service.transition(
        application_id=application_id,
        to_status="SUBMITTED",
        current_user=current_user,
        comment="Application submitted",
    )


@router.post("/{application_id}/transitions")
def transition_application(
    application_id: int,
    request: TransitionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationStateService = Depends(_get_service),
) -> dict[str, Any]:
    return service.transition(
        application_id=application_id,
        to_status=request.to_status,
        current_user=current_user,
        comment=request.comment,
    )


@router.get("/{application_id}")
def get_application(
    application_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationStateService = Depends(_get_service),
) -> dict[str, Any]:
    return service.get_application(application_id=application_id, current_user=current_user)


@router.get("/{application_id}/history")
def get_application_history(
    application_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationStateService = Depends(_get_service),
) -> dict[str, Any]:
    return service.get_history(application_id=application_id, current_user=current_user)
