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
from app.models import certificate as certificate_models  # noqa: F401
from app.models.base import Base
from app.routers.applications import router as applications_router
from app.routers.certificates import router as certificates_router


class CertificatesApiTests(unittest.TestCase):
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
        self._app = FastAPI()
        self._app.include_router(applications_router)
        self._app.include_router(certificates_router)

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

    def _other_applicant_user(self) -> CurrentUser:
        return CurrentUser(
            subject="applicant-2",
            username="another.applicant",
            email="another@example.local",
            roles=frozenset({"Applicant"}),
            claims={},
        )

    def _payload(self) -> dict:
        return {
            "applicant_name": "ТОО Тест",
            "applicant_bin": "123456789012",
            "applicant_address": "г. Алматы",
            "ops_code": "OPS-KZ-001",
            "cert_scheme_code": "SCHEME-1",
            "products": [{"name": "Провод"}],
        }

    def _create_approved_application(self) -> tuple[int, int]:
        created = self._client.post("/applications/drafts", json=self._payload())
        self.assertEqual(created.status_code, 200)
        app_id = created.json()["id"]

        submitted = self._client.post(f"/applications/{app_id}/submit")
        self.assertEqual(submitted.status_code, 200)

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
        certificate_id = approved.json()["certificate"]["id"]
        return app_id, certificate_id

    def test_get_certificate_by_application_happy_path(self) -> None:
        app_id, _ = self._create_approved_application()
        self._set_auth_user(self._ops_user())

        response = self._client.get(f"/certificates/by-application/{app_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "GENERATED")
        self.assertEqual(response.json()["source_application_id"], app_id)

    def test_get_certificate_by_id_happy_path(self) -> None:
        _, certificate_id = self._create_approved_application()
        self._set_auth_user(self._ops_user())

        response = self._client.get(f"/certificates/{certificate_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], certificate_id)
        self.assertEqual(response.json()["status"], "GENERATED")

    def test_applicant_cannot_read_foreign_certificate(self) -> None:
        _, certificate_id = self._create_approved_application()
        self._set_auth_user(self._other_applicant_user())

        response = self._client.get(f"/certificates/{certificate_id}")
        self.assertEqual(response.status_code, 403)

    def test_get_certificate_by_application_returns_404_until_approved(self) -> None:
        created = self._client.post("/applications/drafts", json=self._payload())
        self.assertEqual(created.status_code, 200)
        app_id = created.json()["id"]
        self._set_auth_user(self._ops_user())

        response = self._client.get(f"/certificates/by-application/{app_id}")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
