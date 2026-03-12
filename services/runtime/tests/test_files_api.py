import sys
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import CurrentUser, get_current_user
from app.routers.files import get_file_slot_service, router as files_router
from app.services.file_slot_service import FileSlotService


class FakeStorage:
    def __init__(self) -> None:
        self.last_call: dict | None = None

    def put_object(self, key: str, content: bytes, content_type: str) -> str | None:
        self.last_call = {
            "key": key,
            "size": len(content),
            "content_type": content_type,
        }
        return "fake-etag"


class FilesApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._app = FastAPI()
        self._app.include_router(files_router)

        self._storage = FakeStorage()
        self._service = FileSlotService(storage=self._storage, max_file_size_bytes=1024 * 1024)

        def _service_override() -> FileSlotService:
            return self._service

        self._app.dependency_overrides[get_file_slot_service] = _service_override
        self._set_auth_user(
            CurrentUser(
                subject="ops-1",
                username="ops.demo",
                email="ops@example.local",
                roles=frozenset({"OPS"}),
                claims={},
            )
        )
        self._client = TestClient(self._app)

    def _set_auth_user(self, user: CurrentUser) -> None:
        def _auth_override() -> CurrentUser:
            return user

        self._app.dependency_overrides[get_current_user] = _auth_override

    def test_upload_slot_file_for_ops(self) -> None:
        response = self._client.post(
            "/files/slots/upload",
            json={
                "application_id": 11,
                "slot": "protocol_test_report",
                "file_name": "protocol.pdf",
                "content_type": "application/pdf",
                "content_base64": "dGVzdCBwcm90b2NvbA==",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["slot"], "protocol_test_report")
        self.assertEqual(data["application_id"], 11)
        self.assertEqual(data["etag"], "fake-etag")
        self.assertTrue(data["object_key"].startswith("applications/11/protocol_test_report/"))

    def test_upload_slot_file_denies_non_ops(self) -> None:
        self._set_auth_user(
            CurrentUser(
                subject="applicant-1",
                username="applicant.demo",
                email="applicant@example.local",
                roles=frozenset({"Applicant"}),
                claims={},
            )
        )
        response = self._client.post(
            "/files/slots/upload",
            json={
                "application_id": 11,
                "slot": "protocol_test_report",
                "file_name": "protocol.pdf",
                "content_type": "application/pdf",
                "content_base64": "dGVzdA==",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_upload_post_issuance_basis_allows_applicant(self) -> None:
        self._set_auth_user(
            CurrentUser(
                subject="applicant-1",
                username="applicant.demo",
                email="applicant@example.local",
                roles=frozenset({"Applicant"}),
                claims={},
            )
        )
        response = self._client.post(
            "/files/slots/upload",
            json={
                "entity_kind": "post_issuance",
                "entity_id": 17,
                "slot": "post_issuance_basis",
                "file_name": "basis.pdf",
                "content_type": "application/pdf",
                "content_base64": "dGVzdCBiYXNpcw==",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["post_issuance_id"], 17)
        self.assertEqual(data["entity_kind"], "post_issuance")
        self.assertTrue(data["object_key"].startswith("post-issuance/17/post_issuance_basis/"))

    def test_upload_application_scan_allows_applicant(self) -> None:
        self._set_auth_user(
            CurrentUser(
                subject="applicant-1",
                username="applicant.demo",
                email="applicant@example.local",
                roles=frozenset({"Applicant"}),
                claims={},
            )
        )
        response = self._client.post(
            "/files/slots/upload",
            json={
                "application_id": 12,
                "slot": "application_scan",
                "file_name": "application.pdf",
                "content_type": "application/pdf",
                "content_base64": "dGVzdCBhcHBsaWNhdGlvbg==",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["application_id"], 12)
        self.assertEqual(data["slot"], "application_scan")
        self.assertTrue(data["object_key"].startswith("applications/12/application_scan/"))

    def test_upload_critical_components_certificate_allows_applicant(self) -> None:
        self._set_auth_user(
            CurrentUser(
                subject="applicant-1",
                username="applicant.demo",
                email="applicant@example.local",
                roles=frozenset({"Applicant"}),
                claims={},
            )
        )
        response = self._client.post(
            "/files/slots/upload",
            json={
                "application_id": 12,
                "slot": "critical_components_certificate",
                "file_name": "components.pdf",
                "content_type": "application/pdf",
                "content_base64": "dGVzdCBjb21wb25lbnRz",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["application_id"], 12)
        self.assertEqual(data["slot"], "critical_components_certificate")
        self.assertTrue(data["object_key"].startswith("applications/12/critical_components_certificate/"))

    def test_upload_application_slot_rejects_post_issuance_target(self) -> None:
        response = self._client.post(
            "/files/slots/upload",
            json={
                "entity_kind": "post_issuance",
                "entity_id": 17,
                "slot": "application_scan",
                "file_name": "application.pdf",
                "content_type": "application/pdf",
                "content_base64": "dGVzdCBhcHBsaWNhdGlvbg==",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_upload_slot_file_rejects_invalid_extension(self) -> None:
        response = self._client.post(
            "/files/slots/upload",
            json={
                "application_id": 11,
                "slot": "protocol_test_report",
                "file_name": "protocol.exe",
                "content_type": "application/octet-stream",
                "content_base64": "dGVzdA==",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_upload_slot_file_rejects_invalid_base64(self) -> None:
        response = self._client.post(
            "/files/slots/upload",
            json={
                "application_id": 11,
                "slot": "protocol_test_report",
                "file_name": "protocol.pdf",
                "content_type": "application/pdf",
                "content_base64": "@@@invalid@@@",
            },
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
