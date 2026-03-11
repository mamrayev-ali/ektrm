from __future__ import annotations

from datetime import date
from typing import TypedDict


class DictionaryDefinition(TypedDict):
    code: str
    name: str
    description: str


class DictionaryItemDefinition(TypedDict):
    dictionary_code: str
    code: str
    name: str
    sort_order: int
    legal_basis: str | None


class OpsRegistryDefinition(TypedDict):
    ops_code: str
    full_name: str
    bin: str
    accreditation_attestat_number: str
    head_name: str
    city: str


class AttestatDefinition(TypedDict):
    attestat_number: str
    ops_code: str
    issued_at: date
    expires_at: date
    status: str
    scope_summary: str


TERMINATION_REASON_APPLICANT_CODES = frozenset({"term_applicant_decision"})
TERMINATION_REASON_OPS_CODES = frozenset(
    {
        "term_applicant_decision",
        "term_negative_periodic_assessment",
        "term_change_notice_affecting_certified_indicators",
        "term_product_nonconformity",
        "term_unfulfilled_ops_obligations",
        "term_unfulfilled_clause_152_requirements",
        "term_confirmed_state_control_nonconformity",
        "term_standard_change_without_notice",
        "term_unapproved_changes_causing_nonconformity",
    }
)


MANDATORY_DICTIONARIES: tuple[DictionaryDefinition, ...] = (
    {"code": "certification_type", "name": "Вид сертификации", "description": "Классификатор вида сертификации."},
    {"code": "applicant_type", "name": "Тип заявителя", "description": "Классификатор типа заявителя."},
    {"code": "application_submission_by", "name": "Подача заявки от", "description": "Источник подачи заявки."},
    {"code": "application_submission_format", "name": "Формат подачи заявки", "description": "Формат подачи заявки."},
    {"code": "organization_type", "name": "Тип организации", "description": "Классификатор типа организации."},
    {"code": "certification_scheme", "name": "Схемы сертификации", "description": "Классификатор схем сертификации."},
    {"code": "certification_object", "name": "Объект сертификации", "description": "Классификатор объектов сертификации."},
    {"code": "measurement_unit", "name": "Единицы измерения", "description": "Классификатор единиц измерения."},
    {
        "code": "post_issuance_action_type",
        "name": "Тип действия",
        "description": "Тип действия для post-issuance: прекращение/приостановление.",
    },
    {"code": "application_initiator", "name": "Подать заявку", "description": "Кто инициировал заявку."},
    {"code": "suspension_reason", "name": "Причины приостановления", "description": "Основания для приостановления."},
    {"code": "termination_reason", "name": "Причины прекращения", "description": "Основания для прекращения."},
    {"code": "reissue_reason", "name": "Причины переоформления", "description": "Основания для переоформления."},
    {"code": "application_status", "name": "Статусы заявок", "description": "Статусы заявок в workflow."},
    {"code": "certificate_status", "name": "Статусы сертификатов", "description": "Статусы сертификатов в lifecycle."},
    {"code": "appendix_mode", "name": "Режим приложения", "description": "Режим приложения: таблица или свободная форма."},
)


