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

        def _auth_override() -> CurrentUser:
            return CurrentUser(
                subject="applicant-1",
                username="applicant.demo",
                email="applicant@example.local",
                roles=frozenset({"Applicant"}),
                claims={},
            )

        self._app.dependency_overrides[get_session] = _session_override
        self._app.dependency_overrides[get_current_user] = _auth_override
        self._client = TestClient(self._app)

    def test_create_draft_and_submit_happy_path(self) -> None:
        payload = {
            "applicant_name": "ТОО Тест",
            "applicant_bin": "1234567890",
            "applicant_address": "г. Алматы",
            "ops_code": "OPS-KZ-001",
            "cert_scheme_code": "SCHEME-1",
            "products": [{"name": "Провод"}],
        }
        created = self._client.post("/applications/drafts", json=payload)
        self.assertEqual(created.status_code, 200)
        app_id = created.json()["id"]

        submitted = self._client.post(f"/applications/{app_id}/submit")
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json()["status"], "SUBMITTED")

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
            json={"to_status": "APPROVED", "comment": "force"},
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
        payload = {
            "applicant_name": "ТОО Тест",
            "applicant_bin": "1234567890",
            "applicant_address": "г. Алматы",
            "ops_code": "OPS-KZ-001",
            "cert_scheme_code": "SCHEME-1",
            "products": [{"name": "Провод"}],
        }
        created = self._client.post("/applications/drafts", json=payload)
        self.assertEqual(created.status_code, 200)
        app_id = created.json()["id"]

        submitted = self._client.post(f"/applications/{app_id}/submit")
        self.assertEqual(submitted.status_code, 200)

        response = self._client.delete(f"/applications/{app_id}/draft")
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
