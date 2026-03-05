# Architecture Rules (e-КТРМ)

## Architectural style
- MVP реализуется как микросервисный набор с прагматичной укрупненностью, не как монолит.
- Бизнес-критичные переходы (статусы заявок/сертификатов) реализуются доменными сервисами, а не контроллерами.
- Базовая структура backend: `router -> service -> persistence`.

## Required service boundaries
- `gateway-service`:
  - единая внешняя точка входа;
  - разделение публичных и защищенных маршрутов;
  - проброс correlation-id.
- `applications-service`:
  - Ордер 3 + post-issuance заявки;
  - state transitions;
  - валидации и архивирование заявок.
- `certificates-service`:
  - генерация сертификатов и snapshot;
  - mock-подпись;
  - версии сертификата и публикация в реестр.
- `reference-data-service`:
  - read-only справочники и lookup-реестры.
- `files-service`:
  - хранение вложений в MinIO;
  - генерация PDF.
- `notifications-service`:
  - in-app уведомления;
  - read/unread;
  - realtime push.

## Dependency direction
- `gateway -> domain services`.
- Domain services не зависят друг от друга напрямую через shared mutable state.
- Межсервисная синхронизация — через явные API/event contracts.
- `reference-data-service` является upstream для lookup-значений; write-операции UI на справочники не допускаются.

## Data ownership
- Источник identity: Keycloak.
- Источник доменных данных: PostgreSQL сервисов.
- Сертификат хранит snapshot данных заявки; после формирования нельзя строить сертификат на «живом» mutable-состоянии заявки.
- Post-issuance prefill строится от выбранного сертификата.

## Event and async rules
- Фоновые операции выполняются через Celery + Redis:
  - генерация PDF;
  - публикация в реестр;
  - рассылка уведомлений;
  - тяжелые post-issuance обновления.
- Каждое событие, влияющее на статус, должно фиксироваться в истории и аудит-логе.

## Architecture invariants
- В MVP активны только `Applicant` и `OPS`; дополнительные роли закладываются архитектурно, но не активируются.
- Сценарий `возобновление` не реализуется.
- Любой защищенный endpoint должен проверять роль и ownership на backend.

## High-risk areas
- Auth/RBAC и role mapping.
- Миграции/статусы/версионирование сертификатов.
- Публичный read-only реестр и стабильность внешнего контракта.
