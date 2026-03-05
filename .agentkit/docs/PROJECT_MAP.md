# PROJECT_MAP — e-КТРМ (Platform Bootstrap Stage)

This file is the persistent, human-readable **map of the repository**.
It exists so that a new agent chat can quickly understand **what lives where**, **why it exists**, and **what contracts matter**.

**Strict rule:** If any repo files change in a ticket, this file must be updated in the same ticket.
This is enforced by `.agentkit/scripts/verify.sh` (DOC-gate). No exceptions.

---

## 0) TL;DR
- What this system does:
  - Репозиторий хранит процессный каркас AgentKit и базовую runtime-платформу e-КТРМ (MVP Phase 1) с приоритетом Ордер 3 -> Ордер 4 -> Ордер 5 (без возобновления).
- Key user flows:
  - Applicant создает/отправляет заявку, OPS проверяет/возвращает/принимает решение, система формирует сертификат, OPS mock-подписывает, сертификат публикуется в реестр, далее доступны post-issuance действия.
- Tech stack:
  - Целевой: Angular SPA, Python/FastAPI микросервисы, PostgreSQL + SQLAlchemy/Alembic, Redis + Celery, MinIO, Keycloak, WebSocket, Docker Compose.
  - Текущий этап репозитория: docker-compose topology + bootstrap-сценарии + runtime baseline c OIDC/JWT/RBAC (`T2`) и demo protected endpoint-ами.
- Where to start reading the code:
  - `docker-compose.yml`,
  - `services/runtime/app/main.py`,
  - `services/runtime/app/auth.py`,
  - `frontend/index.html`,
  - `infra/keycloak/realm-export.json`,
  - `scripts/bootstrap.sh` и `scripts/bootstrap.ps1`,
  - `README.md`,
  - `.agentkit/_temp/TECH_SPEC.md` (источник истины по домену),
  - `.agentkit/docs/ROADMAP.md`.

## 1) Repo structure (high level)
- `/.agentkit/` — процессный каркас AgentKit (правила, шаблоны, документация, скрипты верификации).
  - Ownership: команда разработки/архитектор процесса.
  - Boundary: инфраструктура процесса, не бизнес-код продукта.
- `/.agentkit/docs/` — живые документы проекта (`ROADMAP.md`, `PROJECT_MAP.md`).
  - Boundary: описание планов, структуры и контрактов; обновляются в каждом тикете.
- `/.agentkit/rules/common/` — универсальные правила разработки.
  - Boundary: общие инженерные практики, не доменная специфика e-КТРМ.
- `/.agentkit/rules/local/` — проектные правила e-КТРМ (архитектура, домен, безопасность, тестирование, интеграции, CI).
  - Boundary: локальные инструкции, привязанные к `TECH_SPEC.md`.
- `/.agentkit/scripts/` — универсальные verify-раннеры (`verify.sh`, `verify.ps1`) и вендор-утилиты.
- `/.agentkit/_temp/` — рабочие исходники аналитики (`TECH_SPEC.md`, `PDF_ORDERS_DETAILED.md`, BPMN jpg).
  - Boundary: источник требований на этапе intake/adaptation; каталог gitignored.
- `/.agents/skills/` — локальные навыки Codex (`project-intake`, `ticket-planning`).
- `/logs/agent/` — локальные аудиторские логи тикетов (gitignored).
- `/docker-compose.yml` — контейнерная топология T1 (core services + infrastructure).
- `/services/runtime/` — единый Python/FastAPI runtime-шаблон для gateway и доменных сервисов.
- `/frontend/` — контейнер статического frontend baseline (nginx + OIDC/RBAC demo shell + health probes).
- `/infra/keycloak/` — realm import для локального Keycloak baseline (`Applicant`, `OPS`).
- `/scripts/bootstrap.sh`, `/scripts/bootstrap.ps1` — единый bootstrap для локального старта платформы.

## 2) Key contracts & boundaries
- Architectural principles:
  - Микросервисный стиль с прагматичной укрупненностью сервисов для MVP.
  - Явное разделение слоев: `router -> service -> persistence`.
  - Бизнес-переходы статусов кодируются доменными сервисами, не контроллерами.
  - Snapshot-подход для сертификатов: сертификат не зависит от «живой» заявки после генерации.
- Public interfaces:
  - REST API по доменным группам: applications, certificates, post-issuance, registry, notifications, reference-data.
  - OpenAPI — обязательный контракт backend-to-frontend.
  - Публичный API реестра — read-only.
  - Для T2 добавлены auth baseline endpoint-ы: `/auth/config`, `/auth/me`, `/auth/applicant-area`, `/auth/ops-area`.
- Error handling strategy:
  - Frontend: пользовательские сообщения + field-level validation state.
  - Backend: структурированные ошибки с доменными кодами и без утечки чувствительных данных.