MANDATORY_DICTIONARY_ITEMS: tuple[DictionaryItemDefinition, ...] = (
    {"dictionary_code": "certification_type", "code": "mandatory", "name": "Обязательная сертификация", "sort_order": 10, "legal_basis": None},
    {"dictionary_code": "certification_type", "code": "voluntary", "name": "Добровольная сертификация", "sort_order": 20, "legal_basis": None},
    {"dictionary_code": "applicant_type", "code": "manufacturer", "name": "Производитель", "sort_order": 10, "legal_basis": None},
    {"dictionary_code": "applicant_type", "code": "authorized_representative", "name": "Уполномоченное лицо", "sort_order": 20, "legal_basis": None},
    {"dictionary_code": "application_submission_by", "code": "applicant", "name": "От заявителя", "sort_order": 10, "legal_basis": None},
    {"dictionary_code": "application_submission_by", "code": "ops", "name": "От ОПС", "sort_order": 20, "legal_basis": None},
    {"dictionary_code": "application_submission_format", "code": "self_service", "name": "Самостоятельно", "sort_order": 10, "legal_basis": None},
    {"dictionary_code": "application_submission_format", "code": "ops_paper", "name": "ОПС с бумажного носителя", "sort_order": 20, "legal_basis": None},
    {"dictionary_code": "organization_type", "code": "legal_entity", "name": "Юридическое лицо", "sort_order": 10, "legal_basis": None},
    {"dictionary_code": "organization_type", "code": "individual_entrepreneur", "name": "Индивидуальный предприниматель", "sort_order": 20, "legal_basis": None},
    {"dictionary_code": "certification_scheme", "code": "scheme_1c", "name": "Схема 1с", "sort_order": 10, "legal_basis": None},
    {"dictionary_code": "certification_scheme", "code": "scheme_3c", "name": "Схема 3с", "sort_order": 20, "legal_basis": None},
    {"dictionary_code": "certification_object", "code": "serial_production", "name": "Серийная продукция", "sort_order": 10, "legal_basis": None},
    {"dictionary_code": "certification_object", "code": "batch", "name": "Партия продукции", "sort_order": 20, "legal_basis": None},
    {"dictionary_code": "measurement_unit", "code": "pcs", "name": "Штука", "sort_order": 10, "legal_basis": None},
    {"dictionary_code": "measurement_unit", "code": "kg", "name": "Килограмм", "sort_order": 20, "legal_basis": None},
    {"dictionary_code": "post_issuance_action_type", "code": "suspend", "name": "Приостановление", "sort_order": 10, "legal_basis": None},
    {"dictionary_code": "post_issuance_action_type", "code": "terminate", "name": "Прекращение", "sort_order": 20, "legal_basis": None},
    {"dictionary_code": "application_initiator", "code": "applicant", "name": "Заявитель", "sort_order": 10, "legal_basis": None},
    {"dictionary_code": "application_initiator", "code": "ops", "name": "ОПС", "sort_order": 20, "legal_basis": None},
    {
        "dictionary_code": "suspension_reason",
        "code": "susp_product_nonconformity",
        "name": "Выявлено несоответствие продукции установленным требованиям при подтверждении соответствия.",
        "sort_order": 10,
        "legal_basis": "Основание из аналитической выжимки Ордер 5, хранится без нормализации текста.",
    },
    {
        "dictionary_code": "suspension_reason",
        "code": "susp_labelling_violation",
        "name": "Нарушены требования к маркировке и предоставлению подтверждающих материалов по сертификату.",
        "sort_order": 20,
        "legal_basis": "Основание из аналитической выжимки Ордер 5, хранится без нормализации текста.",
    },
    {
        "dictionary_code": "termination_reason",
        "code": "term_applicant_decision",
        "name": "Прекращение производства данной продукции, услуги, процесса или по обоснованным иным причинам.",
        "sort_order": 10,
        "legal_basis": "Основание для заявителя и ОПС из PDF_ORDERS_DETAILED.md (дословный перенос с минимальной редакцией OCR).",
    },
    {
        "dictionary_code": "termination_reason",
        "code": "term_negative_periodic_assessment",
        "name": "Отрицательные результаты периодической оценки сертифицированной продукции, услуги, процесса, если выявленное несоответствие неисправимо или требуется проведение дополнительных испытаний (проверок) соответствия продукции, услуги, процесса требованиям, установленным техническими регламентами, документами по стандартизации.",
        "sort_order": 20,
        "legal_basis": "Основание для ОПС из PDF_ORDERS_DETAILED.md (пункты 2 и OCR-продолжение на той же странице).",
    },
    {
        "dictionary_code": "termination_reason",
        "code": "term_change_notice_affecting_certified_indicators",
        "name": "Наличие уведомления о внесении изменений в конструкцию (состав) продукции или технологию ее производства, которые влияют на показатели, удостоверяемые сертификацией, до проведения полных или частичных испытаний либо оценки состояния производства продукции, оказания услуг, процесса.",
        "sort_order": 30,
        "legal_basis": "Основание для ОПС из PDF_ORDERS_DETAILED.md (дословный перенос с минимальной редакцией OCR).",
    },
    {
        "dictionary_code": "termination_reason",
        "code": "term_product_nonconformity",
        "name": "Несоответствие продукции, услуги, процесса требованиям, установленным техническими регламентами, документами по стандартизации.",
        "sort_order": 40,
        "legal_basis": "Основание для ОПС из PDF_ORDERS_DETAILED.md (нормализация явных OCR-шумов без изменения смысла).",
    },
    {
        "dictionary_code": "termination_reason",
        "code": "term_unfulfilled_ops_obligations",
        "name": "Неисполнение обязательств перед ОПС, установленных схемой сертификации продукции (периодическая оценка), предусмотренных договором, заключенным между ними.",
        "sort_order": 50,
        "legal_basis": "Основание для ОПС из PDF_ORDERS_DETAILED.md (дословный перенос с минимальной редакцией OCR).",
    },
    {
        "dictionary_code": "termination_reason",
        "code": "term_unfulfilled_clause_152_requirements",
        "name": "Неисполнение требований подпунктов 2), 5) и 6) пункта 152 Правил оценки соответствия (приказ от 29 июня 2021 года № 433-НК) в период приостановления действия документа в сфере подтверждения соответствия.",
        "sort_order": 60,
        "legal_basis": "Основание для ОПС из PDF_ORDERS_DETAILED.md (нормализация явных OCR-шумов без изменения смысла).",
    },
    {
        "dictionary_code": "termination_reason",
        "code": "term_confirmed_state_control_nonconformity",
        "name": "Наличие подтвержденных сведений от государственных органов, осуществляющих государственный контроль и надзор в области технического регулирования, о несоответствии продукции, услуги, процесса требованиям, установленным техническими регламентами, документами по стандартизации, если выявленное несоответствие неисправимо или требуется проведение дополнительных испытаний (проверок) соответствия продукции, услуги, процесса указанным требованиям.",
        "sort_order": 70,
        "legal_basis": "Основание для ОПС из PDF_ORDERS_DETAILED.md (пункт 7 и OCR-продолжение).",
    },
    {
        "dictionary_code": "termination_reason",
        "code": "term_standard_change_without_notice",
        "name": "Изменение документа по стандартизации, метода контроля и испытаний, системы менеджмента, конструкции (состава), комплектности продукции, организации и (или) технологии производства продукции без соответствующего уведомления или согласования ОПС.",
        "sort_order": 80,
        "legal_basis": "Основание для ОПС из PDF_ORDERS_DETAILED.md (пункт 8, хранится как длинная юридическая формулировка).",
    },
    {
        "dictionary_code": "termination_reason",
        "code": "term_unapproved_changes_causing_nonconformity",
        "name": "Изменение документа по стандартизации, метода контроля и испытаний, системы менеджмента, конструкции (состава), комплектности продукции, организации и (или) технологии производства продукции, оказания услуг, процесса, если указанные изменения либо невыполнение требований вызывают несоответствие услуг и условий обслуживания требованиям, проверяемым при сертификации.",
        "sort_order": 90,
        "legal_basis": "Основание для ОПС из PDF_ORDERS_DETAILED.md (пункт 9, нормализация явных OCR-шумов без изменения смысла).",
    },
    {
        "dictionary_code": "reissue_reason",
        "code": "reissue_product_change",
        "name": "Изменение данных о продукции или изготовителе при сохранении области подтверждения соответствия.",
        "sort_order": 10,
        "legal_basis": "Основание из аналитической выжимки Ордер 5.",
    },
    {
        "dictionary_code": "reissue_reason",
        "code": "reissue_certificate_details",
        "name": "Корректировка реквизитов сертификата при сохранении результатов оценки соответствия.",
        "sort_order": 20,
        "legal_basis": "Основание из аналитической выжимки Ордер 5.",
    },
    {"dictionary_code": "application_status", "code": "DRAFT", "name": "Черновик", "sort_order": 10, "legal_basis": None},
    {"dictionary_code": "application_status", "code": "SUBMITTED", "name": "Подана", "sort_order": 20, "legal_basis": None},
    {"dictionary_code": "application_status", "code": "REVISION_REQUESTED", "name": "На доработке", "sort_order": 30, "legal_basis": None},
    {"dictionary_code": "application_status", "code": "APPROVED", "name": "Одобрена", "sort_order": 40, "legal_basis": None},
    {"dictionary_code": "application_status", "code": "REJECTED", "name": "Отказано", "sort_order": 50, "legal_basis": None},
    {"dictionary_code": "application_status", "code": "ARCHIVED", "name": "Архивирована", "sort_order": 60, "legal_basis": None},
    {"dictionary_code": "certificate_status", "code": "GENERATED", "name": "Сформирован", "sort_order": 10, "legal_basis": None},
    {"dictionary_code": "certificate_status", "code": "SIGNED", "name": "Подписан", "sort_order": 20, "legal_basis": None},
    {"dictionary_code": "certificate_status", "code": "PUBLISHED", "name": "Опубликован", "sort_order": 30, "legal_basis": None},
    {"dictionary_code": "certificate_status", "code": "ACTIVE", "name": "Действующий", "sort_order": 40, "legal_basis": None},
    {"dictionary_code": "certificate_status", "code": "REISSUED", "name": "Переоформлен", "sort_order": 50, "legal_basis": None},
    {"dictionary_code": "certificate_status", "code": "SUSPENDED", "name": "Приостановлен", "sort_order": 60, "legal_basis": None},
    {"dictionary_code": "certificate_status", "code": "TERMINATED", "name": "Прекращен", "sort_order": 70, "legal_basis": None},
    {"dictionary_code": "appendix_mode", "code": "table", "name": "Таблица", "sort_order": 10, "legal_basis": None},
    {"dictionary_code": "appendix_mode", "code": "free_form", "name": "В свободной форме", "sort_order": 20, "legal_basis": None},
)


