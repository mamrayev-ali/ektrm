import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.applicant_lookup_service import ApplicantLookupService

GBD_UL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ns3:responseDataType xmlns:ns3="http://gbdulinfobybin_v2.egp.gbdul.tamur.kz">
  <Status>
    <Code>002</Code>
    <NameRu>Запрос обработан успешно</NameRu>
  </Status>
  <Organization>
    <BIN>123456789012</BIN>
    <RegStatus>
      <NameRu>Зарегистрирован</NameRu>
    </RegStatus>
    <RegistrationDate>2020-01-15+06:00</RegistrationDate>
    <FullNameRu>Товарищество с ограниченной ответственностью "Тест"</FullNameRu>
    <FullNameKz>"Тест" жауапкершілігі шектеулі серіктестігі</FullNameKz>
    <OrganizationLeader>
      <Position>
        <PositionType>
          <NameRu>Руководитель</NameRu>
        </PositionType>
      </Position>
      <IIN>890627301030</IIN>
    </OrganizationLeader>
    <Activity>
      <ActivityNameRu>Испытания продукции</ActivityNameRu>
    </Activity>
    <Address>
      <DistrictRu>город Алматы</DistrictRu>
      <RegionRu>Бостандыкский район</RegionRu>
      <CityRu>-</CityRu>
      <StreetRu>Проспект Абая</StreetRu>
      <BuildingType>
        <NameRu>здание</NameRu>
      </BuildingType>
      <BuildingNumber>10</BuildingNumber>
    </Address>
    <StatCommInfo>
      <AddressFact>
        <NameRu>город Алматы Бостандыкский район Проспект Абая, дом 10</NameRu>
      </AddressFact>
    </StatCommInfo>
  </Organization>
</ns3:responseDataType>
"""


class _FakeResponse:
    def __init__(self, *, text: str = "", json_payload: dict | None = None) -> None:
        self.text = text
        self._json_payload = json_payload or {}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._json_payload


class ApplicantLookupServiceTests(unittest.TestCase):
    def test_lookup_by_bin_merges_gbd_ul_and_kompra(self) -> None:
        service = ApplicantLookupService(
            gbd_ul_base_url="http://gbd.local",
            gbd_ul_env="prod",
            gbd_ul_extract=True,
            gbd_ul_req_xml=True,
            gbd_ul_timeout_seconds=5,
            kompra_api_base_url="https://kompra.local/api/v2",
            kompra_api_token="token",
            kompra_timeout_seconds=5,
        )

        with patch(
            "app.services.applicant_lookup_service.httpx.get",
            side_effect=[
                _FakeResponse(text=GBD_UL_XML),
                _FakeResponse(
                    json_payload={
                        "status": True,
                        "content": {
                            "surname": "КАБЫЛОВ",
                            "name": "МЕЙРАМБЕК",
                            "middle_name": "МАЛИБЕКОВИЧ",
                            "birthdate": "27-06-1989",
                            "gender": "male",
                            "iin": "890627301030",
                        },
                    }
                ),
            ],
        ):
            result = service.lookup_by_bin("123456789012")

        resolved = result["resolved_fields"]
        self.assertEqual(resolved["applicant_name"], 'Товарищество с ограниченной ответственностью "Тест"')
        self.assertEqual(resolved["applicant_head_iin"], "890627301030")
        self.assertEqual(resolved["applicant_head_name"], "КАБЫЛОВ МЕЙРАМБЕК МАЛИБЕКОВИЧ")
        self.assertEqual(resolved["applicant_head_name_kz"], "КАБЫЛОВ МЕЙРАМБЕК МАЛИБЕКОВИЧ")
        self.assertNotIn("applicant_head_position", resolved)
        self.assertEqual(resolved["applicant_activity_address"], "legal")
        self.assertEqual(result["integration_snapshot"]["gbd_ul"]["primary_activity_ru"], "Испытания продукции")


if __name__ == "__main__":
    unittest.main()
