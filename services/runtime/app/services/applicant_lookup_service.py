from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from xml.etree import ElementTree

import httpx
from fastapi import HTTPException, status

BIN_PATTERN = re.compile(r"^\d{12}$")
IIN_PATTERN = re.compile(r"^\d{12}$")


class ApplicantLookupService:
    def __init__(
        self,
        *,
        gbd_ul_base_url: str,
        gbd_ul_env: str,
        gbd_ul_extract: bool,
        gbd_ul_req_xml: bool,
        gbd_ul_timeout_seconds: float,
        kompra_api_base_url: str,
        kompra_api_token: str,
        kompra_timeout_seconds: float,
    ) -> None:
        self._gbd_ul_base_url = gbd_ul_base_url.rstrip("/")
        self._gbd_ul_env = gbd_ul_env
        self._gbd_ul_extract = gbd_ul_extract
        self._gbd_ul_req_xml = gbd_ul_req_xml
        self._gbd_ul_timeout_seconds = gbd_ul_timeout_seconds
        self._kompra_api_base_url = kompra_api_base_url.rstrip("/")
        self._kompra_api_token = kompra_api_token
        self._kompra_timeout_seconds = kompra_timeout_seconds

    def lookup_by_bin(self, bin_value: str) -> dict[str, Any]:
        normalized_bin = str(bin_value or "").strip()
        if not BIN_PATTERN.fullmatch(normalized_bin):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Invalid applicant BIN format",
                    "field": "applicant_bin",
                    "expected": "12 digits",
                },
            )

        gbd_payload = self._fetch_gbd_ul(normalized_bin)
        leader_iin = str(gbd_payload.get("leader_iin") or "").strip()
        if not IIN_PATTERN.fullmatch(leader_iin):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "Applicant leader IIN is missing in GBD UL response",
                    "field": "applicant_head_iin",
                },
            )

        kompra_payload = self._fetch_kompra_fio(leader_iin)
        leader_full_name = self._build_full_name(kompra_payload)
        if not leader_full_name:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "Leader FIO is missing in Kompra response",
                    "field": "applicant_head_name",
                },
            )

        legal_address = str(gbd_payload.get("legal_address_ru") or "").strip()
        actual_address = str(gbd_payload.get("actual_address_ru") or "").strip()
        activity_address_mode = "other" if actual_address and actual_address != legal_address else "legal"
        resolved_actual_address = actual_address if activity_address_mode == "other" else ""

        resolved_fields = {
            "applicant_bin": normalized_bin,
            "applicant_name": str(gbd_payload.get("full_name_ru") or "").strip(),
            "applicant_name_kz": str(gbd_payload.get("full_name_kz") or "").strip(),
            "applicant_head_iin": leader_iin,
            "applicant_head_name": leader_full_name,
            "applicant_head_position": str(gbd_payload.get("leader_position_ru") or "").strip(),
            "applicant_address": legal_address,
            "applicant_activity_address": activity_address_mode,
            "actual_address": resolved_actual_address,
        }
        resolved_at = datetime.now(UTC).isoformat()
        return {
            "resolved_fields": resolved_fields,
            "integration_snapshot": {
                "source": "gbd_ul_kompra_v1",
                "resolved_at": resolved_at,
                "resolved_fields": resolved_fields,
                "gbd_ul": {
                    "bin": normalized_bin,
                    "status_code": gbd_payload.get("status_code"),
                    "status_name_ru": gbd_payload.get("status_name_ru"),
                    "registration_status_ru": gbd_payload.get("registration_status_ru"),
                    "registration_date": gbd_payload.get("registration_date"),
                    "full_name_ru": gbd_payload.get("full_name_ru"),
                    "full_name_kz": gbd_payload.get("full_name_kz"),
                    "leader_iin": leader_iin,
                    "leader_position_ru": gbd_payload.get("leader_position_ru"),
                    "legal_address_ru": legal_address,
                    "actual_address_ru": actual_address,
                    "primary_activity_ru": gbd_payload.get("primary_activity_ru"),
                },
                "kompra": {
                    "iin": leader_iin,
                    "status": True,
                    "surname": kompra_payload.get("surname"),
                    "name": kompra_payload.get("name"),
                    "middle_name": kompra_payload.get("middle_name"),
                    "birthdate": kompra_payload.get("birthdate"),
                    "gender": kompra_payload.get("gender"),
                },
            },
        }

    def _fetch_gbd_ul(self, bin_value: str) -> dict[str, Any]:
        params = {
            "bin": bin_value,
            "env": self._gbd_ul_env,
            "extract": str(self._gbd_ul_extract).lower(),
            "req_xml": str(self._gbd_ul_req_xml).lower(),
        }
        try:
            response = httpx.get(
                f"{self._gbd_ul_base_url}/ul",
                params=params,
                timeout=self._gbd_ul_timeout_seconds,
                headers={"Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8"},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "GBD UL lookup is unavailable",
                    "source": "gbd_ul",
                },
            ) from exc

        return self._parse_gbd_ul_xml(response.text, bin_value)

    def _fetch_kompra_fio(self, iin_value: str) -> dict[str, Any]:
        try:
            response = httpx.get(
                f"{self._kompra_api_base_url}/getFio",
                params={"iin": iin_value, "api-token": self._kompra_api_token},
                timeout=self._kompra_timeout_seconds,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Kompra lookup is unavailable",
                    "source": "kompra",
                },
            ) from exc

        if not isinstance(payload, dict) or payload.get("status") is not True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Leader FIO was not found in Kompra",
                    "source": "kompra",
                },
            )

        content = payload.get("content")
        if not isinstance(content, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "Kompra response content is malformed",
                    "source": "kompra",
                },
            )
        return content

    @staticmethod
    def _build_full_name(payload: dict[str, Any]) -> str:
        return " ".join(
            part.strip()
            for part in (
                str(payload.get("surname") or ""),
                str(payload.get("name") or ""),
                str(payload.get("middle_name") or ""),
            )
            if part.strip()
        )

    @classmethod
    def _parse_gbd_ul_xml(cls, raw_xml: str, requested_bin: str) -> dict[str, Any]:
        try:
            root = ElementTree.fromstring(raw_xml)
        except ElementTree.ParseError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "GBD UL response is not valid XML",
                    "source": "gbd_ul",
                },
            ) from exc

        cls._strip_namespaces(root)
        status_code = (root.findtext("./Status/Code") or "").strip()
        status_name_ru = (root.findtext("./Status/NameRu") or "").strip()
        if status_code != "002":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Applicant BIN was not found in GBD UL",
                    "source": "gbd_ul",
                    "status_code": status_code,
                    "status_name_ru": status_name_ru,
                },
            )

        organization = root.find("./Organization")
        if organization is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "GBD UL response does not contain organization data",
                    "source": "gbd_ul",
                },
            )

        response_bin = (organization.findtext("./BIN") or "").strip()
        if response_bin and response_bin != requested_bin:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "GBD UL returned data for another BIN",
                    "source": "gbd_ul",
                },
            )

        address_node = organization.find("./Address")
        activity_node = organization.find("./Activity")
        if activity_node is None:
            activity_node = organization.find("./StatCommInfo/Activity")

        return {
            "status_code": status_code,
            "status_name_ru": status_name_ru,
            "registration_status_ru": (organization.findtext("./RegStatus/NameRu") or "").strip(),
            "registration_date": (organization.findtext("./RegistrationDate") or "").strip(),
            "full_name_ru": (organization.findtext("./FullNameRu") or "").strip(),
            "full_name_kz": (organization.findtext("./FullNameKz") or "").strip(),
            "leader_iin": (organization.findtext("./OrganizationLeader/IIN") or "").strip(),
            "leader_position_ru": (organization.findtext("./OrganizationLeader/Position/PositionType/NameRu") or "").strip(),
            "legal_address_ru": cls._compose_legal_address(address_node),
            "actual_address_ru": (organization.findtext("./StatCommInfo/AddressFact/NameRu") or "").strip(),
            "primary_activity_ru": (activity_node.findtext("./ActivityNameRu") if activity_node is not None else "") or "",
        }

    @staticmethod
    def _strip_namespaces(root: ElementTree.Element) -> None:
        for node in root.iter():
            if "}" in node.tag:
                node.tag = node.tag.split("}", 1)[1]

    @staticmethod
    def _compose_legal_address(address_node: ElementTree.Element | None) -> str:
        if address_node is None:
            return ""
        building_type = (address_node.findtext("./BuildingType/NameRu") or "").strip()
        building_number = (address_node.findtext("./BuildingNumber") or "").strip()
        parts = [
            (address_node.findtext("./DistrictRu") or "").strip(),
            (address_node.findtext("./RegionRu") or "").strip(),
            "" if (address_node.findtext("./CityRu") or "").strip() == "-" else (address_node.findtext("./CityRu") or "").strip(),
            (address_node.findtext("./StreetRu") or "").strip(),
            " ".join(part for part in (building_type, building_number) if part),
        ]
        return ", ".join(part for part in parts if part)
