# e-КТРМ — MVP Platform Bootstrap (T1) + Auth Baseline (T2) + Reference Data (T3) + Order 3 Domain Model (T4) + Applicant Wizard (T5) + OPS Review and Protocol Attachment (T6) + Certificate Generation and Snapshot (T7) + Mock Signing and Registry (T8)

Репозиторий содержит AgentKit-процесс и стартовую контейнерную топологию MVP Phase 1 для e-КТРМ.

Реализовано в тикетах `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, `T7` и `T8`:
- docker-compose с обязательными контейнерами платформы;
- bootstrap-скрипты запуска;
- минимальные runtime-сервисы с `/health` и `/readiness`;
- frontend wizard Ордер 3 (8 шагов) с действиями `Сохранить черновик`, `Подписать и отправить`, `Удалить черновик`;
- backend JWT verification через Keycloak JWKS и role-gated endpoint-ы `Applicant` / `OPS`.
- Alembic-миграции и seed обязательных справочников MVP + lookup-таблиц `ops_registry` и `accreditation_attestats`;
- read-only API справочников для `reference-data-service`.
- доменная модель Ордер 3 (`cert_application`, `cert_application_status_history`) и state engine переходов;
- API для черновиков/переходов статусов заявок с хранением истории статусов.
- API-операция удаления черновика: `DELETE /applications/{id}/draft` (переводит заявку в `ARCHIVED`).
- OPS review-контур: очередь ОПС, role-gated переходы review-статусов, прикрепление протокола и автоархивирование после отказа.
- files-service API для типизированного слота `protocol_test_report` с загрузкой в MinIO и возвратом metadata для привязки к заявке.
- baseline Ордер 4: автогенерация сертификата из `APPROVED` заявки, immutable snapshot и базовая история статусов сертификата (`GENERATED`).
- read API сертификатов: `GET /certificates/{id}` и `GET /certificates/by-application/{application_id}`.
- действие `Подписать` (mock-sign) для роли `OPS` с автоматической публикацией сертификата во внутренний/публичный реестры.
- registry API:
  - `GET /registry/internal` (Applicant: только свои, OPS: все),
  - `GET /registry/public` (без авторизации, read-only только опубликованные).
- UI внутреннего реестра сертификатов (`frontend/index.html`) + отдельная публичная страница (`/public-registry.html`).

## Быстрый старт

1. Скопировать окружение:
   - Linux/macOS: `cp .env.example .env`
   - Windows: `Copy-Item .env.example .env`
2. Поднять платформу:
   - Linux/macOS: `./scripts/bootstrap.sh`
   - Windows: `pwsh -File .\\scripts\\bootstrap.ps1`
   - Альтернатива: `docker compose up -d --build`
3. Проверить health endpoints:
   - Gateway: `http://localhost:8080/health`
   - Applications: `http://localhost:8081/health`
   - Certificates: `http://localhost:8082/health`
   - Reference Data: `http://localhost:8083/health`
   - Files: `http://localhost:8084/health`
   - Notifications: `http://localhost:8085/health`
   - Frontend: `http://localhost:4200/health`
4. Остановить платформу:
   - `docker compose down`

## Контейнерная топология

Application services:
- `gateway-service`
- `applications-service`
- `certificates-service`
- `reference-data-service`
- `files-service`
- `notifications-service`
- `frontend`

Infrastructure services:
- `postgres` (PostgreSQL)
- `redis` (broker/cache)
- `minio` + `minio-init` (object storage + bucket bootstrap)
- `keycloak` (OIDC/RBAC baseline, realm import)

## Keycloak bootstrap

Реалм импортируется из:
- `infra/keycloak/realm-export.json`

Demo users:
- `applicant.demo` / `Applicant123!`
- `ops.demo` / `Ops123456!`

Админ Keycloak:
- логин/пароль задаются через `.env` (`KEYCLOAK_ADMIN_USER`, `KEYCLOAK_ADMIN_PASSWORD`).

## T2 Auth/RBAC baseline: как проверить

1. Открыть фронтенд: `http://localhost:4200`.
2. Нажать `Войти` и авторизоваться одним из demo users.
3. Вызвать:
   - `GET /auth/me` (любой авторизованный пользователь),
   - `GET /auth/applicant-area` (только роль `Applicant`),
   - `GET /auth/ops-area` (только роль `OPS`).
