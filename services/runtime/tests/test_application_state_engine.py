import sys
import unittest
from copy import deepcopy
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

LOOKUP_FIELDS = {
    "applicant_bin": "123456789012",
    "applicant_name": "ТОО Источник",
    "applicant_name_kz": "Источник ЖШС",
    "applicant_head_iin": "890627301030",
    "applicant_head_name": "КАБЫЛОВ МЕЙРАМБЕК МАЛИБЕКОВИЧ",
    "applicant_head_position": "Руководитель",
    "applicant_address": "город Алматы, Бостандыкский район, Проспект Абая, здание 10",
    "applicant_activity_address": "legal",
    "actual_address": "",
}


class FakeApplicantLookupService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def lookup_by_bin(self, bin_value: str) -> dict:
        self.calls.append(bin_value)
        return {
            "resolved_fields": deepcopy(LOOKUP_FIELDS),
            "integration_snapshot": {
                "source": "gbd_ul_kompra_v1",
                "resolved_fields": deepcopy(LOOKUP_FIELDS),
            },
        }


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

    def test_revision_and_resubmit_flow_is_supported(self) -> None:
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
        app = self._service.transition(
            application_id=app["id"],
            to_status="REVISION_REQUESTED",
            current_user=self._ops_user,
            comment="Нужно уточнить комплект документов",
        )
        app = self._service.transition(
            application_id=app["id"],
            to_status="SUBMITTED",
            current_user=self._user,
        )

        self.assertEqual(app["status"], "SUBMITTED")

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
                to_status="REVISION_REQUESTED",
                current_user=self._user,
                comment="forbidden",
            )
        self.assertEqual(context.exception.status_code, 403)

    def test_revision_requested_requires_comment(self) -> None:
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
                to_status="REVISION_REQUESTED",
                current_user=self._ops_user,
                comment="",
            )
        self.assertEqual(context.exception.status_code, 422)

    def test_apply_ops_decision_attaches_protocol_and_returns_approved(self) -> None:
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

        approved = self._service.apply_ops_decision(
            application_id=app["id"],
            decision_status="APPROVED",
            current_user=self._ops_user,
            protocol_metadata={
                "slot": "protocol_test_report",
                "object_key": f"applications/{app['id']}/protocol_test_report/test.pdf",
                "file_name": "protocol.pdf",
                "content_type": "application/pdf",
                "size_bytes": 128,
                "etag": "etag-1",
            },
            comment="Протокол подтверждает соответствие",
        )
        self.assertEqual(approved["status"], "APPROVED")
        self.assertEqual(
            approved["payload"]["file_slots"]["protocol_test_report"]["file_name"],
            "protocol.pdf",
        )
        self.assertIn("certificate", approved)

    def test_rejected_application_remains_rejected(self) -> None:
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
        rejected = self._service.apply_ops_decision(
            application_id=app["id"],
            decision_status="REJECTED",
            current_user=self._ops_user,
            protocol_metadata={
                "slot": "protocol_test_report",
                "object_key": f"applications/{app['id']}/protocol_test_report/reject.pdf",
                "file_name": "reject.pdf",
                "content_type": "application/pdf",
                "size_bytes": 96,
                "etag": "etag-2",
            },
            comment="Отказ по результатам проверки",
        )
        self.assertEqual(rejected["status"], "REJECTED")

        history = self._service.get_history(application_id=app["id"], current_user=self._ops_user)
        self.assertTrue(any(row["to_status"] == "REJECTED" for row in history["items"]))
        self.assertFalse(any(row["to_status"] == "ARCHIVED" for row in history["items"]))

    def test_submit_normalizes_sourced_fields_from_lookup_service(self) -> None:
        lookup_service = FakeApplicantLookupService()
        service = ApplicationStateService(self._repository, applicant_lookup_service=lookup_service)
        payload = {
            "applicant_name": "Ручное значение",
            "applicant_bin": "123456789012",
            "applicant_address": "Ручной адрес",
            "ops_code": "OPS-KZ-001",
            "cert_scheme_code": "SCHEME-1",
            "products": [{"name": "Провод"}],
        }

        draft = service.create_draft(payload=payload, current_user=self._user)
        submitted = service.transition(
            application_id=draft["id"],
            to_status="SUBMITTED",
            current_user=self._user,
        )

        self.assertEqual(lookup_service.calls, ["123456789012"])
        self.assertEqual(submitted["payload"]["applicant_name"], LOOKUP_FIELDS["applicant_name"])
        self.assertEqual(submitted["payload"]["applicant_head_name"], LOOKUP_FIELDS["applicant_head_name"])
        self.assertIn("integration_snapshot", submitted["payload"])


if __name__ == "__main__":
    unittest.main()
