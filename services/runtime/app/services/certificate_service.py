from __future__ import annotations

import json
import textwrap
from datetime import UTC, datetime
from datetime import timedelta
from typing import Any

from fastapi import HTTPException, status

from app.auth import CurrentUser
from app.models.application import CertApplication
from app.models.certificate import Certificate
from app.repositories.certificate_repository import CertificateRepository


class CertificateService:
    def __init__(self, repository: CertificateRepository) -> None:
        self._repository = repository

    def generate_for_approved_application(
        self,
        application: CertApplication,
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        if application.status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Certificate can be generated only for APPROVED applications",
            )

        existing = self._repository.get_by_source_application(application.id)
        if existing is not None:
            return self._serialize_certificate(existing)

        snapshot = self._build_snapshot(application)
        certificate = self._repository.create_certificate(
            certificate_number=self._new_certificate_number(application.id),
            source_application_id=application.id,
            source_application_number=application.application_number,
            applicant_subject=application.applicant_subject,
            applicant_username=application.applicant_username,
            snapshot=snapshot,
            generated_by_subject=current_user.subject,
        )
        self._repository.add_history(
            certificate_id=certificate.id,
            from_status=None,
            to_status="GENERATED",
            changed_by_subject=current_user.subject,
            comment=f"Certificate generated from application {application.application_number}",
        )
        return self._serialize_certificate(certificate)

    def sign_and_publish(
        self,
        certificate_id: int,
        current_user: CurrentUser,
        comment: str | None = None,
    ) -> dict[str, Any]:
        self._require_ops(current_user)
        certificate = self._repository.get_certificate(certificate_id)
        if certificate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate was not found")
        if certificate.status != "GENERATED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only GENERATED certificate can be signed and published",
            )

        now = datetime.now(UTC)
        certificate.signed_by_subject = current_user.subject
        certificate.signed_at = now

        self._repository.add_history(
            certificate_id=certificate.id,
            from_status="GENERATED",
            to_status="SIGNED",
            changed_by_subject=current_user.subject,
            comment=comment or "Certificate mock-signed by OPS",
        )
        certificate.status = "SIGNED"

        self._repository.add_history(
            certificate_id=certificate.id,
            from_status="SIGNED",
            to_status="PUBLISHED",
            changed_by_subject=current_user.subject,
            comment="Certificate published to internal and public registries",
        )
        certificate.status = "PUBLISHED"
        certificate.published_at = now

        self._repository.add_publication(
            certificate_id=certificate.id,
            visibility="INTERNAL",
            is_public=False,
            published_by_subject=current_user.subject,
            comment="Internal registry publication event",
        )
        self._repository.add_publication(
            certificate_id=certificate.id,
            visibility="PUBLIC",
            is_public=True,
            published_by_subject=current_user.subject,
            comment="Public read-only registry publication event",
        )

        self._repository.add_history(
            certificate_id=certificate.id,
            from_status="PUBLISHED",
            to_status="ACTIVE",
            changed_by_subject=current_user.subject,
            comment="Certificate is active after publication",
        )
        certificate.status = "ACTIVE"

        try:
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise
        return self._serialize_certificate(certificate)

    def get_certificate(self, certificate_id: int, current_user: CurrentUser) -> dict[str, Any]:
        certificate = self._repository.get_certificate(certificate_id)
        if certificate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate was not found")
        self._assert_owner_or_ops(certificate, current_user)
        return self._serialize_certificate(certificate)

    def get_certificate_by_application(self, application_id: int, current_user: CurrentUser) -> dict[str, Any]:
        certificate = self._repository.get_by_source_application(application_id)
        if certificate is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificate for the application was not found",
            )
        self._assert_owner_or_ops(certificate, current_user)
        return self._serialize_certificate(certificate)

    def download_certificate_pdf(self, certificate_id: int, current_user: CurrentUser) -> tuple[bytes, str]:
        certificate = self._repository.get_certificate(certificate_id)
        if certificate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate was not found")
        self._assert_owner_or_ops(certificate, current_user)
        pdf_bytes = self._build_certificate_pdf(certificate)
        safe_number = certificate.certificate_number.replace("/", "_")
        return pdf_bytes, f"{safe_number}.pdf"

    def list_internal_registry(
        self,
        current_user: CurrentUser,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
    ) -> dict[str, Any]:
        if "OPS" in current_user.roles:
            applicant_subject = None
        elif "Applicant" in current_user.roles:
            applicant_subject = current_user.subject
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Applicant or OPS role can view internal registry",
            )

        certificates = self._repository.list_internal_registry(
            limit=limit,
            offset=offset,
            search=search,
            applicant_subject=applicant_subject,
        )
        items = [self._serialize_registry_item(certificate, include_subject=True) for certificate in certificates]
        return {
            "total": len(items),
            "limit": limit,
            "offset": offset,
            "items": items,
        }

    def list_public_registry(
        self,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
    ) -> dict[str, Any]:
        certificates = self._repository.list_public_registry(limit=limit, offset=offset, search=search)
        items = [self._serialize_registry_item(certificate, include_subject=False) for certificate in certificates]
        return {
            "total": len(items),
            "limit": limit,
            "offset": offset,
            "items": items,
        }

    def _assert_owner_or_ops(self, certificate: Certificate, current_user: CurrentUser) -> None:
        if "OPS" in current_user.roles:
            return
        if certificate.applicant_subject != current_user.subject:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this certificate")

    def _require_ops(self, current_user: CurrentUser) -> None:
        if "OPS" not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only OPS role can sign and publish certificates",
            )

    def _serialize_certificate(self, certificate: Certificate) -> dict[str, Any]:
        return {
            "id": certificate.id,
            "certificate_number": certificate.certificate_number,
            "source_application_id": certificate.source_application_id,
            "source_application_number": certificate.source_application_number,
            "status": certificate.status,
            "is_dangerous_product": certificate.is_dangerous_product,
            "applicant_subject": certificate.applicant_subject,
            "applicant_username": certificate.applicant_username,
            "snapshot": self._decode_snapshot(certificate.snapshot_json),
            "generated_by_subject": certificate.generated_by_subject,
            "generated_at": certificate.generated_at.isoformat(),
            "signed_by_subject": certificate.signed_by_subject,
            "signed_at": certificate.signed_at.isoformat() if certificate.signed_at else None,
            "published_at": certificate.published_at.isoformat() if certificate.published_at else None,
            "created_at": certificate.created_at.isoformat(),
            "updated_at": certificate.updated_at.isoformat(),
        }

    def _serialize_registry_item(self, certificate: Certificate, include_subject: bool) -> dict[str, Any]:
        snapshot = self._decode_snapshot(certificate.snapshot_json)
        payload = snapshot.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}

        product_name = None
        products = payload.get("products")
        if isinstance(products, list) and products and isinstance(products[0], dict):
            product_name = products[0].get("name")

        item: dict[str, Any] = {
            "id": certificate.id,
            "certificate_number": certificate.certificate_number,
            "source_application_id": certificate.source_application_id,
            "source_application_number": certificate.source_application_number,
            "status": certificate.status,
            "applicant_username": certificate.applicant_username,
            "applicant_name": payload.get("applicant_name"),
            "ops_code": payload.get("ops_code"),
            "product_name": product_name,
            "signed_at": certificate.signed_at.isoformat() if certificate.signed_at else None,
            "published_at": certificate.published_at.isoformat() if certificate.published_at else None,
            "is_dangerous_product": certificate.is_dangerous_product,
            "generated_at": certificate.generated_at.isoformat(),
            "updated_at": certificate.updated_at.isoformat(),
        }
        if include_subject:
            item["applicant_subject"] = certificate.applicant_subject
        return item

    def _decode_snapshot(self, snapshot_json: str) -> dict[str, Any]:
        try:
            raw = json.loads(snapshot_json)
        except json.JSONDecodeError:
            return {}
        return raw if isinstance(raw, dict) else {}

    def _build_snapshot(self, application: CertApplication) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if application.payload_json:
            try:
                parsed = json.loads(application.payload_json)
                if isinstance(parsed, dict):
                    payload = parsed
            except json.JSONDecodeError:
                payload = {}

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "application": {
                "id": application.id,
                "application_number": application.application_number,
                "status": application.status,
                "applicant_subject": application.applicant_subject,
                "applicant_username": application.applicant_username,
            },
            "payload": payload,
        }

    def _new_certificate_number(self, application_id: int) -> str:
        now = datetime.now(UTC)
        return f"KZ/CERT/{now:%Y%m%d}/{application_id:06d}"

    def _build_certificate_pdf(self, certificate: Certificate) -> bytes:
        from io import BytesIO
        from pathlib import Path

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import simpleSplit
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas

        font_dir = Path("/usr/share/fonts/truetype/dejavu")
        font_map = {
            "DejaVuSerif": font_dir / "DejaVuSerif.ttf",
            "DejaVuSerif-Bold": font_dir / "DejaVuSerif-Bold.ttf",
            "DejaVuSans": font_dir / "DejaVuSans.ttf",
            "DejaVuSans-Bold": font_dir / "DejaVuSans-Bold.ttf",
        }
        registered_fonts = set(pdfmetrics.getRegisteredFontNames())
        for font_name, font_path in font_map.items():
            if font_name in registered_fonts:
                continue
            if not font_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Required PDF font is unavailable: {font_path.name}",
                )
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))

        snapshot = self._decode_snapshot(certificate.snapshot_json)
        payload = snapshot.get("payload", {}) if isinstance(snapshot.get("payload", {}), dict) else {}
        products = payload.get("products")
        product_name = (
            products[0].get("name")
            if isinstance(products, list) and products and isinstance(products[0], dict)
            else payload.get("product_name")
        )
        issued_at = certificate.published_at or certificate.generated_at
        valid_until = issued_at + timedelta(days=365 * 3)

        applicant_name = self._pdf_text(payload.get("applicant_name") or certificate.applicant_username or "-")
        applicant_bin = self._pdf_text(payload.get("applicant_bin") or "-")
        applicant_address = self._pdf_text(payload.get("applicant_address") or "Республика Казахстан")
        actual_address = self._pdf_text(payload.get("actual_address") or applicant_address)
        product_name_text = self._pdf_text(product_name or "Программное обеспечение")
        ops_code = self._pdf_text(payload.get("ops_code") or "KZ.O.02.E0968")
        certification_scheme = self._pdf_text(payload.get("cert_scheme_code") or "8")
        certificate_number = self._pdf_text(certificate.certificate_number)
        application_number = self._pdf_text(certificate.source_application_number)
        decision_date = issued_at.strftime("%d.%m.%Y")
        validity_date = valid_until.strftime("%d.%m.%Y")
        ops_full_name = self._pdf_text(
            payload.get("ops_name")
            or 'Товарищество с ограниченной ответственностью "SERTSOFT"'
        )
        manufacturer_name = self._pdf_text(payload.get("manufacturer_name") or 'Товарищество с ограниченной ответственностью "КОМРA"')
        manufacturer_address = self._pdf_text(
            payload.get("manufacturer_address")
            or "Республика Казахстан, г. Астана, пр. Б. Момышулы, 2/1, индекс: 010000"
        )
        applicant_display = self._pdf_text(payload.get("seller_name") or manufacturer_name)
        assessment_basis = self._pdf_text(
            payload.get("protocol_basis")
            or (
                "Протокол исследований (испытаний), выданный лабораториями (центрами), "
                "аккредитованными в национальных системах аккредитации (аттестации) "
                f"по заявке №{application_number} от {decision_date}."
            )
        )
        safety_standard = self._pdf_text(
            payload.get("safety_standard")
            or (
                "СТ РК ISO/IEC 15408-3-2017 «Информационные технологии. Методы и средства "
                "обеспечения безопасности. Критерии оценки безопасности информационных технологий»."
            )
        )
        additional_info = self._pdf_text(
            payload.get("additional_info") or f"Схема сертификации: {certification_scheme}"
        )
        protocol_code = self._pdf_text(payload.get("protocol_code") or "№ 7500968.05.01.47709")
        head_name = self._pdf_text(payload.get("head_name") or "ТИЛЕУБЕРДИЕВ АСХАТ ТИЛЕУБЕРДИЕВИЧ")
        auditor_name = self._pdf_text(payload.get("auditor_name") or "Тілеуберді Мадина Болатбекқызы")

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=0)
        page_width, page_height = A4
        pdf.setTitle(f"Сертификат соответствия {certificate_number}")
        pdf.setAuthor("e-KTRM")
        pdf.setSubject("Сертификат соответствия")
        pdf.setFillColor(colors.white)
        pdf.rect(0, 0, page_width, page_height, fill=1, stroke=0)
        pdf.setFillColor(colors.black)

        def draw_centered(text: str, y: float, font_name: str, font_size: int) -> None:
            pdf.setFillColor(colors.black)
            pdf.setFont(font_name, font_size)
            text_width = pdf.stringWidth(text, font_name, font_size)
            pdf.drawString((page_width - text_width) / 2, y, text)

        def draw_wrapped(
            x: float,
            y: float,
            text: str,
            font_name: str,
            font_size: int,
            max_width: float,
            leading: float,
        ) -> float:
            lines = simpleSplit(text, font_name, font_size, max_width)
            cursor = y
            pdf.setFillColor(colors.black)
            pdf.setFont(font_name, font_size)
            for line in lines:
                pdf.drawString(x, cursor, line)
                cursor -= leading
            return cursor

        def draw_section(
            y: float,
            title: str,
            body: str | None = None,
            *,
            title_font: str = "DejaVuSerif-Bold",
            title_size: int = 10,
            title_width: float = 455,
            title_leading: float = 12,
            body_font: str = "DejaVuSerif",
            body_size: int = 9,
            body_width: float = 455,
            body_leading: float = 10.5,
            gap_after_title: float = 6,
            gap_after_body: float = 14,
        ) -> float:
            cursor = draw_wrapped(70, y, title, title_font, title_size, title_width, title_leading)
            if body:
                cursor = draw_wrapped(70, cursor - gap_after_title, body, body_font, body_size, body_width, body_leading)
            return cursor - gap_after_body

        draw_centered("ГОСУДАРСТВЕННАЯ СИСТЕМА", 806, "DejaVuSerif-Bold", 12)
        draw_centered("ТЕХНИЧЕСКОГО РЕГУЛИРОВАНИЯ РЕСПУБЛИКИ КАЗАХСТАН", 792, "DejaVuSerif-Bold", 11)

        draw_centered("СЕРТИФИКАТ СООТВЕТСТВИЯ", 700, "DejaVuSerif-Bold", 22)
        draw_centered("зарегистрирован в реестре данных", 681, "DejaVuSerif", 10)
        draw_centered("государственной системы технического регулирования", 668, "DejaVuSerif", 10)
        draw_centered(f"от {decision_date} г.", 652, "DejaVuSerif", 10)
        draw_centered(protocol_code, 636, "DejaVuSerif", 11)
        draw_centered(f"Действителен до {validity_date} г.", 620, "DejaVuSerif", 11)

        content_width = 455
        y = 572
        y = draw_section(
            y,
            "Орган по подтверждению соответствия",
            f"БИН {applicant_bin}, {ops_full_name}, юридический адрес: {applicant_address}, "
            f"фактический адрес: {actual_address}. Код ОПС: {ops_code}",
            body_width=content_width,
        )

        y = draw_section(
            y,
            "Настоящий сертификат удостоверяет, что должным образом идентифицированная продукция",
            product_name_text,
            body_width=content_width,
        )

        y = draw_section(y, "КОД ТН ВЭД ЕАЭС", "8471900000", body_width=content_width)

        y = draw_section(
            y,
            "Изготовленная",
            f"{manufacturer_name}, юридический адрес: {manufacturer_address}",
            body_width=content_width,
        )

        y = draw_section(
            y,
            "Соответствует требованиям безопасности, установленным в",
            safety_standard,
            body_width=content_width,
        )

        y = draw_section(
            y,
            "Заявитель (изготовитель, продавец)",
            f"БИН {applicant_bin}, {applicant_display}, юридический адрес: {applicant_address}",
            body_width=content_width,
        )

        y = draw_section(
            y,
            "Сертификат выдан на основании",
            assessment_basis,
            body_width=content_width,
        )

        y = draw_section(
            y,
            "Дополнительная информация",
            additional_info,
            body_width=content_width,
        )

        signature_y = max(100, y - 2)
        pdf.setFillColor(colors.black)
        draw_wrapped(
            70,
            signature_y,
            "Руководитель органа по подтверждению соответствия или уполномоченное им лицо",
            "DejaVuSerif-Bold",
            8,
            130,
            8.5,
        )
        draw_wrapped(70, signature_y - 38, "Эксперт-аудитор", "DejaVuSerif-Bold", 8, 130, 8.5)

        draw_wrapped(320, signature_y - 2, head_name, "DejaVuSerif-Bold", 8.5, 150, 8.5)
        draw_wrapped(320, signature_y - 40, auditor_name, "DejaVuSerif", 8.5, 150, 8.5)

        draw_wrapped(
            70,
            16,
            "Данный документ согласно пункту 1 статьи 7 ЗРК от 7 января 2003 года N370-II "
            "«Об электронном документе и электронной цифровой подписи» равнозначен документу на бумажном носителе.",
            "DejaVuSerif",
            7.2,
            470,
            7.8,
        )

        pdf.showPage()
        pdf.save()
        return buffer.getvalue()

    def _pdf_text(self, value: Any) -> str:
        text = str(value or "-").strip()
        return " ".join(text.split()) or "-"
