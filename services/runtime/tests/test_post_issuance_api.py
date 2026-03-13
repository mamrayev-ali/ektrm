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
from app.models import post_issuance as post_issuance_models  # noqa: F401
from app.models import reference_data as reference_data_models  # noqa: F401
from app.models.base import Base
from app.models.reference_data import ReferenceDictionary, ReferenceDictionaryItem
from app.routers.applications import router as applications_router
from app.routers.certificates import router as certificates_router
from app.routers.certificates import get_signature_validator
from app.routers.post_issuance import router as post_issuance_router
from app.routers.registry import router as registry_router
from app.services.certificate_signature_validation import SignatureValidationResult


class FakeSignatureValidator:
    def validate(self, *, payload_base64: str, signature_cms_base64: str, signature_mode: str) -> SignatureValidationResult:
        return SignatureValidationResult(
            is_valid=True,
            validator_name="fake-validator",
            revocation_check_mode="TEST",
            signer_subject="CN=OPS Signer",
            signer_serial_number="ABC123",
        )


class PostIssuanceApiTests(unittest.TestCase):
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
        self._app.include_router(post_issuance_router)
        self._app.include_router(registry_router)

        def _session_override() -> Iterator[Session]:
            session = self._session_factory()
            try:
                yield session
            finally:
                session.close()

        self._app.dependency_overrides[get_session] = _session_override
        self._app.dependency_overrides[get_signature_validator] = lambda: FakeSignatureValidator()
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
        self._seed_reference_data()

    def _seed_reference_data(self) -> None:
        session = self._session_factory()
        try:
            definitions = {
                "suspension_reason": ("mutual_agreement", "По взаимному согласию"),
            }
            for dictionary_code, (item_code, item_name) in definitions.items():
                dictionary = session.query(ReferenceDictionary).filter(ReferenceDictionary.code == dictionary_code).one_or_none()
                if dictionary is None:
                    dictionary = ReferenceDictionary(code=dictionary_code, name=dictionary_code, description=dictionary_code)
                    session.add(dictionary)
                    session.flush()
                    session.add(
                        ReferenceDictionaryItem(
                            dictionary_id=dictionary.id,
                            code=item_code,
                            name=item_name,
                            sort_order=10,
                            is_active=True,
                        )
                    )
            termination_dictionary = (
                session.query(ReferenceDictionary).filter(ReferenceDictionary.code == "termination_reason").one_or_none()
            )
            if termination_dictionary is None:
                termination_dictionary = ReferenceDictionary(
                    code="termination_reason",
                    name="termination_reason",
                    description="termination_reason",
                )
                session.add(termination_dictionary)
                session.flush()
            existing_codes = {
                row.code
                for row in session.query(ReferenceDictionaryItem)
                .filter(ReferenceDictionaryItem.dictionary_id == termination_dictionary.id)
                .all()
            }
            for item_code, item_name, sort_order in (
                (
                    "term_applicant_decision",
                    "Прекращение производства данной продукции, услуги, процесса или по обоснованным иным причинам.",
                    10,
                ),
                (
                    "term_product_nonconformity",
                    "Несоответствие продукции, услуги, процесса требованиям, установленным техническими регламентами, документами по стандартизации.",
                    40,
                ),
            ):
                if item_code not in existing_codes:
                    session.add(
                        ReferenceDictionaryItem(
                            dictionary_id=termination_dictionary.id,
                            code=item_code,
                            name=item_name,
                            sort_order=sort_order,
                            is_active=True,
                        )
                    )
            session.commit()
        finally:
            session.close()

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
            "accreditation_no": "KZ.ACC.001",
            "ops_manager": "Ответственный ОПС",
            "cert_scheme_code": "SCHEME-1",
            "products": [{"name": "Провод"}],
        }

    def _create_active_certificate(self) -> int:
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

        approved = self._client.post(f"/applications/{app_id}/transitions", json={"to_status": "APPROVED"})
        self.assertEqual(approved.status_code, 200)
        certificate_id = approved.json()["certificate"]["id"]
        prepared = self._client.post(
            f"/certificates/{certificate_id}/sign/prepare",
            json={"signer_kind": "signAny"},
        )
        self.assertEqual(prepared.status_code, 200)
        operation = prepared.json()["signature_operation"]
        signed = self._client.post(
            f"/certificates/{certificate_id}/sign",
            json={
                "operation_id": operation["operation_id"],
                "signature_mode": "detached",
                "payload_base64": operation["payload_base64"],
                "payload_sha256_hex": operation["payload_sha256_hex"],
                "signature_cms_base64": "ZmFrZS1zaWduYXR1cmU=",
                "comment": "Активировать сертификат",
            },
        )
        self.assertEqual(signed.status_code, 200)
        self.assertEqual(signed.json()["certificate"]["status"], "ACTIVE")
        self._set_auth_user(
            CurrentUser(
                subject="applicant-1",
                username="applicant.demo",
                email="applicant@example.local",
                roles=frozenset({"Applicant"}),
                claims={},
            )
        )
        return certificate_id

    def _prepare_payload(self, draft_payload: dict, action_type: str) -> dict:
        payload = {
            **draft_payload,
            "reason_detail": "Подробное описание основания",
            "note": "Примечание к post-issuance",
            "remediation_deadline": "2026-03-10T09:30",
        }
        if action_type == "SUSPEND":
            payload["suspension_reason_code"] = "mutual_agreement"
        else:
            payload["termination_reason_code"] = "term_applicant_decision"
        return payload

    def test_suspend_happy_path_updates_certificate_and_registry(self) -> None:
        certificate_id = self._create_active_certificate()

        created = self._client.post(
            "/post-issuance/drafts",
            json={"source_certificate_id": certificate_id, "action_type": "SUSPEND"},
        )
        self.assertEqual(created.status_code, 200)
        application_id = created.json()["id"]

        updated = self._client.put(
            f"/post-issuance/{application_id}/draft",
            json=self._prepare_payload(created.json()["payload"], "SUSPEND"),
        )
        self.assertEqual(updated.status_code, 200)

        attached = self._client.post(
            f"/post-issuance/{application_id}/basis/attach",
            json={
                "slot": "post_issuance_basis",
                "object_key": f"post-issuance/{application_id}/post_issuance_basis/basis.pdf",
                "file_name": "basis.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
                "etag": "etag-1",
            },
        )
        self.assertEqual(attached.status_code, 200)

        submitted = self._client.post(f"/post-issuance/{application_id}/submit")
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json()["status"], "REGISTERED")

        self._set_auth_user(self._ops_user())
        review = self._client.post(
            f"/post-issuance/{application_id}/transitions",
            json={"to_status": "IN_REVIEW"},
        )
        self.assertEqual(review.status_code, 200)

        approved = self._client.post(
            f"/post-issuance/{application_id}/transitions",
            json={"to_status": "APPROVED", "comment": "Основания подтверждены"},
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["status"], "COMPLETED")
        self.assertEqual(approved.json()["certificate"]["status"], "SUSPENDED")

        internal = self._client.get("/registry/internal")
        self.assertEqual(internal.status_code, 200)
        item = next(item for item in internal.json()["items"] if item["id"] == certificate_id)
        self.assertEqual(item["status"], "SUSPENDED")

        public = self._client.get("/registry/public")
        self.assertEqual(public.status_code, 200)
        public_item = next(item for item in public.json()["items"] if item["id"] == certificate_id)
        self.assertEqual(public_item["status"], "SUSPENDED")

    def test_terminate_sets_danger_flag(self) -> None:
        certificate_id = self._create_active_certificate()

        created = self._client.post(
            "/post-issuance/drafts",
            json={"source_certificate_id": certificate_id, "action_type": "TERMINATE"},
        )
        self.assertEqual(created.status_code, 200)
        application_id = created.json()["id"]

        self._client.put(
            f"/post-issuance/{application_id}/draft",
            json=self._prepare_payload(created.json()["payload"], "TERMINATE"),
        )
        self._client.post(
            f"/post-issuance/{application_id}/basis/attach",
            json={
                "slot": "post_issuance_basis",
                "object_key": f"post-issuance/{application_id}/post_issuance_basis/basis.pdf",
                "file_name": "basis.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
        )
        submitted = self._client.post(f"/post-issuance/{application_id}/submit")
        self.assertEqual(submitted.status_code, 200)

        self._set_auth_user(self._ops_user())
        approved = self._client.post(
            f"/post-issuance/{application_id}/transitions",
            json={"to_status": "APPROVED"},
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["certificate"]["status"], "TERMINATED")
        self.assertTrue(approved.json()["certificate"]["is_dangerous_product"])

    def test_reject_archives_request_and_keeps_certificate_active(self) -> None:
        certificate_id = self._create_active_certificate()
        created = self._client.post(
            "/post-issuance/drafts",
            json={"source_certificate_id": certificate_id, "action_type": "SUSPEND"},
        )
        application_id = created.json()["id"]
        self._client.put(
            f"/post-issuance/{application_id}/draft",
            json=self._prepare_payload(created.json()["payload"], "SUSPEND"),
        )
        self._client.post(
            f"/post-issuance/{application_id}/basis/attach",
            json={
                "slot": "post_issuance_basis",
                "object_key": f"post-issuance/{application_id}/post_issuance_basis/basis.pdf",
                "file_name": "basis.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
        )
        self._client.post(f"/post-issuance/{application_id}/submit")

        self._set_auth_user(self._ops_user())
        rejected = self._client.post(
            f"/post-issuance/{application_id}/transitions",
            json={"to_status": "REJECTED", "comment": "Недостаточно оснований"},
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json()["status"], "ARCHIVED")
        self.assertEqual(rejected.json()["certificate"]["status"], "ACTIVE")

    def test_same_action_returns_existing_editable_draft(self) -> None:
        certificate_id = self._create_active_certificate()
        first = self._client.post(
            "/post-issuance/drafts",
            json={"source_certificate_id": certificate_id, "action_type": "SUSPEND"},
        )
        self.assertEqual(first.status_code, 200)

        second = self._client.post(
            "/post-issuance/drafts",
            json={"source_certificate_id": certificate_id, "action_type": "SUSPEND"},
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["id"], first.json()["id"])
        self.assertEqual(second.json()["status"], "DRAFT")

    def test_duplicate_active_process_returns_409_for_different_action(self) -> None:
        certificate_id = self._create_active_certificate()
        first = self._client.post(
            "/post-issuance/drafts",
            json={"source_certificate_id": certificate_id, "action_type": "SUSPEND"},
        )
        self.assertEqual(first.status_code, 200)

        second = self._client.post(
            "/post-issuance/drafts",
            json={"source_certificate_id": certificate_id, "action_type": "TERMINATE"},
        )
        self.assertEqual(second.status_code, 409)

    def test_delete_draft_archives_editable_post_issuance(self) -> None:
        certificate_id = self._create_active_certificate()
        created = self._client.post(
            "/post-issuance/drafts",
            json={"source_certificate_id": certificate_id, "action_type": "SUSPEND"},
        )
        self.assertEqual(created.status_code, 200)
        application_id = created.json()["id"]

        deleted = self._client.delete(f"/post-issuance/{application_id}/draft")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["status"], "ARCHIVED")

        mine = self._client.get("/post-issuance/mine")
        self.assertEqual(mine.status_code, 200)
        archived = next(item for item in mine.json()["items"] if item["id"] == application_id)
        self.assertEqual(archived["status"], "ARCHIVED")

    def test_delete_submitted_post_issuance_returns_409(self) -> None:
        certificate_id = self._create_active_certificate()
        created = self._client.post(
            "/post-issuance/drafts",
            json={"source_certificate_id": certificate_id, "action_type": "SUSPEND"},
        )
        self.assertEqual(created.status_code, 200)
        application_id = created.json()["id"]

        self._client.put(
            f"/post-issuance/{application_id}/draft",
            json=self._prepare_payload(created.json()["payload"], "SUSPEND"),
        )
        self._client.post(
            f"/post-issuance/{application_id}/basis/attach",
            json={
                "slot": "post_issuance_basis",
                "object_key": f"post-issuance/{application_id}/post_issuance_basis/basis.pdf",
                "file_name": "basis.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
        )
        submitted = self._client.post(f"/post-issuance/{application_id}/submit")
        self.assertEqual(submitted.status_code, 200)

        deleted = self._client.delete(f"/post-issuance/{application_id}/draft")
        self.assertEqual(deleted.status_code, 409)

    def test_applicant_cannot_approve_post_issuance(self) -> None:
        certificate_id = self._create_active_certificate()
        created = self._client.post(
            "/post-issuance/drafts",
            json={"source_certificate_id": certificate_id, "action_type": "SUSPEND"},
        )
        application_id = created.json()["id"]
        self._client.put(
            f"/post-issuance/{application_id}/draft",
            json=self._prepare_payload(created.json()["payload"], "SUSPEND"),
        )
        self._client.post(
            f"/post-issuance/{application_id}/basis/attach",
            json={
                "slot": "post_issuance_basis",
                "object_key": f"post-issuance/{application_id}/post_issuance_basis/basis.pdf",
                "file_name": "basis.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
        )
        self._client.post(f"/post-issuance/{application_id}/submit")

        response = self._client.post(
            f"/post-issuance/{application_id}/transitions",
            json={"to_status": "APPROVED"},
        )
        self.assertEqual(response.status_code, 403)

    def test_foreign_applicant_cannot_open_post_issuance(self) -> None:
        certificate_id = self._create_active_certificate()
        created = self._client.post(
            "/post-issuance/drafts",
            json={"source_certificate_id": certificate_id, "action_type": "SUSPEND"},
        )
        application_id = created.json()["id"]

        self._set_auth_user(self._other_applicant_user())
        response = self._client.get(f"/post-issuance/{application_id}")
        self.assertEqual(response.status_code, 403)

    def test_applicant_cannot_submit_ops_only_termination_reason(self) -> None:
        certificate_id = self._create_active_certificate()
        created = self._client.post(
            "/post-issuance/drafts",
            json={"source_certificate_id": certificate_id, "action_type": "TERMINATE"},
        )
        self.assertEqual(created.status_code, 200)
        application_id = created.json()["id"]

        updated = self._client.put(
            f"/post-issuance/{application_id}/draft",
            json={
                **created.json()["payload"],
                "request_source": "OPS",
                "termination_reason_code": "term_product_nonconformity",
                "reason_detail": "Попытка выбрать OPS-only основание",
                "note": "Негативный сценарий",
                "remediation_deadline": "2026-03-10T09:30",
            },
        )
        self.assertEqual(updated.status_code, 200)

        attached = self._client.post(
            f"/post-issuance/{application_id}/basis/attach",
            json={
                "slot": "post_issuance_basis",
                "object_key": f"post-issuance/{application_id}/post_issuance_basis/basis.pdf",
                "file_name": "basis.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
        )
        self.assertEqual(attached.status_code, 200)

        submitted = self._client.post(f"/post-issuance/{application_id}/submit")
        self.assertEqual(submitted.status_code, 422)
        self.assertIn("not available", submitted.json()["detail"])


if __name__ == "__main__":
    unittest.main()
