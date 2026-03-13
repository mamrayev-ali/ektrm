from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.repositories.certificate_repository import CertificateRepository
from app.services.certificate_signature_validation import (
    CertificateSignatureValidator,
    build_certificate_signature_validator,
)
from app.services.certificate_service import CertificateService

router = APIRouter(prefix="/certificates", tags=["certificates"])


class CertificateSignRequest(BaseModel):
    operation_id: str = Field(min_length=8, max_length=64)
    signature_mode: str = Field(default="detached", pattern="^(detached|attached)$")
    payload_base64: str = Field(min_length=8)
    payload_sha256_hex: str | None = Field(default=None, min_length=64, max_length=64)
    signature_cms_base64: str = Field(min_length=8)
    comment: str | None = Field(default=None, max_length=2000)
    client_meta: dict[str, object] | None = Field(default=None)


class CertificateSignPrepareRequest(BaseModel):
    signer_kind: str = Field(default="signAny", pattern="^signAny$")


def get_signature_validator() -> CertificateSignatureValidator:
    return build_certificate_signature_validator()


def _get_service(
    session: Session = Depends(get_session),
    signature_validator: CertificateSignatureValidator = Depends(get_signature_validator),
) -> CertificateService:
    return CertificateService(
        CertificateRepository(session),
        signature_validator=signature_validator,
    )


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


@router.get("/{certificate_id}/download")
def download_certificate(
    certificate_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: CertificateService = Depends(_get_service),
) -> Response:
    pdf_bytes, file_name = service.download_certificate_pdf(certificate_id=certificate_id, current_user=current_user)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


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
        operation_id=request.operation_id,
        payload_base64=request.payload_base64,
        payload_sha256_hex=request.payload_sha256_hex,
        signature_cms_base64=request.signature_cms_base64,
        signature_mode=request.signature_mode,
        client_meta=request.client_meta,
        comment=request.comment,
    )


@router.post("/{certificate_id}/sign/prepare")
def prepare_certificate_sign(
    certificate_id: int,
    request: CertificateSignPrepareRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: CertificateService = Depends(_get_service),
) -> dict[str, object]:
    return service.prepare_signature(
        certificate_id=certificate_id,
        current_user=current_user,
        signer_kind=request.signer_kind,
    )
