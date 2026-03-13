from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class SignatureValidationResult:
    is_valid: bool
    validator_name: str
    validation_error_code: str | None = None
    validation_details: str | None = None
    revocation_check_mode: str | None = None
    signer_subject: str | None = None
    signer_serial_number: str | None = None
    signer_iin: str | None = None
    signer_bin: str | None = None
    accepted_without_crypto_verify: bool = False


class CertificateSignatureValidator(Protocol):
    def validate(self, *, payload_base64: str, signature_cms_base64: str, signature_mode: str) -> SignatureValidationResult:
        ...


class OpenSslCertificateSignatureValidator:
    def __init__(
        self,
        openssl_bin: str,
        ca_file: str | None,
        crl_file: str | None,
    ) -> None:
        self._openssl_bin = openssl_bin
        self._ca_file = ca_file
        self._crl_file = crl_file

    def validate(self, *, payload_base64: str, signature_cms_base64: str, signature_mode: str) -> SignatureValidationResult:
        if shutil.which(self._openssl_bin) is None:
            return SignatureValidationResult(
                is_valid=False,
                validator_name="openssl-cms",
                validation_error_code="validation_backend_unavailable",
                validation_details="OpenSSL executable was not found",
            )

        if not self._ca_file or not Path(self._ca_file).is_file():
            return SignatureValidationResult(
                is_valid=False,
                validator_name="openssl-cms",
                validation_error_code="validation_backend_unavailable",
                validation_details="Trusted CA file is not configured",
            )

        normalized_payload_base64 = normalize_base64_block(payload_base64)
        normalized_signature_cms_base64 = normalize_base64_block(signature_cms_base64)

        try:
            payload_bytes = base64.b64decode(normalized_payload_base64, validate=True)
            signature_bytes = base64.b64decode(normalized_signature_cms_base64, validate=True)
        except Exception:
            return SignatureValidationResult(
                is_valid=False,
                validator_name="openssl-cms",
                validation_error_code="invalid_signature_payload",
                validation_details="Payload or signature is not valid Base64",
            )

        with tempfile.TemporaryDirectory(prefix="ektrm-sign-") as temp_dir:
            temp_path = Path(temp_dir)
            payload_path = temp_path / "payload.bin"
            signature_path = temp_path / "signature.der"
            payload_path.write_bytes(payload_bytes)
            signature_path.write_bytes(signature_bytes)

            verify_command = [
                self._openssl_bin,
                "cms",
                "-verify",
                "-inform",
                "DER",
                "-binary",
                "-in",
                str(signature_path),
                "-CAfile",
                self._ca_file,
                "-purpose",
                "any",
                "-out",
                os.devnull,
            ]
            if signature_mode == "detached":
                verify_command.extend(["-content", str(payload_path)])

            revocation_mode = "SKIPPED"
            if self._crl_file and Path(self._crl_file).is_file():
                verify_command.extend(["-crl_check", "-CRLfile", self._crl_file])
                revocation_mode = "CRL"

            verify_process = subprocess.run(
                verify_command,
                capture_output=True,
                text=True,
                check=False,
            )
            if verify_process.returncode != 0:
                return SignatureValidationResult(
                    is_valid=False,
                    validator_name="openssl-cms",
                    validation_error_code=_map_openssl_error_code(verify_process.stderr),
                    validation_details=(verify_process.stderr or verify_process.stdout).strip() or None,
                    revocation_check_mode=revocation_mode,
                )

            signer_subject = None
            signer_serial = None
            signer_iin = None
            signer_bin = None

            print_certs_process = subprocess.run(
                [
                    self._openssl_bin,
                    "pkcs7",
                    "-inform",
                    "DER",
                    "-in",
                    str(signature_path),
                    "-print_certs",
                    "-text",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if print_certs_process.returncode == 0:
                signer_subject = _extract_first_match(r"Subject:\s*(.+)", print_certs_process.stdout)
                signer_serial = _extract_first_match(r"Serial Number:\s*([A-Fa-f0-9:\s]+)", print_certs_process.stdout)
                signer_iin = _extract_first_match(r"SERIALNUMBER=IIN(\d+)", print_certs_process.stdout)
                signer_bin = _extract_first_match(r"SERIALNUMBER=BIN(\d+)", print_certs_process.stdout)

            return SignatureValidationResult(
                is_valid=True,
                validator_name="openssl-cms",
                revocation_check_mode=revocation_mode,
                signer_subject=signer_subject,
                signer_serial_number=_normalize_serial(signer_serial),
                signer_iin=signer_iin,
                signer_bin=signer_bin,
            )


class TemporaryGostFallbackCertificateSignatureValidator:
    _CMS_SIGNED_DATA_OID_DER = bytes.fromhex("06092A864886F70D010702")

    def __init__(self, openssl_bin: str) -> None:
        self._openssl_bin = openssl_bin

    def validate(self, *, payload_base64: str, signature_cms_base64: str, signature_mode: str) -> SignatureValidationResult:
        normalized_payload_base64 = normalize_base64_block(payload_base64)
        normalized_signature_cms_base64 = normalize_base64_block(signature_cms_base64)

        try:
            base64.b64decode(normalized_payload_base64, validate=True)
            signature_bytes = base64.b64decode(normalized_signature_cms_base64, validate=True)
        except Exception:
            return SignatureValidationResult(
                is_valid=False,
                validator_name="temporary-gost-fallback",
                validation_error_code="invalid_signature_payload",
                validation_details="Payload or signature is not valid Base64",
            )

        if signature_mode not in {"detached", "attached"}:
            return SignatureValidationResult(
                is_valid=False,
                validator_name="temporary-gost-fallback",
                validation_error_code="invalid_signature_mode",
                validation_details="Unsupported signature mode for temporary validator",
            )

        if not self._looks_like_cms_signed_data(signature_bytes):
            return SignatureValidationResult(
                is_valid=False,
                validator_name="temporary-gost-fallback",
                validation_error_code="invalid_signature_container",
                validation_details="Signature does not look like a CMS SignedData container",
            )

        signer_subject, signer_serial, signer_iin, signer_bin = self._extract_signature_metadata(signature_bytes)
        return SignatureValidationResult(
            is_valid=True,
            validator_name="temporary-gost-fallback",
            validation_details=(
                "Temporary GOST fallback accepted CMS without server-side cryptographic verification"
            ),
            revocation_check_mode="SKIPPED",
            signer_subject=signer_subject,
            signer_serial_number=signer_serial,
            signer_iin=signer_iin,
            signer_bin=signer_bin,
            accepted_without_crypto_verify=True,
        )

    def _looks_like_cms_signed_data(self, signature_bytes: bytes) -> bool:
        return bool(signature_bytes) and signature_bytes.startswith(b"\x30") and self._CMS_SIGNED_DATA_OID_DER in signature_bytes

    def _extract_signature_metadata(self, signature_bytes: bytes) -> tuple[str | None, str | None, str | None, str | None]:
        if shutil.which(self._openssl_bin) is None:
            return None, None, None, None

        with tempfile.TemporaryDirectory(prefix="ektrm-sign-meta-") as temp_dir:
            signature_path = Path(temp_dir) / "signature.der"
            signature_path.write_bytes(signature_bytes)
            process = subprocess.run(
                [
                    self._openssl_bin,
                    "pkcs7",
                    "-inform",
                    "DER",
                    "-in",
                    str(signature_path),
                    "-print_certs",
                    "-text",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if process.returncode != 0:
                return None, None, None, None

            stdout = process.stdout
            signer_subject = _extract_first_match(r"Subject:\s*(.+)", stdout)
            signer_serial = _normalize_serial(_extract_first_match(r"Serial Number:\s*([A-Fa-f0-9:\s]+)", stdout))
            signer_iin = _extract_first_match(r"SERIALNUMBER=IIN(\d+)", stdout)
            signer_bin = _extract_first_match(r"SERIALNUMBER=BIN(\d+)", stdout)
            return signer_subject, signer_serial, signer_iin, signer_bin


def build_certificate_signature_validator() -> CertificateSignatureValidator:
    validator_mode = os.getenv("CERT_SIGNATURE_VALIDATOR_MODE", "openssl").strip().lower()
    openssl_bin = os.getenv("CERT_SIGNATURE_OPENSSL_BIN", "openssl")
    ca_file = os.getenv("CERT_SIGNATURE_TRUSTED_CA_FILE")
    crl_file = os.getenv("CERT_SIGNATURE_CRL_FILE")
    if validator_mode == "temporary_gost_fallback":
        return TemporaryGostFallbackCertificateSignatureValidator(openssl_bin=openssl_bin)
    return OpenSslCertificateSignatureValidator(
        openssl_bin=openssl_bin,
        ca_file=ca_file,
        crl_file=crl_file,
    )


def normalize_base64_block(value: str) -> str:
    normalized = (value or "").strip()
    normalized = re.sub(r"-----BEGIN [^-]+-----", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"-----END [^-]+-----", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def _extract_first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text)
    if not match:
        return None
    return match.group(1).strip()


def _normalize_serial(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"\s+", "", value).replace(":", "").upper()


def _map_openssl_error_code(stderr: str) -> str:
    lowered = (stderr or "").lower()
    if "certificate has expired" in lowered:
        return "expired_certificate"
    if "certificate revoked" in lowered:
        return "revoked_certificate"
    if "verify error" in lowered or "unable to get issuer certificate" in lowered:
        return "broken_chain"
    if "content verify error" in lowered or "verification failure" in lowered:
        return "invalid_signature"
    return "validation_internal_error"
