# e-КТРМ — MVP Platform Bootstrap (T1) + Auth Baseline (T2) + Reference Data (T3) + Order 3 Domain Model (T4) + Applicant Wizard (T5) + OPS Review and Protocol Attachment (T6) + Certificate Generation and Snapshot (T7) + Mock Signing and Registry (T8) + Post-Issuance Suspend / Terminate (T9)

Репозиторий содержит AgentKit-процесс и стартовую контейнерную топологию MVP Phase 1 для e-КТРМ.

Реализовано в тикетах `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, `T7`, `T8` и `T9`:
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
- действие `Подписать ЭЦП` для роли `OPS`: frontend готовит detached CMS через NCALayer, backend валидирует доступным verifier path и после успешной проверки публикует сертификат во внутренний/публичный реестры.
- registry API:
  - `GET /registry/internal` (Applicant: только свои, OPS: все),
  - `GET /registry/public` (без авторизации, read-only только опубликованные).
- UI внутреннего реестра сертификатов (`frontend/index.html`) + отдельная публичная страница (`/public-registry.html`).
- baseline Ордер 5: post-issuance процесс `Приостановление` / `Прекращение` для опубликованных сертификатов.
- API post-issuance:
  - `POST /post-issuance/drafts`,
  - `PUT /post-issuance/{id}/draft`,
  - `POST /post-issuance/{id}/submit`,
  - `POST /post-issuance/{id}/transitions`,
  - `POST /post-issuance/{id}/basis/attach`,
  - `GET /post-issuance/mine`,
  - `GET /post-issuance/ops/queue`.
- file-slot API расширен поддержкой `post_issuance_basis` с таргетом `entity_kind=post_issuance`.
- UI T9 встроен в раздел `Реестр сертификатов`: создание процесса, загрузка файла-основания и OPS-очередь suspend/terminate.

## Быстрый старт

1. Скопировать окружение:
   - Linux/macOS: `cp .env.example .env`
   - Windows: `Copy-Item .env.example .env`
2. Поднять платформу:
   - Linux/macOS: `./scripts/bootstrap.sh`
   - Windows: `pwsh -File .\\scripts\\bootstrap.ps1`
   - bootstrap-скрипты сначала валидируют `.env` через `python scripts/validate_deploy_env.py`, затем автоматически пересобирают runtime image, выполняют `alembic upgrade head` и idempotent sync seeded reference-data внутри контейнера.
   - Альтернатива: `docker compose up -d --build`
   - если запуск делается напрямую без bootstrap-скриптов, после старта контейнеров нужно отдельно выполнить:
     - `docker compose run --rm --no-deps gateway-service python -m alembic -c /app/alembic.ini upgrade head`
     - `docker compose run --rm --no-deps gateway-service python -m app.seed.reference_data_sync`
3. Проверить health endpoints:
   - Gateway: `http://localhost:8180/health`
   - Applications: `http://localhost:8081/health`
   - Certificates: `http://localhost:8082/health`
   - Reference Data: `http://localhost:8083/health`
   - Files: `http://localhost:8084/health`
   - Notifications: `http://localhost:8085/health`
   - Frontend: `http://localhost:9035/health`
4. Остановить платформу:
   - `docker compose down`

## Server deployment checklist

- Default host ports in this repo are now:
  - `gateway`: `8180`
  - `frontend`: `9035`
  - `keycloak`: `8088`
  - `postgres`: `6432`
  - `redis`: `7379`
- Frontend runtime URLs are now generated inside the nginx container from env:
  - `FRONTEND_API_BASE`
  - `FRONTEND_OIDC_AUTHORITY`
  - `FRONTEND_OIDC_CLIENT_ID`
  - if explicit frontend URLs are empty, runtime config derives them from the current host plus `GATEWAY_PORT` / `KEYCLOAK_EXPOSE_PORT`
- Important: only host-exposed ports change. Internal container ports remain:
  - PostgreSQL: `5432`
  - Redis: `6379`
  - Keycloak: `8080`
- Common fatal mistake:
  - do not set `POSTGRES_PORT=6432`, `REDIS_PORT=7379`, or `KEYCLOAK_URL=http://keycloak:8180`;
  - those are host ports, not internal Docker-network ports.