- Logging/observability conventions:
  - Audit обязателен для CRUD/статусов/публикации/подписи/архивирования.
  - Field-level audit обязателен для критичных полей (номер/статус/срок сертификата, причины post-issuance, ключевые реквизиты).
  - Correlation-id должен пробрасываться через gateway и сервисы (планируемый контракт на этапе реализации).

## 3) Domain map (important concepts)
- Core domain entities:
  - `cert_application`, `certificate`, `certificate_version`, `post_issuance_application`.
  - `stored_file`, `notification`, `audit_log`, `field_audit_log`.
  - Reference/lookup: ОПС, аттестаты, схемы, статусы, причины действий.
- Main business rules:
  - Активные роли MVP: только `Applicant` и `OPS`.
  - Order 3: workflow заявка -> review -> decision -> generate certificate.
  - Order 4: mock-sign + publication in internal/public registry.
  - Order 5: reissue/suspend/terminate (resume explicitly out of scope).
  - Post-issuance forms prefill from source certificate.
- Invariants (things that must always be true):
  - Сертификат создается только из одобренной заявки.
  - Каждое успешное post-issuance действие создает историю состояния/версий.
  - Внешний публичный реестр показывает только опубликованные сертификаты.
  - Backend всегда финальный источник истины для валидности и авторизации.
  - Уникальны номер заявки и номер сертификата; запрещены конфликтующие активные post-issuance процессы на один сертификат без явного разрешения.

## 4) Public API surface (if applicable)
- Where the API contract lives:
  - Целевой контракт: OpenAPI в backend-сервисах (будет добавлен в тикетах реализации).
- Versioning strategy:
  - Semver API namespace (`/api/v1/...`) и эволюционные non-breaking изменения в рамках версии.
- Critical endpoints / operations (planned):
  - `POST /applications/drafts`, `POST /applications/{id}/submit`, `POST /applications/{id}/review-actions`
  - `POST /applications/{id}/protocol`, `POST /applications/{id}/decision`
  - `GET /certificates`, `POST /certificates/{id}/sign-mock`, `POST /certificates/{id}/publish`
  - `POST /post-issuance/drafts`, `POST /post-issuance/{id}/submit`, `POST /post-issuance/{id}/decision`
  - `GET /registry/public`
  - `GET /notifications`, `POST /notifications/{id}/read`

## 5) Data & migrations (if applicable)
- Database(s):
  - PostgreSQL (основная доменная БД).
  - Redis (брокер/кэш/реaltime support).
  - MinIO (S3-compatible object storage).
- Migration approach:
  - Alembic migration chain + deterministic seed scripts.
  - Любые изменения схемы через отдельные migration tickets.
- Rollback approach:
  - Для каждого migration тикета обязателен rollback-план (down migration/compensation).
  - На risky migrations требуется отдельный PR.
- Critical tables/collections (high level):
  - Applications: `cert_application`, `cert_application_status_history`.
  - Certificates: `certificate`, `certificate_version`, `certificate_status_history`.
  - Post-issuance: `post_issuance_application`, `post_issuance_status_history`.
  - Reference: `ref_*`, `ops_registry`, `accreditation_attestat`.
  - Infra/domain cross-cutting: `stored_file`, `notification`, `audit_log`, `field_audit_log`.

## 6) Frontend / UI surface (if applicable)
- Routing approach:
  - Angular SPA route guards as UX layer; backend authorization is mandatory enforcement.
- State management approach:
  - Feature-level state by domain modules (applications, certificates, registry, notifications).
  - Realtime updates via WebSocket + fallback refresh.
- Where styles/tokens live:
  - Базовый визуальный источник: `prototype.html`.
  - Локальные UI-правила: `.agentkit/rules/local/ui-design.md`.
- How UI is verified vs design:
  - Сверка на этапе разработки по `prototype.html`, `TECH_SPEC.md`, `PDF_ORDERS_DETAILED.md` и BPMN jpg.
  - Для e2e smoke планируется Playwright-пакет (тикет T13).

## 7) Testing & verification map
### Local DoD (must pass before asking to push)
- `make verify-local` does:
  - Проверяет целостность AgentKit + bootstrap-контракта:
    - наличие критичных файлов docs/rules/scripts;
    - отсутствие template-маркеров;
    - наличие ticket-плана в ROADMAP;
    - наличие changelog-записи в PROJECT_MAP;
    - наличие всех обязательных local rules файлов.
- Coverage target:
  - Формальный порог coverage будет включен в T13; на текущем этапе проверяется структурная и процессная целостность.
- “API e2e smoke” definition:
  - На текущем этапе smoke покрывает health/readiness + auth baseline (`401` без токена, `403` при недостаточной роли, role-gated happy-path).

