from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.repositories.certificate_repository import CertificateRepository
from app.services.certificate_service import CertificateService

router = APIRouter(prefix="/registry", tags=["registry"])


def _get_service(session: Session = Depends(get_session)) -> CertificateService:
    return CertificateService(CertificateRepository(session))


@router.get("/internal")
def get_internal_registry(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=128),
    current_user: CurrentUser = Depends(get_current_user),
    service: CertificateService = Depends(_get_service),
) -> dict[str, object]:
    return service.list_internal_registry(
        current_user=current_user,
        limit=limit,
        offset=offset,
        search=search,
    )


@router.get("/public")
def get_public_registry(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=128),
    service: CertificateService = Depends(_get_service),
) -> dict[str, object]:
    return service.list_public_registry(limit=limit, offset=offset, search=search)
