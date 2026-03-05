# Domain Rules (e-КТРМ)

## Scope boundaries
- Обязательный functional scope:
  - Ордер 3 (первичная сертификация),
  - Ордер 4 (сертификат и публикация),
  - Ордер 5 (переоформление, приостановление, прекращение).
- Явно вне scope MVP:
  - `возобновление`,
  - реальные внешние интеграции,
  - реальная ЭЦП,
  - дополнительные активные роли.

## Active roles and visibility
- `Applicant`:
  - видит только свои заявки/сертификаты/post-issuance процессы.
- `OPS`:
  - видит все заявки и сертификаты;
  - выполняет review/decision/sign/publication действия.
- Public:
  - видит только публичный read-only реестр опубликованных сертификатов.

## Order 3 status model
- Supported statuses:
  - `DRAFT`
  - `SUBMITTED`
  - `REGISTERED`
  - `IN_REVIEW`
  - `REVISION_REQUESTED`
  - `PROTOCOL_ATTACHED`
  - `APPROVED`
  - `REJECTED`
  - `ARCHIVED`
  - `COMPLETED`
- Required transitions:
  - `DRAFT -> SUBMITTED`
  - `SUBMITTED -> REGISTERED`
  - `REGISTERED -> IN_REVIEW`
  - `IN_REVIEW -> REVISION_REQUESTED`
  - `REVISION_REQUESTED -> IN_REVIEW`
  - `IN_REVIEW -> PROTOCOL_ATTACHED`
  - `PROTOCOL_ATTACHED -> APPROVED`
  - `PROTOCOL_ATTACHED -> REJECTED`
  - `REJECTED -> ARCHIVED`
  - `APPROVED -> COMPLETED`

## Certificate lifecycle (Order 4)
- Supported statuses:
  - `GENERATED`
  - `SIGNED`
  - `PUBLISHED`
  - `ACTIVE`
  - `REISSUED`
  - `SUSPENDED`
  - `TERMINATED`
- Rules:
  - сертификат создается из `APPROVED` заявки;
  - формирование использует snapshot полей заявки;
  - публикация фиксируется как отдельное событие даже если финальный статус сразу `ACTIVE`.

## Post-issuance (Order 5)
- Supported actions:
  - `REISSUE`, `SUSPEND`, `TERMINATE`.
- Post-issuance statuses:
  - `DRAFT`, `SUBMITTED`, `REGISTERED`, `IN_REVIEW`, `REVISION_REQUESTED`, `APPROVED`, `REJECTED`, `ARCHIVED`, `REGISTRY_UPDATED`, `COMPLETED`.
- Outcome mapping:
  - успешный reissue -> `REISSUED`;
  - успешный suspend -> `SUSPENDED`;
  - успешный terminate -> `TERMINATED`.

## Required domain invariants
- Номер заявки уникален.
- Номер сертификата уникален.
- Нельзя создавать конфликтующие активные post-issuance процессы на один сертификат без явного разрешения бизнес-правил.
- Любой отказ переводит заявку в архив и формирует уведомление.
- При успешном post-issuance обязательно обновляется история версий/состояний сертификата.

## Reference-data rules
- Справочники физически хранятся в БД и seed-ятся.
- UI CRUD для справочников в MVP запрещен.
- Причины приостановления/прекращения/переоформления берутся из аналитики как есть; ручная «юридическая правка» без отдельного согласования запрещена.
