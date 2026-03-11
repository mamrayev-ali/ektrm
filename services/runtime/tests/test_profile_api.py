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
from app.models import user_profile as user_profile_models  # noqa: F401
from app.models.base import Base
from app.routers.profile import router as profile_router


class ProfileApiTests(unittest.TestCase):
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
        self._app.include_router(profile_router)

        def _session_override() -> Iterator[Session]:
            session = self._session_factory()
            try:
                yield session
            finally:
                session.close()

        self._app.dependency_overrides[get_session] = _session_override
        self._set_auth_user(self._applicant_user())
        self._client = TestClient(self._app)

    def _set_auth_user(self, user: CurrentUser) -> None:
        def _auth_override() -> CurrentUser:
            return user

        self._app.dependency_overrides[get_current_user] = _auth_override

    def _applicant_user(self) -> CurrentUser:
        return CurrentUser(
            subject="applicant-1",
            username="applicant.demo",
            email="applicant@example.local",
            roles=frozenset({"Applicant"}),
            claims={"name": "Иван Тестов"},
        )

    def _ops_user(self) -> CurrentUser:
        return CurrentUser(
            subject="ops-1",
            username="ops.demo",
            email="ops@example.local",
            roles=frozenset({"OPS"}),
            claims={"name": "ОПС Оператор"},
        )

    def test_get_profile_bootstraps_from_current_user(self) -> None:
        response = self._client.get("/profile/me")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["subject"], "applicant-1")
        self.assertEqual(body["username"], "applicant.demo")
        self.assertEqual(body["display_name"], "Иван Тестов")
        self.assertEqual(body["primary_role"], "Applicant")
        self.assertEqual(body["role_label"], "Заявитель")

    def test_update_profile_persists_fields(self) -> None:
        updated = self._client.put(
            "/profile/me",
            json={
                "full_name": "ТОО Тестовый заявитель",
                "email": "cabinet@example.local",
                "phone": "+7(701) 111 22 33",
                "address": "г. Алматы, ул. Абая, 1",
                "actual_address": "г. Астана, ул. Сарыарка, 5",
            },
        )
        self.assertEqual(updated.status_code, 200)
        body = updated.json()
        self.assertEqual(body["full_name"], "ТОО Тестовый заявитель")
        self.assertEqual(body["email"], "cabinet@example.local")
        self.assertEqual(body["phone"], "+7(701) 111 22 33")
        self.assertEqual(body["address"], "г. Алматы, ул. Абая, 1")
        self.assertEqual(body["actual_address"], "г. Астана, ул. Сарыарка, 5")

        fetched = self._client.get("/profile/me")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["full_name"], "ТОО Тестовый заявитель")

    def test_update_avatar_stores_data_url(self) -> None:
        response = self._client.put(
            "/profile/me/avatar",
            json={
                "content_type": "image/png",
                "content_base64": "iVBORw0KGgo=",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["avatar_data_url"].startswith("data:image/png;base64,"))

    def test_clear_avatar_removes_stored_avatar(self) -> None:
        uploaded = self._client.put(
            "/profile/me/avatar",
            json={
                "content_type": "image/png",
                "content_base64": "iVBORw0KGgo=",
            },
        )
        self.assertEqual(uploaded.status_code, 200)

        cleared = self._client.delete("/profile/me/avatar")
        self.assertEqual(cleared.status_code, 200)
        self.assertIsNone(cleared.json()["avatar_data_url"])

    def test_get_profile_returns_ops_role_label(self) -> None:
        self._set_auth_user(self._ops_user())
        response = self._client.get("/profile/me")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["primary_role"], "OPS")
        self.assertEqual(body["role_label"], "ОПС")


if __name__ == "__main__":
    unittest.main()
