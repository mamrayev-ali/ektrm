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
            "applicant_bin": "1234567890",
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

    def test_ops_queue_returns_items_for_review_statuses(self) -> None:
        app_id = self._create_and_submit()

        self._set_auth_user(self._ops_user())
        for to_status in ("REGISTERED", "IN_REVIEW"):
            response = self._client.post(
                f"/applications/{app_id}/transitions",
                json={"to_status": to_status},
            )
            self.assertEqual(response.status_code, 200)

        queue = self._client.get("/applications/ops/queue", params={"statuses": "IN_REVIEW,PROTOCOL_ATTACHED"})
        self.assertEqual(queue.status_code, 200)
        items = queue.json()["items"]
        self.assertGreaterEqual(queue.json()["total"], 1)
        by_id = {item["id"]: item for item in items}
        self.assertIn(app_id, by_id)
        self.assertEqual(by_id[app_id]["status"], "IN_REVIEW")

    def test_attach_protocol_happy_path(self) -> None:
        app_id = self._create_and_submit()
        self._set_auth_user(self._ops_user())

        for to_status in ("REGISTERED", "IN_REVIEW"):
            response = self._client.post(
                f"/applications/{app_id}/transitions",
                json={"to_status": to_status},
            )
            self.assertEqual(response.status_code, 200)

        attach = self._client.post(
            f"/applications/{app_id}/protocol/attach",
            json={
                "slot": "protocol_test_report",
                "object_key": f"applications/{app_id}/protocol_test_report/protocol.pdf",
                "file_name": "protocol.pdf",
                "content_type": "application/pdf",
                "size_bytes": 2048,
                "etag": "etag-1",
            },
        )
        self.assertEqual(attach.status_code, 200)
        self.assertEqual(attach.json()["status"], "PROTOCOL_ATTACHED")

    def test_attach_protocol_requires_ops_role(self) -> None:
        app_id = self._create_and_submit()
        attach = self._client.post(
            f"/applications/{app_id}/protocol/attach",
            json={
                "slot": "protocol_test_report",
                "object_key": f"applications/{app_id}/protocol_test_report/protocol.pdf",
                "file_name": "protocol.pdf",
                "content_type": "application/pdf",
                "size_bytes": 2048,
            },
        )
        self.assertEqual(attach.status_code, 403)

    def test_approved_transition_returns_generated_certificate(self) -> None:
        app_id = self._create_and_submit()
        self._set_auth_user(self._ops_user())

        for to_status in ("REGISTERED", "IN_REVIEW", "PROTOCOL_ATTACHED"):
            response = self._client.post(
                f"/applications/{app_id}/transitions",
                json={"to_status": to_status},
            )
            self.assertEqual(response.status_code, 200)

        approved = self._client.post(
            f"/applications/{app_id}/transitions",
            json={"to_status": "APPROVED"},
        )
        self.assertEqual(approved.status_code, 200)
        body = approved.json()
        self.assertEqual(body["status"], "APPROVED")
        self.assertEqual(body["certificate"]["status"], "GENERATED")
        self.assertEqual(body["certificate"]["source_application_id"], app_id)

    def test_reject_transition_auto_archives(self) -> None:
        app_id = self._create_and_submit()
        self._set_auth_user(self._ops_user())

        for to_status in ("REGISTERED", "IN_REVIEW", "PROTOCOL_ATTACHED"):
            response = self._client.post(
                f"/applications/{app_id}/transitions",
                json={"to_status": to_status},
            )
            self.assertEqual(response.status_code, 200)

        rejected = self._client.post(
            f"/applications/{app_id}/transitions",
            json={"to_status": "REJECTED", "comment": "Несоответствие протоколу"},
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json()["status"], "ARCHIVED")

        history = self._client.get(f"/applications/{app_id}/history")
        self.assertEqual(history.status_code, 200)
        to_statuses = [row["to_status"] for row in history.json()["items"]]
        self.assertIn("REJECTED", to_statuses)
        self.assertIn("ARCHIVED", to_statuses)


if __name__ == "__main__":
    unittest.main()
