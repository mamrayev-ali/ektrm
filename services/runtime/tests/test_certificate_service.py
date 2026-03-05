import sys
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import CurrentUser
from app.models import certificate as certificate_models  # noqa: F401
from app.models.base import Base
from app.repositories.application_repository import ApplicationRepository
from app.repositories.certificate_repository import CertificateRepository
from app.services.application_state_service import ApplicationStateService
from app.services.certificate_service import CertificateService


class CertificateServiceTests(unittest.TestCase):
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
        self._app_repository = ApplicationRepository(self._session)
        self._certificate_repository = CertificateRepository(self._session)
        self._certificate_service = CertificateService(self._certificate_repository)
        self._application_service = ApplicationStateService(
            repository=self._app_repository,
            certificate_service=self._certificate_service,
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

    def _payload(self) -> dict:
        return {
            "applicant_name": "ТОО Тест",
            "applicant_bin": "123456789012",
            "applicant_address": "г. Алматы",
            "ops_code": "OPS-KZ-001",
            "cert_scheme_code": "SCHEME-1",
            "products": [{"name": "Провод"}],
        }

    def _move_to_protocol_attached(self) -> dict:
        app = self._application_service.create_draft(payload=self._payload(), current_user=self._applicant)
        app = self._application_service.transition(application_id=app["id"], to_status="SUBMITTED", current_user=self._applicant)
        app = self._application_service.transition(application_id=app["id"], to_status="REGISTERED", current_user=self._ops)
        app = self._application_service.transition(application_id=app["id"], to_status="IN_REVIEW", current_user=self._ops)
        return self._application_service.transition(
            application_id=app["id"],
            to_status="PROTOCOL_ATTACHED",
            current_user=self._ops,
        )

    def test_approved_transition_generates_certificate(self) -> None:
        app = self._move_to_protocol_attached()
        approved = self._application_service.transition(
            application_id=app["id"],
            to_status="APPROVED",
            current_user=self._ops,
        )
        self.assertEqual(approved["status"], "APPROVED")
        self.assertIn("certificate", approved)
        self.assertEqual(approved["certificate"]["status"], "GENERATED")
        self.assertEqual(approved["certificate"]["source_application_id"], app["id"])

    def test_snapshot_is_immutable_after_application_payload_changes(self) -> None:
        app = self._move_to_protocol_attached()
        approved = self._application_service.transition(
            application_id=app["id"],
            to_status="APPROVED",
            current_user=self._ops,
        )
        certificate_before = approved["certificate"]
        self.assertEqual(certificate_before["snapshot"]["payload"]["applicant_name"], "ТОО Тест")

        application_row = self._app_repository.get_application(app["id"])
        self.assertIsNotNone(application_row)
        self._app_repository.update_payload(
            application=application_row,
            payload={**self._payload(), "applicant_name": "ТОО Изменено"},
        )
        self._app_repository.commit()

        certificate_after = self._certificate_service.get_certificate(
            certificate_id=certificate_before["id"],
            current_user=self._ops,
        )
        self.assertEqual(certificate_after["snapshot"]["payload"]["applicant_name"], "ТОО Тест")

    def test_generation_is_blocked_for_non_approved_application(self) -> None:
        draft = self._application_service.create_draft(payload=self._payload(), current_user=self._applicant)
        application_row = self._app_repository.get_application(draft["id"])
        self.assertIsNotNone(application_row)
        with self.assertRaises(HTTPException) as context:
            self._certificate_service.generate_for_approved_application(
                application=application_row,
                current_user=self._ops,
            )
        self.assertEqual(context.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