4. Проверить ожидаемое поведение:
   - при отсутствии токена backend возвращает `401`;
   - при недостаточной роли backend возвращает `403`.

Публичные endpoint-ы для auth baseline (gateway):
- `GET http://localhost:8080/auth/config`
- `GET http://localhost:8080/auth/me` (Bearer required)
- `GET http://localhost:8080/auth/applicant-area` (Bearer + `Applicant`)
- `GET http://localhost:8080/auth/ops-area` (Bearer + `OPS`)

## T3 Reference Data baseline: как применить и проверить

1. Применить миграции:
   - `python -m alembic -c services/runtime/alembic.ini upgrade head`
2. Проверить, что таблицы созданы:
   - `reference_dictionaries`
   - `reference_dictionary_items`
   - `ops_registry`
   - `accreditation_attestats`
3. Проверить read-only endpoint-ы (с Bearer токеном):
   - `GET http://localhost:8080/reference-data/dictionaries`
   - `GET http://localhost:8080/reference-data/dictionaries/termination_reason/items`
   - `GET http://localhost:8080/reference-data/ops-registry`
   - `GET http://localhost:8080/reference-data/accreditation-attestats`

## T4 Order 3 Domain Model: как применить и проверить

1. Применить миграции:
   - `python -m alembic -c services/runtime/alembic.ini upgrade head`
2. Проверить новые таблицы:
   - `cert_application`
   - `cert_application_status_history`
3. Проверить API Ордер 3 через gateway (с Bearer токеном):
   - создать черновик: `POST http://localhost:8080/applications/drafts`
   - отправить заявку: `POST http://localhost:8080/applications/{id}/submit`
   - выполнить переход: `POST http://localhost:8080/applications/{id}/transitions`
   - получить историю: `GET http://localhost:8080/applications/{id}/history`
4. Проверить базовую матрицу переходов:
   - допустимые переходы соответствуют `TECH_SPEC` (раздел 10.8);
   - недопустимый переход должен возвращать `409`.

## T5 Order 3 Applicant Wizard: как проверить

1. Открыть `http://localhost:4200` и выполнить вход (`applicant.demo / Applicant123!`).
2. Заполнить шаги wizard: `Заявитель` -> `Адрес заявителя` -> `ОПС` -> `Схема сертификации` -> `Данные по продукции` -> `Приложение` -> `Документы` -> `Примечание`.
3. Нажать `Сохранить черновик`:
   - backend создает/обновляет draft через `/applications/drafts` и `/applications/{id}/draft`.
4. Нажать `Подписать и отправить`:
   - при невалидных полях UI показывает ошибки валидации;
   - при валидных данных вызывается `/applications/{id}/submit`, статус становится `SUBMITTED`.
5. Для сохраненного draft нажать `Удалить черновик`:
   - вызывается `DELETE /applications/{id}/draft`;
   - заявка переводится в `ARCHIVED`.

## T6 OPS Review and Protocol Attachment: как проверить

1. Войти как `ops.demo / Ops123456!` (или использовать Bearer с ролью `OPS`).
2. Через UI открыть `http://localhost:4200`:
   - для роли `OPS` отображается реестр заявок заявителей;
   - кнопка `Открыть` в строке заявки переводит в OPS-режим формы (read-only данные заявки + блок действий `Проверка и решение`);
   - доступные действия в UI:
     - `Принять` (перевод в `IN_REVIEW`, а для `SUBMITTED` последовательно делает `REGISTERED -> IN_REVIEW`);
     - `На доработку` (`IN_REVIEW -> REVISION_REQUESTED`);
     - `Прикрепить протокол` (upload в `files-service` + attach, результат `PROTOCOL_ATTACHED`);
     - `Принять решение` (`APPROVED` или `REJECTED`);
     - `Завершить` (`APPROVED -> COMPLETED`).
3. Получить очередь ОПС (API-проверка):
   - `GET http://localhost:8080/applications/ops/queue`
   - опционально фильтр: `?statuses=IN_REVIEW,PROTOCOL_ATTACHED`.
4. Выполнить review-переходы заявки:
   - `POST http://localhost:8080/applications/{id}/transitions` с `{"to_status":"REGISTERED"}`;
   - `POST ...` с `{"to_status":"IN_REVIEW"}`.
