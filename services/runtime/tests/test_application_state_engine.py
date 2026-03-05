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

    def tearDown(self) -> None:
        self._session.rollback()
        self._session.close()

    def test_rejects_invalid_transition(self) -> None:
        draft = self._service.create_draft(payload={"applicant_name": "A"}, current_user=self._user)
        with self.assertRaises(HTTPException) as context:
            self._service.transition(
                application_id=draft["id"],
                to_status="APPROVED",
                current_user=self._user,
            )
        self.assertEqual(context.exception.status_code, 409)

    def test_full_order3_transition_chain_is_supported(self) -> None:
        payload = {
            "applicant_name": "ТОО Тест",
            "applicant_bin": "1234567890",
            "applicant_address": "г. Алматы",
            "ops_code": "OPS-KZ-001",
            "cert_scheme_code": "SCHEME-1",
            "products": [{"name": "Провод"}],
        }
        app = self._service.create_draft(payload=payload, current_user=self._user)

        for status in [
            "SUBMITTED",
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
                current_user=self._user,
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


if __name__ == "__main__":
    unittest.main()