### CI DoD (must pass before ticket is Done)
- `make verify-ci` does:
  - Запускает `verify-local`.
  - Дополнительно проверяет наличие `README.md` и `.env.example` как обязательных артефактов runtime-этапа.
  - Запускает `git diff --check --ignore-cr-at-eol` для строгого whitespace gate без ложных падений на CRLF/LF в mixed Windows/Linux среде.
- Security scanning policy (high level):
  - На bootstrap этапе — policy/document checks + ручная проверка отсутствия секретов в tracked файлах.
  - На implementation этапе — статический анализ + dependency/security scanning добавляются в `verify-ci`.

## 8) High-risk areas
- Auth / permissions / role mapping
  - Why risky:
    - Ошибка в claim/role mapping ломает границы доступа Applicant/OPS.
  - What to check:
    - JWT signature/issuer/audience validation, role visibility, org binding.
  - Where in the code:
    - `services/runtime/app/auth.py`, `services/runtime/app/main.py`, `frontend/index.html`, `infra/keycloak/realm-export.json`.
- Database migrations and status model
  - Why risky:
    - Неверные переходы/схема статусов ломают юридический workflow и traceability.
  - What to check:
    - migration plan + rollback, enum transitions, history integrity.
  - Where in the code:
    - future Alembic migrations, applications/certificates/post-issuance services.
- Public registry API contract
  - Why risky:
    - Внешний read-only контракт чувствителен к несовместимым изменениям.
  - What to check:
    - schema stability, published-only filter, pagination/filter compatibility.
  - Where in the code:
    - future gateway + certificates/registry endpoints.
- Security headers and sensitive logging
  - Why risky:
    - Возможны утечки персональных данных и security misconfiguration.
  - What to check:
    - redaction policy, no secrets in logs, response header baseline.
  - Where in the code:
    - future gateway middleware, service logging configuration.

## 9) File registry (only important files)
- `docker-compose.yml` — контейнерная карта MVP foundation.
  - public surface / key exports:
    - сервисы `gateway`, `applications`, `certificates`, `reference-data`, `files`, `notifications`, `frontend`;
    - инфраструктура `postgres`, `redis`, `minio`, `keycloak`.
  - invariants / assumptions:
    - каждый runtime-сервис обязан иметь доступный `/health`;
    - bootstrap выполняется без модификации внешних Docker-проектов.
  - dependencies:
    - `.env(.example)`, `services/runtime`, `frontend`, `infra/keycloak`.
  - tests:
    - `docker compose up -d --build`, проверка health URL.
- `services/runtime/app/main.py` — общий каркас FastAPI runtime для сервисов.
  - public surface / key exports:
    - `GET /`, `GET /health`, `GET /readiness`, `GET /auth/config`, `GET /auth/me`, `GET /auth/applicant-area`, `GET /auth/ops-area`.
  - invariants / assumptions:
    - readiness зависит от доступности postgres/redis/minio/keycloak.
  - dependencies:
    - FastAPI/Uvicorn, auth dependency layer, env-переменные compose.
  - tests:
    - container healthcheck + ручной HTTP probe.
- `services/runtime/app/auth.py` — JWT verification и RBAC dependency layer.
  - public surface / key exports:
    - `get_current_user`, `require_roles`, `extract_roles`.
  - invariants / assumptions:
    - проверяются signature/JWKS, `iss`, `aud`, expiry; backend остаётся source-of-truth для доступа.
  - dependencies:
    - PyJWT + Keycloak JWKS endpoint.
  - tests:
    - `services/runtime/tests/test_auth.py`.
- `infra/keycloak/realm-export.json` — baseline realm для локального OIDC/RBAC.
  - public surface / key exports:
    - realm `ektrm`, роли `Applicant` и `OPS`, demo users, audience mapper `ektrm-api`.
  - invariants / assumptions:
    - только локальная/development-конфигурация.
  - dependencies:
    - контейнер Keycloak с `--import-realm`.
  - tests:
    - загрузка realm при старте keycloak.
- `.env.example` — единый env-контракт локального запуска.
  - public surface / key exports:
    - порты сервисов и инфраструктуры, MinIO/Keycloak/DB параметры, OIDC/JWKS/CORS и feature flags.
  - invariants / assumptions:
    - не содержит production-secret значений.
  - dependencies:
    - `docker-compose.yml`, bootstrap scripts.
  - tests:
    - копирование в `.env` и успешный `docker compose up`.
- `README.md` — runbook T1/T2 для запуска, health-check и auth smoke.
  - public surface / key exports:
    - quickstart, контейнерная топология, keycloak bootstrap, verify команды.
  - invariants / assumptions:
    - инструкции синхронизированы с `docker-compose.yml` и `.env.example`.
  - dependencies:
    - scripts/bootstrap.*, verify scripts.
  - tests:
    - smoke-прогон команд из раздела «Быстрый старт».
