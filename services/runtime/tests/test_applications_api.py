import sys
import unittest
from pathlib import Path
from typing import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.models.base import Base
from app.routers.applications import router as applications_router


class ApplicationsApiTests(unittest.TestCase):
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
        self._app = FastAPI()
        self._app.include_router(applications_router)

        def _session_override() -> Iterator[Session]:
            session = self._session_factory()
            try:
                yield session
            finally:
                session.close()

        self._app.dependency_overrides[get_session] = _session_override
        self._set_auth_user(
            CurrentUser(
                subject="applicant-1",
                username="applicant.demo",
                email="applicant@example.local",
                roles=frozenset({"Applicant"}),
                claims={},
            )
        )
        self._client = TestClient(self._app)

    def _set_auth_user(self, user: CurrentUser) -> None:
        def _auth_override() -> CurrentUser:
            return user

        self._app.dependency_overrides[get_current_user] = _auth_override

    def _ops_user(self) -> CurrentUser:
        return CurrentUser(
            subject="ops-1",
            username="ops.demo",
            email="ops@example.local",
            roles=frozenset({"OPS"}),
            claims={},
        )

    def _applicant_payload(self) -> dict:
        return {
            "applicant_name": "ТОО Тест",
            "applicant_bin": "123456789012",
            "applicant_address": "г. Алматы",
            "ops_code": "OPS-KZ-001",
            "cert_scheme_code": "SCHEME-1",
            "products": [{"name": "Провод"}],
        }

    def _create_and_submit(self) -> int:
        created = self._client.post("/applications/drafts", json=self._applicant_payload())
        self.assertEqual(created.status_code, 200)
        app_id = created.json()["id"]
        submitted = self._client.post(f"/applications/{app_id}/submit")
        self.assertEqual(submitted.status_code, 200)
        return app_id

    def test_create_draft_and_submit_happy_path(self) -> None:
        app_id = self._create_and_submit()
        history = self._client.get(f"/applications/{app_id}/history")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["total"], 2)

    def test_submit_returns_422_for_incomplete_payload(self) -> None:
        created = self._client.post("/applications/drafts", json={})
        self.assertEqual(created.status_code, 200)
        app_id = created.json()["id"]

        response = self._client.post(f"/applications/{app_id}/submit")
        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"]
        self.assertIn("missing_fields", detail)

    def test_submit_returns_422_for_invalid_bin(self) -> None:
        payload = self._applicant_payload()
        payload["applicant_bin"] = "1234567890"
        created = self._client.post("/applications/drafts", json=payload)
        self.assertEqual(created.status_code, 200)
        app_id = created.json()["id"]

        response = self._client.post(f"/applications/{app_id}/submit")
        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"]
        self.assertEqual(detail["field"], "applicant_bin")

    def test_invalid_transition_returns_409(self) -> None:
        created = self._client.post("/applications/drafts", json={"applicant_name": "A"})
        self.assertEqual(created.status_code, 200)
        app_id = created.json()["id"]

        response = self._client.post(
            f"/applications/{app_id}/transitions",
            json={"to_status": "DRAFT", "comment": "force"},
        )
        self.assertEqual(response.status_code, 409)

    def test_delete_draft_archives_application(self) -> None:
        created = self._client.post("/applications/drafts", json={"applicant_name": "A"})
        self.assertEqual(created.status_code, 200)
        app_id = created.json()["id"]

        deleted = self._client.delete(f"/applications/{app_id}/draft")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["status"], "ARCHIVED")

    def test_delete_draft_returns_409_after_submit(self) -> None:
        app_id = self._create_and_submit()
        response = self._client.delete(f"/applications/{app_id}/draft")
        self.assertEqual(response.status_code, 409)

    def test_applicant_cannot_access_ops_queue(self) -> None:
        response = self._client.get("/applications/ops/queue")
        self.assertEqual(response.status_code, 403)

    def test_mine_returns_only_current_user_applications(self) -> None:
        first = self._client.post("/applications/drafts", json={"applicant_name": "A"})
        second = self._client.post("/applications/drafts", json={"applicant_name": "B"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        self._set_auth_user(
            CurrentUser(
                subject="another-applicant",
                username="another.demo",
                email="another@example.local",
                roles=frozenset({"Applicant"}),
                claims={},
            )
        )
        foreign = self._client.post("/applications/drafts", json={"applicant_name": "C"})
        self.assertEqual(foreign.status_code, 200)

        self._set_auth_user(
            CurrentUser(
                subject="applicant-1",
                username="applicant.demo",
                email="applicant@example.local",
                roles=frozenset({"Applicant"}),
                claims={},
            )
        )
        mine = self._client.get("/applications/mine")
        self.assertEqual(mine.status_code, 200)
        ids = [item["id"] for item in mine.json()["items"]]
        self.assertIn(first.json()["id"], ids)
        self.assertIn(second.json()["id"], ids)
        self.assertNotIn(foreign.json()["id"], ids)

    def test_get_application_returns_own_application_for_applicant(self) -> None:
        created = self._client.post("/applications/drafts", json=self._applicant_payload())
        self.assertEqual(created.status_code, 200)
        app_id = created.json()["id"]

        response = self._client.get(f"/applications/{app_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], app_id)
        self.assertEqual(response.json()["applicant_subject"], "applicant-1")

    def test_get_application_returns_403_for_foreign_applicant(self) -> None:
        created = self._client.post("/applications/drafts", json=self._applicant_payload())
        self.assertEqual(created.status_code, 200)
        app_id = created.json()["id"]

        self._set_auth_user(
            CurrentUser(
                subject="another-applicant",
                username="another.demo",
                email="another@example.local",
                roles=frozenset({"Applicant"}),
                claims={},
            )
        )
        response = self._client.get(f"/applications/{app_id}")
        self.assertEqual(response.status_code, 403)

    def test_get_history_returns_403_for_foreign_applicant(self) -> None:
        app_id = self._create_and_submit()

        self._set_auth_user(self._ops_user())
        registered = self._client.post(
            f"/applications/{app_id}/transitions",
            json={"to_status": "REVISION_REQUESTED", "comment": "Нужна доработка"},
        )
        self.assertEqual(registered.status_code, 200)

        self._set_auth_user(
            CurrentUser(
                subject="another-applicant",
                username="another.demo",
                email="another@example.local",
                roles=frozenset({"Applicant"}),
                claims={},
            )
        )
        response = self._client.get(f"/applications/{app_id}/history")
        self.assertEqual(response.status_code, 403)

    def test_ops_queue_returns_items_for_review_statuses(self) -> None:
        app_id = self._create_and_submit()

        self._set_auth_user(self._ops_user())
        queue = self._client.get("/applications/ops/queue", params={"statuses": "SUBMITTED"})
        self.assertEqual(queue.status_code, 200)
        items = queue.json()["items"]
        self.assertGreaterEqual(queue.json()["total"], 1)
        by_id = {item["id"]: item for item in items}
        self.assertIn(app_id, by_id)
        self.assertEqual(by_id[app_id]["status"], "SUBMITTED")

    def test_apply_ops_decision_happy_path(self) -> None:
        app_id = self._create_and_submit()
        self._set_auth_user(self._ops_user())

        decision = self._client.post(
            f"/applications/{app_id}/ops-decision",
            json={
                "decision_status": "APPROVED",
                "comment": "Протокол подтвержден",
                "protocol": {
                    "slot": "protocol_test_report",
                    "object_key": f"applications/{app_id}/protocol_test_report/protocol.pdf",
                    "file_name": "protocol.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 2048,
                    "etag": "etag-1",
                },
            },
        )
        self.assertEqual(decision.status_code, 200)
        self.assertEqual(decision.json()["status"], "APPROVED")
        self.assertIn("certificate", decision.json())

    def test_apply_ops_decision_requires_ops_role(self) -> None:
        app_id = self._create_and_submit()
        decision = self._client.post(
            f"/applications/{app_id}/ops-decision",
            json={
                "decision_status": "APPROVED",
                "protocol": {
                    "slot": "protocol_test_report",
                    "object_key": f"applications/{app_id}/protocol_test_report/protocol.pdf",
                    "file_name": "protocol.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 2048,
                },
            },
        )
        self.assertEqual(decision.status_code, 403)

    def test_approved_transition_returns_generated_certificate(self) -> None:
        app_id = self._create_and_submit()
        self._set_auth_user(self._ops_user())

        approved = self._client.post(
            f"/applications/{app_id}/ops-decision",
            json={
                "decision_status": "APPROVED",
                "protocol": {
                    "slot": "protocol_test_report",
                    "object_key": f"applications/{app_id}/protocol_test_report/protocol.pdf",
                    "file_name": "protocol.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 2048,
                },
            },
        )
        self.assertEqual(approved.status_code, 200)
        body = approved.json()
        self.assertEqual(body["status"], "APPROVED")
        self.assertEqual(body["certificate"]["status"], "GENERATED")
        self.assertEqual(body["certificate"]["source_application_id"], app_id)

    def test_reject_transition_keeps_rejected_status(self) -> None:
        app_id = self._create_and_submit()
        self._set_auth_user(self._ops_user())

        rejected = self._client.post(
            f"/applications/{app_id}/ops-decision",
            json={
                "decision_status": "REJECTED",
                "comment": "Несоответствие протоколу",
                "protocol": {
                    "slot": "protocol_test_report",
                    "object_key": f"applications/{app_id}/protocol_test_report/protocol.pdf",
                    "file_name": "protocol.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 2048,
                },
            },
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json()["status"], "REJECTED")

        history = self._client.get(f"/applications/{app_id}/history")
        self.assertEqual(history.status_code, 200)
        to_statuses = [row["to_status"] for row in history.json()["items"]]
        self.assertIn("REJECTED", to_statuses)
        self.assertNotIn("ARCHIVED", to_statuses)

    def test_revision_requested_can_be_resubmitted_by_applicant(self) -> None:
        app_id = self._create_and_submit()
        self._set_auth_user(self._ops_user())
        revision = self._client.post(
            f"/applications/{app_id}/transitions",
            json={"to_status": "REVISION_REQUESTED", "comment": "Добавьте уточнение"},
        )
        self.assertEqual(revision.status_code, 200)

        self._set_auth_user(
            CurrentUser(
                subject="applicant-1",
                username="applicant.demo",
                email="applicant@example.local",
                roles=frozenset({"Applicant"}),
                claims={},
            )
        )
        resubmitted = self._client.post(f"/applications/{app_id}/submit")
        self.assertEqual(resubmitted.status_code, 200)
        self.assertEqual(resubmitted.json()["status"], "SUBMITTED")


if __name__ == "__main__":
    unittest.main()