- If Keycloak realm already exists in a persistent volume, changes in `infra/keycloak/realm-export.json` will not retroactively update the live client. In that case, update client `ektrm-web` manually in Keycloak admin UI or recreate the imported realm.
- Before treating deployment as successful, always run:
  - `docker compose run --rm --no-deps gateway-service python -m alembic -c /app/alembic.ini upgrade head`
  - `docker compose run --rm --no-deps gateway-service python -m app.seed.reference_data_sync`

## Контейнерная топология

Application services:
- `gateway-service`
- `applications-service`
- `certificates-service`
- `reference-data-service`
- `files-service`
- `notifications-service`
- `frontend`

Test profile services:
- `runtime-tests` — полный runtime test suite
- `gateway-test` — auth/runtime smoke unit tests
- `applications-test` — application state/API tests
- `certificates-test` — certificate service/API tests
- `reference-data-test` — reference-data API tests
- `files-test` — file-slot API tests

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

1. Открыть фронтенд: `http://localhost:9035`.
2. Нажать `Войти` и авторизоваться одним из demo users.
3. Вызвать:
   - `GET /auth/me` (любой авторизованный пользователь),
   - `GET /auth/applicant-area` (только роль `Applicant`),
   - `GET /auth/ops-area` (только роль `OPS`).
4. Проверить ожидаемое поведение:
   - при отсутствии токена backend возвращает `401`;
   - при недостаточной роли backend возвращает `403`.

Публичные endpoint-ы для auth baseline (gateway):
- `GET http://localhost:8180/auth/config`
- `GET http://localhost:8180/auth/me` (Bearer required)
- `GET http://localhost:8180/auth/applicant-area` (Bearer + `Applicant`)
- `GET http://localhost:8180/auth/ops-area` (Bearer + `OPS`)

## T3 Reference Data baseline: как применить и проверить

1. Применить миграции:
   - host-run: `python -m alembic -c services/runtime/alembic.ini upgrade head`
   - container-run: `docker compose run --rm --no-deps gateway-service python -m alembic -c /app/alembic.ini upgrade head`
   - после изменения seed-справочников синхронизировать данные в уже существующей БД: `docker compose run --rm --no-deps gateway-service python -m app.seed.reference_data_sync`
2. Проверить, что таблицы созданы:
   - `reference_dictionaries`
   - `reference_dictionary_items`
   - `ops_registry`
   - `accreditation_attestats`
3. Проверить read-only endpoint-ы (с Bearer токеном):
   - `GET http://localhost:8180/reference-data/dictionaries`
   - `GET http://localhost:8180/reference-data/dictionaries/termination_reason/items`
   - `GET http://localhost:8180/reference-data/ops-registry`
   - `GET http://localhost:8180/reference-data/accreditation-attestats`

## T4 Order 3 Domain Model: как применить и проверить

1. Применить миграции:
   - host-run: `python -m alembic -c services/runtime/alembic.ini upgrade head`
   - container-run: `docker compose run --rm --no-deps gateway-service python -m alembic -c /app/alembic.ini upgrade head`
2. Проверить новые таблицы:
   - `cert_application`
   - `cert_application_status_history`
3. Проверить API Ордер 3 через gateway (с Bearer токеном):
   - создать черновик: `POST http://localhost:8180/applications/drafts`
   - отправить заявку: `POST http://localhost:8180/applications/{id}/submit`
   - выполнить переход: `POST http://localhost:8180/applications/{id}/transitions`
   - получить историю: `GET http://localhost:8180/applications/{id}/history`
4. Проверить базовую матрицу переходов:
   - допустимые переходы соответствуют `TECH_SPEC` (раздел 10.8);
   - недопустимый переход должен возвращать `409`.

## T5 Order 3 Applicant Wizard: как проверить

1. Открыть `http://localhost:9035` и выполнить вход (`applicant.demo / Applicant123!`).
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
2. Через UI открыть `http://localhost:9035`:
   - для роли `OPS` отображается реестр заявок заявителей;
   - кнопка `Открыть` в строке заявки переводит в OPS-режим формы (read-only данные заявки + блок действий `Проверка и решение`);
   - доступные действия в UI:
     - `Принять` (перевод в `IN_REVIEW`, а для `SUBMITTED` последовательно делает `REGISTERED -> IN_REVIEW`);
     - `На доработку` (`IN_REVIEW -> REVISION_REQUESTED`);
     - `Прикрепить протокол` (upload в `files-service` + attach, результат `PROTOCOL_ATTACHED`);
     - `Принять решение` (`APPROVED` или `REJECTED`);
     - `Завершить` (`APPROVED -> COMPLETED`).