5. Загрузить протокол в `files-service` (через gateway):
   - `POST http://localhost:8080/files/slots/upload`
   - body:
     - `application_id`,
     - `slot=protocol_test_report`,
     - `file_name` (pdf/doc/docx/xls/xlsx/jpg/jpeg/png),
     - `content_base64`,
     - `content_type`.
6. Привязать протокол к заявке:
   - `POST http://localhost:8080/applications/{id}/protocol/attach`
   - body содержит metadata из шага upload (`slot`, `object_key`, `file_name`, `content_type`, `size_bytes`, `etag`).
   - ожидаемый результат: статус `PROTOCOL_ATTACHED`.
7. Проверить отказную ветку:
   - `POST http://localhost:8080/applications/{id}/transitions` с `{"to_status":"REJECTED","comment":"..."}`.
   - ожидаемый результат: заявка автоматически переходит в `ARCHIVED`, в истории есть записи `REJECTED` и `ARCHIVED`.
8. Проверить role-based visibility:
   - Applicant не может вызывать `GET /applications/ops/queue` и OPS review transitions (ожидается `403`).

## T7 Certificate Generation and Snapshot: как проверить

1. Войти как `ops.demo / Ops123456!` (или Bearer с ролью `OPS`) и довести заявку до `PROTOCOL_ATTACHED`.
2. Выполнить переход в `APPROVED`:
   - `POST http://localhost:8080/applications/{id}/transitions` с `{"to_status":"APPROVED"}`.
3. Проверить, что в ответе появился объект `certificate`:
   - `status = GENERATED`;
   - заполнены `certificate_number`, `source_application_id`, `snapshot`.
4. Проверить read API сертификатов:
   - `GET http://localhost:8080/certificates/by-application/{application_id}`
   - `GET http://localhost:8080/certificates/{certificate_id}`
5. Проверить инварианты:
   - до `APPROVED` сертификат по заявке не находится (`404`);
   - Applicant не может читать чужой сертификат (`403`);
   - snapshot не меняется при последующих изменениях payload заявки.

## T8 Mock Signing, Publication and Registry: как проверить

1. Войти как `ops.demo / Ops123456!` и убедиться, что есть сертификат в статусе `GENERATED` (после `APPROVED` в Ордер 3).
2. Подписать сертификат:
   - UI: раздел `Реестр сертификатов` -> действие `Подписать`;
   - API: `POST http://localhost:8080/certificates/{certificate_id}/sign` с body `{"comment":"..."}`.
3. Проверить результат подписи:
   - статус становится `ACTIVE`;
   - заполнены поля `signed_by_subject`, `signed_at`, `published_at`.
4. Проверить внутренний реестр:
   - `GET http://localhost:8080/registry/internal` (Bearer required);
   - роль `OPS` видит все записи, роль `Applicant` видит только свои.
5. Проверить публичный read-only реестр:
   - `GET http://localhost:8080/registry/public` (без Bearer);
   - UI: `http://localhost:4200/public-registry.html`.
6. Проверить ограничения:
   - подпись сертификата не-ролью `OPS` возвращает `403`;
   - повторная подпись уже активного сертификата возвращает `409`.

## Ключевые документы

- `.agentkit/docs/ROADMAP.md` — milestones и ticket plan.
- `.agentkit/docs/PROJECT_MAP.md` — карта архитектуры и контрактов.
- `.agentkit/rules/local/*.md` — локальные правила проекта.
- `AGENTS.md` — обязательный process contract.

## Верификация

Linux/macOS (bash):
- `./.agentkit/scripts/verify.sh smoke`
- `./.agentkit/scripts/verify.sh local`
- `./.agentkit/scripts/verify.sh ci`

Windows (PowerShell):
- `pwsh -File .agentkit/scripts/verify.ps1 detect`
- `pwsh -File .agentkit/scripts/verify.ps1 smoke`
- `pwsh -File .agentkit/scripts/verify.ps1 local`

## Ограничения текущего этапа

- Ордер 3 для заявителя и OPS API-уровня реализован (wizard + draft/submit/delete + OPS queue/review/protocol attachment), Ордер 4 baseline T7+T8 покрывает генерацию, mock-sign и публикацию в реестры.
- Расширенный поиск/фильтрация публичного реестра и расширенные карточки сертификатов пока не реализованы.
- Внешние интеграции (ГБД ЮЛ, НУЦ, госреестры) отключены.
- Реальная ЭЦП не реализуется.
