import sys
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import CurrentUser
from app.models import certificate as certificate_models  # noqa: F401
from app.models import post_issuance as post_issuance_models  # noqa: F401
from app.models import reference_data as reference_data_models  # noqa: F401
from app.models.base import Base
from app.models.reference_data import ReferenceDictionary, ReferenceDictionaryItem
from app.repositories.application_repository import ApplicationRepository
from app.repositories.certificate_repository import CertificateRepository
from app.repositories.post_issuance_repository import PostIssuanceRepository
from app.repositories.reference_data_repository import ReferenceDataRepository
from app.services.post_issuance_service import PostIssuanceService


class PostIssuanceServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls._engine)
        cls._session_factory = sessionmaker(bind=cls._engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def setUp(self) -> None:
        self._session: Session = self._session_factory()
        self._seed_reference_data()
        self._application_repository = ApplicationRepository(self._session)
        self._certificate_repository = CertificateRepository(self._session)
        self._post_issuance_repository = PostIssuanceRepository(self._session)
        self._reference_data_repository = ReferenceDataRepository(self._session)
        self._post_issuance_service = PostIssuanceService(
            repository=self._post_issuance_repository,
            certificate_repository=self._certificate_repository,
            reference_data_repository=self._reference_data_repository,
        )
        self._applicant = CurrentUser(
            subject="applicant-1",
            username="applicant.demo",
            email="applicant@example.local",
            roles=frozenset({"Applicant"}),
            claims={},
        )
        self._ops = CurrentUser(
            subject="ops-1",
            username="ops.demo",
            email="ops@example.local",
            roles=frozenset({"OPS"}),
            claims={},
        )

    def tearDown(self) -> None:
        self._session.rollback()
        self._session.close()

    def _seed_reference_data(self) -> None:
        dictionaries = {
            "suspension_reason": "Причины приостановления",
            "termination_reason": "Причины прекращения",
        }
        for code, name in dictionaries.items():
            exists = self._session.query(ReferenceDictionary).filter(ReferenceDictionary.code == code).one_or_none()
            if exists is None:
                dictionary = ReferenceDictionary(code=code, name=name, description=name)
                self._session.add(dictionary)
                self._session.flush()
                if code == "suspension_reason":
                    self._session.add(
                        ReferenceDictionaryItem(
                            dictionary_id=dictionary.id,
                            code="mutual_agreement",
                            name="По взаимному согласию",
                            sort_order=10,
                            is_active=True,
                        )
                    )
                if code == "termination_reason":
                    self._session.add_all(
                        [
                            ReferenceDictionaryItem(
                                dictionary_id=dictionary.id,
                                code="term_applicant_decision",
                                name="Прекращение производства данной продукции, услуги, процесса или по обоснованным иным причинам.",
                                sort_order=10,
                                is_active=True,
                            ),
                            ReferenceDictionaryItem(
                                dictionary_id=dictionary.id,
                                code="term_product_nonconformity",
                                name="Несоответствие продукции, услуги, процесса требованиям, установленным техническими регламентами, документами по стандартизации.",
                                sort_order=40,
                                is_active=True,
                            ),
                        ]
                    )
        self._session.commit()

    def _payload(self) -> dict:
        return {
            "applicant_name": "ТОО Тест",
            "applicant_bin": "123456789012",
            "applicant_address": "г. Алматы",
            "ops_code": "OPS-KZ-001",
            "accreditation_no": "KZ.ACC.001",
            "ops_manager": "Ответственный ОПС",
            "cert_scheme_code": "SCHEME-1",
            "products": [{"name": "Провод"}],
        }

    def _create_active_certificate(self) -> dict:
        suffix = uuid4().hex[:6].upper()
        application = self._application_repository.create_application(
            application_number=f"KZ/20260306/{suffix}",
            applicant_subject=self._applicant.subject,
            applicant_username=self._applicant.username,
            payload=self._payload(),
        )
        self._session.flush()
        certificate = self._certificate_repository.create_certificate(
            certificate_number=f"KZ/CERT/20260306/{suffix}",
            source_application_id=application.id,
            source_application_number=application.application_number,
            applicant_subject=self._applicant.subject,
            applicant_username=self._applicant.username,
            snapshot={"payload": self._payload()},
            generated_by_subject=self._ops.subject,
        )
        certificate.status = "ACTIVE"
        certificate.published_at = certificate.generated_at
        self._session.commit()
        return {
            "id": certificate.id,
            "status": certificate.status,
            "source_application_id": certificate.source_application_id,
        }

    def test_submit_requires_basis_file(self) -> None:
        certificate = self._create_active_certificate()
        created = self._post_issuance_service.create_draft(
            source_certificate_id=certificate["id"],
            action_type="SUSPEND",
            current_user=self._applicant,
        )
        payload = {
            **created["payload"],
            "suspension_reason_code": "mutual_agreement",
            "reason_detail": "Причина подтверждена заявителем",
            "note": "Тестовая приостановка",
            "remediation_deadline": "2026-03-10T09:30",
        }
        self._post_issuance_service.update_draft(created["id"], payload, self._applicant)

        with self.assertRaises(HTTPException) as context:
            self._post_issuance_service.submit(created["id"], self._applicant)
        self.assertEqual(context.exception.status_code, 422)

    def test_same_action_reuses_existing_editable_draft(self) -> None:
        certificate = self._create_active_certificate()
        first = self._post_issuance_service.create_draft(
            source_certificate_id=certificate["id"],
            action_type="SUSPEND",
            current_user=self._applicant,
        )
        second = self._post_issuance_service.create_draft(
            source_certificate_id=certificate["id"],
            action_type="SUSPEND",
            current_user=self._applicant,
        )
        self.assertEqual(second["id"], first["id"])
        self.assertEqual(second["status"], "DRAFT")

    def test_duplicate_active_process_is_blocked_for_different_action(self) -> None:
        certificate = self._create_active_certificate()
        self._post_issuance_service.create_draft(
            source_certificate_id=certificate["id"],
            action_type="SUSPEND",
            current_user=self._applicant,
        )
        with self.assertRaises(HTTPException) as context:
            self._post_issuance_service.create_draft(
                source_certificate_id=certificate["id"],
                action_type="TERMINATE",
                current_user=self._applicant,
            )
        self.assertEqual(context.exception.status_code, 409)

    def test_approve_suspend_updates_certificate_status(self) -> None:
        certificate = self._create_active_certificate()
        created = self._post_issuance_service.create_draft(
            source_certificate_id=certificate["id"],
            action_type="SUSPEND",
            current_user=self._applicant,
        )
        payload = {
            **created["payload"],
            "suspension_reason_code": "mutual_agreement",
            "reason_detail": "Причина подтверждена заявителем",
            "note": "Тестовая приостановка",
            "remediation_deadline": "2026-03-10T09:30",
            "file_slots": {
                "post_issuance_basis": {
                    "object_key": f"post-issuance/{created['id']}/post_issuance_basis/basis.pdf",
                    "file_name": "basis.pdf",
                }
            },
        }
        self._post_issuance_service.update_draft(created["id"], payload, self._applicant)
        submitted = self._post_issuance_service.submit(created["id"], self._applicant)
        self.assertEqual(submitted["status"], "REGISTERED")

        approved = self._post_issuance_service.transition(
            application_id=created["id"],
            to_status="APPROVED",
            current_user=self._ops,
            comment="Основания подтверждены",
        )
        self.assertEqual(approved["status"], "COMPLETED")
        self.assertEqual(approved["certificate"]["status"], "SUSPENDED")

    def test_applicant_cannot_submit_ops_only_termination_reason(self) -> None:
        certificate = self._create_active_certificate()
        created = self._post_issuance_service.create_draft(
            source_certificate_id=certificate["id"],
            action_type="TERMINATE",
            current_user=self._applicant,
        )
        payload = {
            **created["payload"],
            "request_source": "OPS",
            "termination_reason_code": "term_product_nonconformity",
            "reason_detail": "Попытка выбрать OPS-only основание",
            "note": "Тест запрета",
            "remediation_deadline": "2026-03-10T09:30",
            "file_slots": {
                "post_issuance_basis": {
                    "object_key": f"post-issuance/{created['id']}/post_issuance_basis/basis.pdf",
                    "file_name": "basis.pdf",
                }
            },
        }
        self._post_issuance_service.update_draft(created["id"], payload, self._applicant)

        with self.assertRaises(HTTPException) as context:
            self._post_issuance_service.submit(created["id"], self._applicant)
        self.assertEqual(context.exception.status_code, 422)
        self.assertIn("not available", str(context.exception.detail))


if __name__ == "__main__":
    unittest.main()
