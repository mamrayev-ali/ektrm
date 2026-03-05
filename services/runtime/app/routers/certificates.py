from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.repositories.certificate_repository import CertificateRepository
from app.services.certificate_service import CertificateService

router = APIRouter(prefix="/certificates", tags=["certificates"])


class CertificateSignRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


def _get_service(session: Session = Depends(get_session)) -> CertificateService:
    return CertificateService(CertificateRepository(session))


@router.get("/by-application/{application_id}")
def get_certificate_by_application(
    application_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: CertificateService = Depends(_get_service),
) -> dict[str, object]:
    return service.get_certificate_by_application(application_id=application_id, current_user=current_user)


@router.get("/{certificate_id}")
def get_certificate(
    certificate_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: CertificateService = Depends(_get_service),
) -> dict[str, object]:
    return service.get_certificate(certificate_id=certificate_id, current_user=current_user)


@router.post("/{certificate_id}/sign")
def sign_certificate(
    certificate_id: int,
    request: CertificateSignRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: CertificateService = Depends(_get_service),
) -> dict[str, object]:
    return service.sign_and_publish(
        certificate_id=certificate_id,
        current_user=current_user,
        comment=request.comment,
    )
