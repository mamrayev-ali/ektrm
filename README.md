# e-КТРМ — MVP Platform Bootstrap (T1) + Auth Baseline (T2)

Репозиторий содержит AgentKit-процесс и стартовую контейнерную топологию MVP Phase 1 для e-КТРМ.

Реализовано в тикетах `T1` и `T2`:
- docker-compose с обязательными контейнерами платформы;
- bootstrap-скрипты запуска;
- минимальные runtime-сервисы с `/health` и `/readiness`;
- baseline frontend-страница с OIDC login/logout/refresh и вызовами защищенных API;
- backend JWT verification через Keycloak JWKS и role-gated endpoint-ы `Applicant` / `OPS`.

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

- Реальная бизнес-логика ордеров 3/4/5 не реализована (каркасный runtime).
- Внешние интеграции (ГБД ЮЛ, НУЦ, госреестры) отключены.
- Реальная ЭЦП не реализуется.
