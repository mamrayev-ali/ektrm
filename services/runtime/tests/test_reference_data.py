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
from app.models.reference_data import AccreditationAttestat, OpsRegistry, ReferenceDictionary, ReferenceDictionaryItem
from app.routers.reference_data import router as reference_data_router
from app.seed.reference_data_seed import (
    ACCREDITATION_ATTESTATS_SEED,
    MANDATORY_DICTIONARIES,
    MANDATORY_DICTIONARY_ITEMS,
    OPS_REGISTRY_SEED,
)


def _seed_for_test(session: Session) -> None:
    dictionaries = [
        ReferenceDictionary(
            code=entry["code"],
            name=entry["name"],
            description=entry["description"],
            is_active=True,
        )
        for entry in MANDATORY_DICTIONARIES
    ]
    session.add_all(dictionaries)
    session.flush()
    dictionary_ids = {item.code: item.id for item in dictionaries}

    items = [
        ReferenceDictionaryItem(
            dictionary_id=dictionary_ids[entry["dictionary_code"]],
            code=entry["code"],
            name=entry["name"],
            sort_order=entry["sort_order"],
            legal_basis=entry["legal_basis"],
            is_active=True,
        )
        for entry in MANDATORY_DICTIONARY_ITEMS
    ]
    session.add_all(items)

    ops_rows = [OpsRegistry(**entry, is_active=True) for entry in OPS_REGISTRY_SEED]
    session.add_all(ops_rows)

    attestat_rows = [AccreditationAttestat(**entry, is_active=True) for entry in ACCREDITATION_ATTESTATS_SEED]
    session.add_all(attestat_rows)
    session.commit()


class ReferenceDataApiTests(unittest.TestCase):
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
        with cls._session_factory() as session:
            _seed_for_test(session)

    def setUp(self) -> None:
        self._app = FastAPI()
        self._app.include_router(reference_data_router)

        def _session_override() -> Iterator[Session]:
            session = self._session_factory()
            try:
                yield session
            finally:
                session.close()

        def _auth_override() -> CurrentUser:
            return CurrentUser(
                subject="test-user",
                username="applicant.demo",
                email="applicant@example.local",
                roles=frozenset({"Applicant"}),
                claims={},
            )

        self._app.dependency_overrides[get_session] = _session_override
        self._app.dependency_overrides[get_current_user] = _auth_override
        self._client = TestClient(self._app)

    def test_list_dictionaries_returns_seeded_rows(self) -> None:
        response = self._client.get("/reference-data/dictionaries")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["total"], 16)
        self.assertTrue(any(item["code"] == "termination_reason" for item in payload["items"]))

    def test_list_dictionary_items_returns_404_for_unknown_dictionary(self) -> None:
        response = self._client.get("/reference-data/dictionaries/unknown/items")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"])

    def test_list_ops_registry_supports_search(self) -> None:
        response = self._client.get("/reference-data/ops-registry", params={"search": "НацЭксперт"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["ops_code"], "OPS-KZ-002")


if __name__ == "__main__":
    unittest.main()
