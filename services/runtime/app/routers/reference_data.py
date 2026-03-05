from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.repositories.reference_data_repository import ReferenceDataRepository
from app.services.reference_data_service import ReferenceDataService

router = APIRouter(prefix="/reference-data", tags=["reference-data"])


def _get_service(session: Session = Depends(get_session)) -> ReferenceDataService:
    return ReferenceDataService(ReferenceDataRepository(session))


@router.get("/dictionaries")
def list_dictionaries(
    _: CurrentUser = Depends(get_current_user),
    service: ReferenceDataService = Depends(_get_service),
) -> dict[str, object]:
    return service.list_dictionaries()


@router.get("/dictionaries/{dictionary_code}/items")
def list_dictionary_items(
    dictionary_code: str,
    _: CurrentUser = Depends(get_current_user),
    service: ReferenceDataService = Depends(_get_service),
) -> dict[str, object]:
    return service.list_dictionary_items(dictionary_code=dictionary_code)


@router.get("/ops-registry")
def list_ops_registry(
    limit: int = Query(default=100, ge=1, le=500),
    search: str | None = Query(default=None, min_length=2, max_length=255),
    _: CurrentUser = Depends(get_current_user),
    service: ReferenceDataService = Depends(_get_service),
) -> dict[str, object]:
    return service.list_ops_registry(limit=limit, search=search)


@router.get("/accreditation-attestats")
def list_accreditation_attestats(
    limit: int = Query(default=100, ge=1, le=500),
    search: str | None = Query(default=None, min_length=2, max_length=255),
    _: CurrentUser = Depends(get_current_user),
    service: ReferenceDataService = Depends(_get_service),
) -> dict[str, object]:
    return service.list_accreditation_attestats(limit=limit, search=search)
