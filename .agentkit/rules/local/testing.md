# Testing Rules (e-КТРМ)

## Required test levels
- `smoke`:
  - базовая доступность сервисов и критичных маршрутов.
- `unit`:
  - доменные сервисы, валидации, маппинги статусов.
- `integration`:
  - API + persistence + миграции + файлы + справочники.
- `e2e`:
  - сквозные сценарии Applicant -> OPS -> Registry.
- `rbac`:
  - контроль видимости и запретов по ролям.
- `workflow`:
  - переходы статусов Ордер 3/4/5 и отказные ветки.

## Mandatory scenario coverage
- Ордер 3:
  - черновик, submit, auto-register, review, revision, protocol, approve/reject, archive/completed.
- Ордер 4:
  - certificate generation, mock-sign, publication, internal/public registry visibility.
- Ордер 5:
  - reissue/suspend/terminate, reasons validation, version creation, registry update, refusal path.

## Validation checks
- Формальные проверки полей:
  - БИН: 10 цифр;
  - ИИН: 12 цифр;
  - Телефон: `+7(7##) ### ## ##`;
  - корректные email/date/datetime;
  - draft допускает неполноту, submit не допускает.
- Проверки lookup:
  - выбранные значения должны существовать в БД.

## Data and demo requirements
- Seed обязателен для ручной демонстрации:
  - минимум 1 draft, 1 in-review, 1 revision-requested, 1 published certificate, 1 post-issuance кейс.
- Тестовые пользователи:
  - минимум 1 Applicant и 1 OPS.

## Verification contract
- `make verify-smoke`:
  - быстрые проверки структуры/контрактов.
- `make verify-local`:
  - полный локальный DoD текущего этапа.
- `make verify-ci`:
  - CI DoD и gate для завершения тикета.

## Non-negotiables
- Никаких placeholder/fake tests.
- Нельзя обходить verify scripts ради «зеленого» статуса.