- `.agentkit/_temp/TECH_SPEC.md` — главный доменный контракт MVP (локальный source-of-truth).
  - public surface / key exports:
    - Scope, роли, статусы, сущности, API-группы, требования к качеству.
  - invariants / assumptions:
    - Order 3/4/5 required, resume forbidden in MVP.
  - dependencies:
    - PDF analytics + BPMN jpg as secondary evidence.
  - tests:
    - Используется как чеклист для acceptance mapping.
- `.agentkit/_temp/PDF_ORDERS_DETAILED.md` — детальная аналитика PDF-ордеров.
  - public surface / key exports:
    - Подтвержденные шаги, таблицы, роли, справочники, page-by-page карта.
  - invariants / assumptions:
    - При конфликте уступает `TECH_SPEC.md`.
  - dependencies:
    - OCR/diagram interpretation.
  - tests:
    - Источник для seed словарей и QA-сценариев.
- `.agentkit/docs/ROADMAP.md` — поэтапный delivery-план и ticket breakdown.
  - public surface / key exports:
    - Milestones и T1..Tn.
  - invariants / assumptions:
    - Один тикет = один чат = завершенный цикл изменений.
  - dependencies:
    - TECH_SPEC + local rules.
  - tests:
    - Проверяется make-targets на отсутствие шаблонов и наличие тикетов.
- `.agentkit/rules/local/*.md` — проектные guardrails для архитектуры, домена, security, testing, integrations, CI, UI.
  - public surface / key exports:
    - Практические правила реализации для будущих тикетов.
  - invariants / assumptions:
    - Не конфликтуют с `TECH_SPEC`.
  - dependencies:
    - `.agentkit/rules/common/*`.
  - tests:
    - Проверяются verify-targets на наличие.
- `Makefile` — verification contract для локального и CI DoD.
  - public surface / key exports:
    - `verify-smoke`, `verify-local`, `verify-ci`.
  - invariants / assumptions:
    - Никаких placeholder/fake passes.
  - dependencies:
    - `.agentkit/scripts/verify.sh`, `.agentkit/scripts/verify.ps1`.
  - tests:
    - Запускается напрямую и через verify runners.

## 10) Runbook (minimal)
- How to run locally (bootstrap stage):
  - `cp .env.example .env` (или `Copy-Item .env.example .env`)
  - Linux/macOS: `./scripts/bootstrap.sh`
  - Windows: `pwsh -File .\\scripts\\bootstrap.ps1`
  - Проверить `http://localhost:8080/health` и `http://localhost:4200/health`
  - Проверить auth baseline на `http://localhost:4200` (login/logout + `/auth/*` вызовы)
  - Остановить: `docker compose down`
- Verification:
  - `make verify-smoke`
  - `make verify-local`
  - `make verify-ci`
  - Linux/macOS: `./.agentkit/scripts/verify.sh local`
  - Windows: `pwsh -File .agentkit/scripts/verify.ps1 local`
- Required env vars:
  - Обязательные runtime переменные уже заданы в `.env.example`:
    - сервисные порты (`GATEWAY_PORT`, `APPLICATIONS_PORT`, ...);
    - инфраструктура (`POSTGRES_*`, `REDIS_*`, `MINIO_*`, `KEYCLOAK_*`);
    - OIDC и feature flags.
- Troubleshooting:
  - Если порты заняты локально, переопределить `*_PORT`/`*_EXPOSE_PORT` в `.env`.
  - Если `verify.sh` недоступен на Windows, использовать `verify.ps1`.
  - Если падает DOC-gate, убедиться что `.agentkit/docs/PROJECT_MAP.md` изменен в том же тикете.
  - Если падает verify-local из-за template markers, очистить placeholder-текст в docs/rules.

---

## Map changelog (most recent first)
- 2026-03-05 [t2-keycloak-and-access-model-baseline] Добавлен auth baseline: Keycloak audience mapper, backend JWT/JWKS validation и RBAC endpoint-ы, frontend OIDC demo flow, env/compose auth-конфигурация, кроссплатформенный whitespace gate (`--ignore-cr-at-eol`) и документация T2.
- 2026-03-05 [t1-platform-bootstrap-and-container-topology] Добавлена контейнерная топология MVP (docker-compose), runtime-сервисный каркас с health/readiness, keycloak realm import, bootstrap-скрипты и обновленный runbook.
- 2026-03-05 [gitignore-push-2026-03-05] Обновлен `.gitignore` (env/editor/log/build артефакты) и подготовлен репозиторий к публикации изменений.
- 2026-03-05 [project-intake-2026-03-05] Полностью адаптирован PROJECT_MAP под домен e-КТРМ: архитектура, контракты, риски, verification-карта и runbook.