3. Получить очередь ОПС (API-проверка):
   - `GET http://localhost:8180/applications/ops/queue`
   - опционально фильтр: `?statuses=IN_REVIEW,PROTOCOL_ATTACHED`.
4. Выполнить review-переходы заявки:
   - `POST http://localhost:8180/applications/{id}/transitions` с `{"to_status":"REGISTERED"}`;
   - `POST ...` с `{"to_status":"IN_REVIEW"}`.
5. Загрузить протокол в `files-service` (через gateway):
   - `POST http://localhost:8180/files/slots/upload`
   - body:
     - `application_id`,
     - `slot=protocol_test_report`,
     - `file_name` (pdf/doc/docx/xls/xlsx/jpg/jpeg/png),
     - `content_base64`,
     - `content_type`.
6. Привязать протокол к заявке:
   - `POST http://localhost:8180/applications/{id}/protocol/attach`
   - body содержит metadata из шага upload (`slot`, `object_key`, `file_name`, `content_type`, `size_bytes`, `etag`).
   - ожидаемый результат: статус `PROTOCOL_ATTACHED`.
7. Проверить отказную ветку:
   - `POST http://localhost:8180/applications/{id}/transitions` с `{"to_status":"REJECTED","comment":"..."}`.
   - ожидаемый результат: заявка автоматически переходит в `ARCHIVED`, в истории есть записи `REJECTED` и `ARCHIVED`.
8. Проверить role-based visibility:
   - Applicant не может вызывать `GET /applications/ops/queue` и OPS review transitions (ожидается `403`).

## T7 Certificate Generation and Snapshot: как проверить

1. Войти как `ops.demo / Ops123456!` (или Bearer с ролью `OPS`) и довести заявку до `PROTOCOL_ATTACHED`.
2. Выполнить переход в `APPROVED`:
   - `POST http://localhost:8180/applications/{id}/transitions` с `{"to_status":"APPROVED"}`.
3. Проверить, что в ответе появился объект `certificate`:
   - `status = GENERATED`;
   - заполнены `certificate_number`, `source_application_id`, `snapshot`.
4. Проверить read API сертификатов:
   - `GET http://localhost:8180/certificates/by-application/{application_id}`
   - `GET http://localhost:8180/certificates/{certificate_id}`
5. Проверить инварианты:
   - до `APPROVED` сертификат по заявке не находится (`404`);
   - Applicant не может читать чужой сертификат (`403`);
   - snapshot не меняется при последующих изменениях payload заявки.

## T8 OPS ECP Signing, Publication and Registry: как проверить

1. Войти как `ops.demo / Ops123456!` и убедиться, что есть сертификат в статусе `GENERATED` (после `APPROVED` в Ордер 3).
2. Подписать сертификат:
   - UI: раздел `Реестр сертификатов` -> действие `Подписать ЭЦП`;
   - API flow:
     - `POST http://localhost:8180/certificates/{certificate_id}/sign/prepare` с body `{"signer_kind":"signAny"}`;
     - frontend подписывает `payloadBase64` через NCALayer;
     - `POST http://localhost:8180/certificates/{certificate_id}/sign` с `operation_id`, `payload_base64`, `payload_sha256_hex`, `signature_cms_base64`, `signature_mode`.
3. Проверить результат подписи:
   - статус становится `ACTIVE`;
    - заполнены поля `signed_by_subject`, `signed_at`, `published_at`.
   - в БД появляется запись `certificate_signature` с validation metadata.
4. Проверить внутренний реестр:
   - `GET http://localhost:8180/registry/internal` (Bearer required);
   - роль `OPS` видит все записи, роль `Applicant` видит только свои.
5. Проверить публичный read-only реестр:
   - `GET http://localhost:8180/registry/public` (без Bearer);
   - UI: `http://localhost:9035/public-registry.html`.
6. Проверить ограничения:
   - подпись сертификата не-ролью `OPS` возвращает `403`;
   - повторная подпись уже активного сертификата возвращает `409`.

## T9 Post-Issuance: Suspension and Termination

1. Войти как `applicant.demo / Applicant123!` и открыть раздел `Реестр сертификатов`.
2. Для сертификата в статусе `ACTIVE`:
   - нажать `Приостановить` или `Прекратить`;
   - заполнить причину, описание, примечание, `Срок устранения`;
   - прикрепить файл-основание;
   - нажать `Подать заявку`.
   - для `Причина прекращения`: заявитель видит только основание `Прекращение производства...`, роль `OPS` видит расширенный нормативный перечень.