OPS_REGISTRY_SEED: tuple[OpsRegistryDefinition, ...] = (
    {
        "ops_code": "OPS-KZ-001",
        "full_name": "ТОО \"КазСерт Тест\"",
        "bin": "190840001111",
        "accreditation_attestat_number": "KZ.A.01.1001",
        "head_name": "Айдаров Нурлан Серикович",
        "city": "Алматы",
    },
    {
        "ops_code": "OPS-KZ-002",
        "full_name": "АО \"НацЭксперт Сертификация\"",
        "bin": "160540009999",
        "accreditation_attestat_number": "KZ.A.01.1002",
        "head_name": "Омарова Дина Ермековна",
        "city": "Астана",
    },
)


ACCREDITATION_ATTESTATS_SEED: tuple[AttestatDefinition, ...] = (
    {
        "attestat_number": "KZ.A.01.1001",
        "ops_code": "OPS-KZ-001",
        "issued_at": date(2024, 1, 10),
        "expires_at": date(2029, 1, 10),
        "status": "ACTIVE",
        "scope_summary": "Подтверждение соответствия продукции серийного выпуска и партий продукции.",
    },
    {
        "attestat_number": "KZ.A.01.1002",
        "ops_code": "OPS-KZ-002",
        "issued_at": date(2023, 9, 1),
        "expires_at": date(2028, 9, 1),
        "status": "ACTIVE",
        "scope_summary": "Оценка соответствия по схемам 1с и 3с, включая инспекционный контроль.",
    },
)
