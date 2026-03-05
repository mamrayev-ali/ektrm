import sys
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import CurrentUser
from app.models.base import Base
from app.repositories.application_repository import ApplicationRepository
from app.services.application_state_service import ApplicationStateService


class ApplicationStateEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls._engine)
        cls._session_factory = sessionmaker(bind=cls._engine, autoflush=False, autocommit=False)

    def setUp(self) -> None:
        self._session: Session = self._session_factory()
        self._repository = ApplicationRepository(self._session)
        self._service = ApplicationStateService(self._repository)
        self._user = CurrentUser(
            subject="user-1",
            username="applicant.demo",
            email="applicant@example.local",
            roles=frozenset({"Applicant"}),
            claims={},
        )
        self._ops_user = CurrentUser(
            subject="ops-1",
            username="ops.demo",
            email="ops@example.local",
            roles=frozenset({"OPS"}),
            claims={},
        )

    def tearDown(self) -> None:
        self._session.rollback()
        self._session.close()

    def test_rejects_invalid_transition(self) -> None:
        draft = self._service.create_draft(payload={"applicant_name": "A"}, current_user=self._user)
        with self.assertRaises(HTTPException) as context:
            self._service.transition(
                application_id=draft["id"],
                to_status="DRAFT",
                current_user=self._user,
            )
        self.assertEqual(context.exception.status_code, 409)

    def test_full_order3_transition_chain_is_supported(self) -> None:
        payload = {
            "applicant_name": "ТОО Тест",
            "applicant_bin": "123456789012",
            "applicant_address": "г. Алматы",
            "ops_code": "OPS-KZ-001",
            "cert_scheme_code": "SCHEME-1",
            "products": [{"name": "Провод"}],
        }
        app = self._service.create_draft(payload=payload, current_user=self._user)
        app = self._service.transition(
            application_id=app["id"],
            to_status="SUBMITTED",
            current_user=self._user,
        )

        for status in [
            "REGISTERED",
            "IN_REVIEW",
            "REVISION_REQUESTED",
            "IN_REVIEW",
            "PROTOCOL_ATTACHED",
            "APPROVED",
            "COMPLETED",
        ]:
            app = self._service.transition(
                application_id=app["id"],
                to_status=status,
                current_user=self._ops_user,
            )

        self.assertEqual(app["status"], "COMPLETED")

    def test_submit_requires_required_fields(self) -> None:
        draft = self._service.create_draft(payload={}, current_user=self._user)
        with self.assertRaises(HTTPException) as context:
            self._service.transition(
                application_id=draft["id"],
                to_status="SUBMITTED",
                current_user=self._user,
            )
        self.assertEqual(context.exception.status_code, 422)

    def test_delete_draft_moves_application_to_archived(self) -> None:
        draft = self._service.create_draft(payload={"applicant_name": "A"}, current_user=self._user)
        archived = self._service.delete_draft(application_id=draft["id"], current_user=self._user)
        self.assertEqual(archived["status"], "ARCHIVED")

    def test_applicant_cannot_do_ops_review_transitions(self) -> None:
        payload = {
            "applicant_name": "ТОО Тест",
            "applicant_bin": "123456789012",
            "applicant_address": "г. Алматы",
            "ops_code": "OPS-KZ-001",
            "cert_scheme_code": "SCHEME-1",
            "products": [{"name": "Провод"}],
        }
        app = self._service.create_draft(payload=payload, current_user=self._user)
        app = self._service.transition(application_id=app["id"], to_status="SUBMITTED", current_user=self._user)
        with self.assertRaises(HTTPException) as context:
            self._service.transition(
                application_id=app["id"],
                to_status="REGISTERED",
                current_user=self._user,
            )
        self.assertEqual(context.exception.status_code, 403)

    def test_attach_protocol_updates_payload_and_status(self) -> None:
        payload = {
            "applicant_name": "ТОО Тест",
            "applicant_bin": "123456789012",
            "applicant_address": "г. Алматы",
            "ops_code": "OPS-KZ-001",
            "cert_scheme_code": "SCHEME-1",
            "products": [{"name": "Провод"}],
        }
        app = self._service.create_draft(payload=payload, current_user=self._user)
        app = self._service.transition(application_id=app["id"], to_status="SUBMITTED", current_user=self._user)
        app = self._service.transition(application_id=app["id"], to_status="REGISTERED", current_user=self._ops_user)
        app = self._service.transition(application_id=app["id"], to_status="IN_REVIEW", current_user=self._ops_user)

        attached = self._service.attach_protocol(
            application_id=app["id"],
            current_user=self._ops_user,
            metadata={
                "slot": "protocol_test_report",
                "object_key": f"applications/{app['id']}/protocol_test_report/test.pdf",
                "file_name": "protocol.pdf",
                "content_type": "application/pdf",
                "size_bytes": 128,
                "etag": "etag-1",
            },
        )
        self.assertEqual(attached["status"], "PROTOCOL_ATTACHED")
        self.assertEqual(
            attached["payload"]["file_slots"]["protocol_test_report"]["file_name"],
            "protocol.pdf",
        )

    def test_rejected_application_is_auto_archived_with_notification_history(self) -> None:
        payload = {
            "applicant_name": "ТОО Тест",
            "applicant_bin": "123456789012",
            "applicant_address": "г. Алматы",
            "ops_code": "OPS-KZ-001",
            "cert_scheme_code": "SCHEME-1",
            "products": [{"name": "Провод"}],
        }
        app = self._service.create_draft(payload=payload, current_user=self._user)
        app = self._service.transition(application_id=app["id"], to_status="SUBMITTED", current_user=self._user)
        app = self._service.transition(application_id=app["id"], to_status="REGISTERED", current_user=self._ops_user)
        app = self._service.transition(application_id=app["id"], to_status="IN_REVIEW", current_user=self._ops_user)
        app = self._service.transition(application_id=app["id"], to_status="PROTOCOL_ATTACHED", current_user=self._ops_user)
        rejected = self._service.transition(
            application_id=app["id"],
            to_status="REJECTED",
            current_user=self._ops_user,
            comment="Отказ по результатам проверки",
        )
        self.assertEqual(rejected["status"], "ARCHIVED")

        history = self._service.get_history(application_id=app["id"], current_user=self._ops_user)
        self.assertTrue(any(row["to_status"] == "REJECTED" for row in history["items"]))
        self.assertTrue(any(row["to_status"] == "ARCHIVED" for row in history["items"]))


if __name__ == "__main__":
    unittest.main()