3. Проверить API-эквивалент applicant-flow:
   - `POST http://localhost:8180/post-issuance/drafts`
   - `PUT http://localhost:8180/post-issuance/{id}/draft`
   - `POST http://localhost:8180/post-issuance/{id}/basis/attach`
   - `POST http://localhost:8180/post-issuance/{id}/submit`
4. Войти как `ops.demo / Ops123456!` и открыть раздел `Реестр сертификатов`:
   - в таблице `Очередь post-issuance` доступны `В работу`, `На доработку`, `Одобрить`, `Отказать`.
5. Проверить happy-path suspend:
   - `REGISTERED -> IN_REVIEW -> APPROVED`;
   - сертификат получает статус `SUSPENDED`;
   - `GET http://localhost:8180/registry/internal` и `GET http://localhost:8180/registry/public` показывают новый статус.
6. Проверить happy-path terminate:
   - `REGISTERED -> APPROVED`;
   - сертификат получает статус `TERMINATED`;
   - в ответе и internal registry выставляется `is_dangerous_product=true`.
7. Проверить reject path:
   - `POST http://localhost:8180/post-issuance/{id}/transitions` с `{"to_status":"REJECTED","comment":"..."}`.
   - ожидаемый результат: post-issuance заявка переводится в `ARCHIVED`, а статус сертификата не меняется.
8. Проверить ограничения:
   - applicant не может `APPROVE/REJECT` (`403`);
   - нельзя создать второй активный post-issuance процесс на тот же сертификат (`409`);
   - без файла-основания submit возвращает `422`.

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

Контейнерный запуск runtime-тестов:
- полный suite: `docker compose --profile test run --rm runtime-tests`
- auth/runtime: `docker compose --profile test run --rm gateway-test`
- applications: `docker compose --profile test run --rm applications-test`
- certificates: `docker compose --profile test run --rm certificates-test`
- reference-data: `docker compose --profile test run --rm reference-data-test`
- files: `docker compose --profile test run --rm files-test`
- точечный файл: `docker compose --profile test run --rm applications-test python -m unittest discover -s tests -p "test_applications_api.py"`

Дополнительная конфигурация backend verifier:
- `CERT_SIGNATURE_VALIDATOR_MODE` — режим backend verifier:
  - `openssl` — strict CMS verification через OpenSSL;
  - `temporary_gost_fallback` — dev/demo-only fallback для GOST CMS без server-side cryptographic verification.
- `CERT_SIGNATURE_OPENSSL_BIN` — путь к `openssl` внутри runtime environment;
- `CERT_SIGNATURE_TRUSTED_CA_FILE` — chain/CA bundle для проверки CMS;
- `CERT_SIGNATURE_CRL_FILE` — optional CRL file для `crl_check`.
- trust artifacts монтируются из `infra/cert-signing/` в контейнеры как `/app/cert-signing`.

Если verifier backend не настроен, операция подписи завершится ошибкой `validation_backend_unavailable` и сертификат не будет опубликован.
В локальном `docker-compose` по умолчанию включен `temporary_gost_fallback`, чтобы GOST-подпись через NCALayer проходила end-to-end как рабочий dev/demo flow. Этот режим сохраняет CMS и проверяет только техническую корректность контейнера подписи, но не выполняет полноценную криптографическую проверку цепочки НУЦ, отзыва и срока действия.

## Ограничения текущего этапа

- Ордер 3 для заявителя и OPS API-уровня реализован (wizard + draft/submit/delete + OPS queue/review/protocol attachment), Ордер 4 покрывает генерацию сертификата, OPS ECP signing flow и публикацию в реестры.
- Расширенный поиск/фильтрация публичного реестра и расширенные карточки сертификатов пока не реализованы.
- Широкий контур внешних интеграций по-прежнему вне текущего этапа; из runtime включен только точечный applicant lookup по `BIN` через backend-mediated ГБД ЮЛ + Kompra.
- Автозаполнение заявителя по `BIN` через ГБД ЮЛ + Kompra работает только при заполненных `GBD_UL_*` и `KOMPRA_*` переменных в `.env`; Kompra token хранится только на backend.
- Клиентское подписание через NCALayer реализуется, но полнота production-grade серверной проверки ЭЦП зависит от настроенного verifier toolchain и trust store.
