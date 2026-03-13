import base64
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.certificate_signature_validation import (  # noqa: E402
    TemporaryGostFallbackCertificateSignatureValidator,
    normalize_base64_block,
)


class CertificateSignatureValidationTests(unittest.TestCase):
    def test_normalize_base64_block_removes_pem_wrappers_and_whitespace(self) -> None:
        raw = "-----BEGIN CMS-----\nZmFrZS1zaWduYXR1cmU=\r\n-----END CMS-----"
        self.assertEqual(normalize_base64_block(raw), "ZmFrZS1zaWduYXR1cmU=")

    def test_temporary_gost_fallback_accepts_cms_like_signed_data(self) -> None:
        validator = TemporaryGostFallbackCertificateSignatureValidator(openssl_bin="openssl")
        payload_base64 = base64.b64encode(b'{"hello":"world"}').decode("ascii")
        cms_like_bytes = b"\x30\x82\x00\x16" + bytes.fromhex("06092A864886F70D010702") + b"temporary"
        signature_base64 = base64.b64encode(cms_like_bytes).decode("ascii")

        result = validator.validate(
            payload_base64=payload_base64,
            signature_cms_base64=signature_base64,
            signature_mode="detached",
        )

        self.assertTrue(result.is_valid)
        self.assertTrue(result.accepted_without_crypto_verify)
        self.assertEqual(result.validator_name, "temporary-gost-fallback")
        self.assertEqual(result.revocation_check_mode, "SKIPPED")

    def test_temporary_gost_fallback_rejects_non_cms_container(self) -> None:
        validator = TemporaryGostFallbackCertificateSignatureValidator(openssl_bin="openssl")
        payload_base64 = base64.b64encode(b"payload").decode("ascii")
        signature_base64 = base64.b64encode(b"not-a-cms-container").decode("ascii")

        result = validator.validate(
            payload_base64=payload_base64,
            signature_cms_base64=signature_base64,
            signature_mode="detached",
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.validation_error_code, "invalid_signature_container")


if __name__ == "__main__":
    unittest.main()
