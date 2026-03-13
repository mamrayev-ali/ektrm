import sys
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import CurrentUser
from app.models import certificate as certificate_models  # noqa: F401
from app.models.base import Base
from app.repositories.application_repository import ApplicationRepository
from app.repositories.certificate_repository import CertificateRepository
from app.services.application_state_service import ApplicationStateService
from app.services.certificate_signature_validation import SignatureValidationResult, normalize_base64_block
from app.services.certificate_service import CertificateService


class FakeSignatureValidator:
    def __init__(self, *, accepted_without_crypto_verify: bool = False) -> None:
        self.last_payload_base64: str | None = None
        self.last_signature_cms_base64: str | None = None
        self.accepted_without_crypto_verify = accepted_without_crypto_verify

    def validate(self, *, payload_base64: str, signature_cms_base64: str, signature_mode: str) -> SignatureValidationResult:
        self.last_payload_base64 = payload_base64
        self.last_signature_cms_base64 = signature_cms_base64
        return SignatureValidationResult(
            is_valid=True,
            validator_name="fake-validator",
            revocation_check_mode="TEST",
            signer_subject="CN=OPS Signer",
            signer_serial_number="ABC123",
            accepted_without_crypto_verify=self.accepted_without_crypto_verify,
        )


class CertificateServiceTests(unittest.TestCase):
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
        self._session: Session = self._session_factory()
        self._app_repository = ApplicationRepository(self._session)
        self._certificate_repository = CertificateRepository(self._session)
        self._signature_validator = FakeSignatureValidator()
        self._certificate_service = CertificateService(
            self._certificate_repository,
            signature_validator=self._signature_validator,
        )
        self._application_service = ApplicationStateService(
            repository=self._app_repository,
            certificate_service=self._certificate_service,
        )
        self._applicant = CurrentUser(
            subject="applicant-1",
            username="applicant.demo",
            email="applicant@example.local",
            roles=frozenset({"Applicant"}),
            claims={},
        )
        self._ops = CurrentUser(
            subject="ops-1",
            username="ops.demo",
            email="ops@example.local",
            roles=frozenset({"OPS"}),
            claims={},
        )

    def tearDown(self) -> None:
        self._session.rollback()
        self._session.close()

    def _payload(self) -> dict:
        return {
            "applicant_name": "ТОО Тест",
            "applicant_bin": "123456789012",
            "applicant_address": "г. Алматы",
            "ops_code": "OPS-KZ-001",
            "cert_scheme_code": "SCHEME-1",
            "products": [{"name": "Провод"}],
        }

    def _approve_application(self) -> dict:
        app = self._application_service.create_draft(payload=self._payload(), current_user=self._applicant)
        app = self._application_service.transition(application_id=app["id"], to_status="SUBMITTED", current_user=self._applicant)
        return self._application_service.apply_ops_decision(
            application_id=app["id"],
            decision_status="APPROVED",
            current_user=self._ops,
            protocol_metadata={
                "slot": "protocol_test_report",
                "object_key": f"applications/{app['id']}/protocol_test_report/protocol.pdf",
                "file_name": "protocol.pdf",
                "content_type": "application/pdf",
                "size_bytes": 512,
                "etag": "etag-approve",
            },
        )

    def _approve_with_certificate(self) -> dict:
        approved = self._approve_application()
        return approved["certificate"]

    def test_approved_transition_generates_certificate(self) -> None:
        approved = self._approve_application()
        self.assertEqual(approved["status"], "APPROVED")
        self.assertIn("certificate", approved)
        self.assertEqual(approved["certificate"]["status"], "GENERATED")
        self.assertEqual(approved["certificate"]["source_application_id"], approved["id"])

    def test_snapshot_is_immutable_after_application_payload_changes(self) -> None:
        approved = self._approve_application()
        certificate_before = approved["certificate"]
        self.assertEqual(certificate_before["snapshot"]["payload"]["applicant_name"], "ТОО Тест")

        application_row = self._app_repository.get_application(approved["id"])
        self.assertIsNotNone(application_row)
        self._app_repository.update_payload(
            application=application_row,
            payload={**self._payload(), "applicant_name": "ТОО Изменено"},
        )
        self._app_repository.commit()

        certificate_after = self._certificate_service.get_certificate(
            certificate_id=certificate_before["id"],
            current_user=self._ops,
        )
        self.assertEqual(certificate_after["snapshot"]["payload"]["applicant_name"], "ТОО Тест")

    def test_generation_is_blocked_for_non_approved_application(self) -> None:
        draft = self._application_service.create_draft(payload=self._payload(), current_user=self._applicant)
        application_row = self._app_repository.get_application(draft["id"])
        self.assertIsNotNone(application_row)
        with self.assertRaises(HTTPException) as context:
            self._certificate_service.generate_for_approved_application(
                application=application_row,
                current_user=self._ops,
            )
        self.assertEqual(context.exception.status_code, 409)

    def test_sign_and_publish_sets_active_status_and_metadata(self) -> None:
        certificate = self._approve_with_certificate()
        prepared = self._certificate_service.prepare_signature(
            certificate_id=certificate["id"],
            current_user=self._ops,
            signer_kind="signAny",
        )
        signed = self._certificate_service.sign_and_publish(
            certificate_id=certificate["id"],
            current_user=self._ops,
            operation_id=prepared["signature_operation"]["operation_id"],
            payload_base64=prepared["signature_operation"]["payload_base64"],
            payload_sha256_hex=prepared["signature_operation"]["payload_sha256_hex"],
            signature_cms_base64="ZmFrZS1zaWduYXR1cmU=",
            signature_mode="detached",
            comment="Signed with ECP",
        )
        self.assertEqual(signed["certificate"]["status"], "ACTIVE")
        self.assertEqual(signed["certificate"]["signed_by_subject"], "ops-1")
        self.assertIsNotNone(signed["certificate"]["signed_at"])
        self.assertIsNotNone(signed["certificate"]["published_at"])
        self.assertEqual(signed["signature_operation"]["validation_result"], "VALID")

    def test_sign_and_publish_requires_ops_role(self) -> None:
        certificate = self._approve_with_certificate()
        prepared = self._certificate_service.prepare_signature(
            certificate_id=certificate["id"],
            current_user=self._ops,
            signer_kind="signAny",
        )
        with self.assertRaises(HTTPException) as context:
            self._certificate_service.sign_and_publish(
                certificate_id=certificate["id"],
                current_user=self._applicant,
                operation_id=prepared["signature_operation"]["operation_id"],
                payload_base64=prepared["signature_operation"]["payload_base64"],
                payload_sha256_hex=prepared["signature_operation"]["payload_sha256_hex"],
                signature_cms_base64="ZmFrZS1zaWduYXR1cmU=",
                signature_mode="detached",
            )
        self.assertEqual(context.exception.status_code, 403)

    def test_sign_and_publish_rejects_double_sign(self) -> None:
        certificate = self._approve_with_certificate()
        prepared = self._certificate_service.prepare_signature(
            certificate_id=certificate["id"],
            current_user=self._ops,
            signer_kind="signAny",
        )
        self._certificate_service.sign_and_publish(
            certificate_id=certificate["id"],
            current_user=self._ops,
            operation_id=prepared["signature_operation"]["operation_id"],
            payload_base64=prepared["signature_operation"]["payload_base64"],
            payload_sha256_hex=prepared["signature_operation"]["payload_sha256_hex"],
            signature_cms_base64="ZmFrZS1zaWduYXR1cmU=",
            signature_mode="detached",
        )
        with self.assertRaises(HTTPException) as context:
            self._certificate_service.sign_and_publish(
                certificate_id=certificate["id"],
                current_user=self._ops,
                operation_id=prepared["signature_operation"]["operation_id"],
                payload_base64=prepared["signature_operation"]["payload_base64"],
                payload_sha256_hex=prepared["signature_operation"]["payload_sha256_hex"],
                signature_cms_base64="ZmFrZS1zaWduYXR1cmU=",
                signature_mode="detached",
            )
        self.assertEqual(context.exception.status_code, 409)

    def test_sign_and_publish_normalizes_whitespace_and_pem_wrapped_signature(self) -> None:
        certificate = self._approve_with_certificate()
        prepared = self._certificate_service.prepare_signature(
            certificate_id=certificate["id"],
            current_user=self._ops,
            signer_kind="signAny",
        )
        payload_base64 = prepared["signature_operation"]["payload_base64"]
        normalized_signature = "ZmFrZS1zaWduYXR1cmU="
        pem_wrapped_signature = "-----BEGIN PKCS7-----\nZmFrZS1zaWdu\nYXR1cmU=\n-----END PKCS7-----"

        signed = self._certificate_service.sign_and_publish(
            certificate_id=certificate["id"],
            current_user=self._ops,
            operation_id=prepared["signature_operation"]["operation_id"],
            payload_base64=f"{payload_base64[:32]}\n{payload_base64[32:]}",
            payload_sha256_hex=prepared["signature_operation"]["payload_sha256_hex"],
            signature_cms_base64=pem_wrapped_signature,
            signature_mode="detached",
            comment="Signed with ECP",
        )

        self.assertEqual(signed["certificate"]["status"], "ACTIVE")
        self.assertEqual(self._signature_validator.last_payload_base64, normalize_base64_block(payload_base64))
        self.assertEqual(self._signature_validator.last_signature_cms_base64, normalized_signature)

    def test_sign_and_publish_marks_temporary_fallback_result(self) -> None:
        self._signature_validator = FakeSignatureValidator(accepted_without_crypto_verify=True)
        self._certificate_service = CertificateService(
            self._certificate_repository,
            signature_validator=self._signature_validator,
        )
        self._application_service = ApplicationStateService(
            repository=self._app_repository,
            certificate_service=self._certificate_service,
        )
        certificate = self._approve_with_certificate()
        prepared = self._certificate_service.prepare_signature(
            certificate_id=certificate["id"],
            current_user=self._ops,
            signer_kind="signAny",
        )

        signed = self._certificate_service.sign_and_publish(
            certificate_id=certificate["id"],
            current_user=self._ops,
            operation_id=prepared["signature_operation"]["operation_id"],
            payload_base64=prepared["signature_operation"]["payload_base64"],
            payload_sha256_hex=prepared["signature_operation"]["payload_sha256_hex"],
            signature_cms_base64="ZmFrZS1zaWduYXR1cmU=",
            signature_mode="detached",
            comment="Signed with temporary fallback",
        )

        self.assertEqual(signed["certificate"]["status"], "ACTIVE")
        self.assertEqual(signed["signature_operation"]["validation_result"], "ACCEPTED_WITHOUT_CRYPTO_VERIFY")


if __name__ == "__main__":
    unittest.main()
