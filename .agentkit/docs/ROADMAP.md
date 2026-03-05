# ROADMAP — e-КТРМ MVP Phase 1

Источники: `TECH_SPEC.md` (главный), `PDF_ORDERS_DETAILED.md`, BPMN-скрины, `.agentkit/README.md`.

---

## 0) Project overview (1–2 paragraphs)
Строится локально запускаемая MVP-система e-КТРМ для сертификации продукции РК с полным рабочим контуром процессов `Ордер 3`, `Ордер 4`, `Ордер 5` (кроме `возобновления`). Решение должно быть не макетом, а рабочим foundation для production-развития: чистая архитектура, формализованные статусы, audit, версионирование сертификатов, реестр и in-app уведомления.

Целевые пользователи MVP: `Applicant` (Заявитель) и `OPS` (ОПС), плюс внешние анонимные пользователи публичного read-only реестра. Критерий успеха: система поднимается одной командой через Docker Compose, проходит end-to-end сценарии по ордерам, публикует сертификаты в реестр и поддерживает post-issuance изменения с историей версий.

## 1) Constraints & assumptions
Hard constraints:
- Источник истины по требованиям: `TECH_SPEC.md`.
- Обязательный scope: Ордер 3, Ордер 4, Ордер 5 (без возобновления).
- Только две активные роли: `Applicant`, `OPS`.
- Авторизация через локальный Keycloak (`OIDC Code + PKCE` на фронте, `JWT validation` на backend).
- Локальная инфраструктура: Docker Desktop, PostgreSQL, Redis, Celery, MinIO, Keycloak, микросервисы.
- UI на русском языке; дизайн строится вокруг `prototype.html`.
- Без внешних интеграций (ГБД ЮЛ, НУЦ, госреестры, внешние e-mail/SMS API).
- Реальная ЭЦП не реализуется, только mock-подпись.

Assumptions:
- В репозитории сначала формируется процессный и архитектурный каркас, затем по тикетам наращивается бизнес-код.
- Справочники и юридические основания для Ордер 5 сначала хранятся в «как есть» виде из аналитики.
- Расширенные роли (`Эксперт`, `Руководитель ОПС`, инспектор и т.д.) закладываются архитектурно, но не активируются в MVP.
- Публичный реестр MVP — простой listing без сложного поиска и без отдельной публичной детальной карточки.

## 2) Architecture sketch (high level)
Main components/services:
- `gateway-service`: единая входная точка, маршрутизация публичных/защищенных API.
- `auth-integration`: проверка JWT/JWKS, RBAC/claims helpers.
- `applications-service`: Ордер 3 + post-issuance заявки, статусы и переходы.
- `certificates-service`: сертификаты, версии, mock-подпись, публикация в реестр.
- `reference-data-service`: read-only справочники и lookup-реестры.
- `files-service`: загрузки, хранение в MinIO, генерация PDF.
- `notifications-service`: in-app уведомления и realtime канал.
- `workflow-events`: доменные события и фоновые операции (логически выделенный слой).

Data storage:
- PostgreSQL (доменная модель, статусы, версии, справочники, аудит).
- Redis (Celery broker/result backend, realtime-вспомогательные механики).
- MinIO (файлы заявок/протоколов/PDF).

Integrations:
- Внутренние: Keycloak, MinIO, Redis.
- Внешние интеграции в MVP отключены.

Auth approach:
- Frontend: OIDC Authorization Code + PKCE.
- Backend: JWT signature/issuer/audience/expiry validation + role/org claim mapping.

Deployment environment:
- Docker Compose, единая команда запуска и автоинициализация (миграции + seed + Keycloak import).

## 3) Milestones
- M1: Platform Foundation
  - Локальная инфраструктура, service skeletons, auth baseline, справочники и базовые миграции.
- M2: Order 3 End-to-End
  - Полный цикл первичной заявки: черновик -> submit -> review/revision -> протокол -> решение.
- M3: Certificates Lifecycle (Order 4)
  - Автогенерация сертификата, mock-подпись, публикация во внутренний/публичный реестр.
- M4: Post-Issuance (Order 5)
  - Переоформление, приостановление, прекращение, обновление статуса и версии сертификата.
- M5: Quality & Readiness
  - Audit, уведомления, тесты, demo seed, эксплуатационные документы и hardening.

## 4) Ticket plan (ordered)
Каждый тикет исполняется за один агент-чат: план -> изменения -> diff -> verify -> завершение.

### T1 — Platform Bootstrap and Container Topology
**Scope**
- Создать каркас сервисов и docker-compose топологию под все обязательные контейнеры.
- Добавить `.env.example`, bootstrap-скрипты и единый старт.

**Acceptance criteria**
- `docker compose up --build` поднимает инфраструктурные контейнеры.
- Сервисы доступны по health/readiness endpoint.
- Документация запуска и переменных окружения заполнена.

**Risk**
- medium

**Notes**
- PR required: no.

### T2 — Keycloak and Access Model Baseline
**Scope**
- Интегрировать Keycloak realm/client/roles/users import.
- Настроить token verification и RBAC для `Applicant`/`OPS`.

**Acceptance criteria**
- Логин/логаут/refresh работают.
- Backend валидирует JWT и блокирует неавторизованные действия.
- Ролевая видимость подтверждена тестами.

**Risk**
- high

**Notes**
- PR required: yes (auth/permissions high-risk area).

### T3 — Reference Data and Lookup Registries
**Scope**
- Реализовать миграции и seed для обязательных справочников.
- Добавить lookup-таблицы `ops_registry` и `accreditation_attestat`.

**Acceptance criteria**
- Справочники физически есть в БД и заполняются из seed.
- Read-only API справочников доступен фронтенду.
- Причины post-issuance хранятся как отдельные классификаторы.

**Risk**
- high

**Notes**
- PR required: yes (migrations high-risk area, migration plan + rollback mandatory).

### T4 — Order 3 Domain Model and State Engine
**Scope**
- Реализовать `cert_application` модель, статусы и переходы.
- Поддержать черновик, submit, review, revision, rejection/archive ветки.

**Acceptance criteria**
- Все переходы из `TECH_SPEC` соблюдаются backend-валидацией.
- Уникальность номера заявки enforced.
- История статусов сохраняется.

**Risk**
- medium

**Notes**
- PR required: no.

### T5 — Order 3 Applicant UI Wizard
**Scope**
- Собрать wizard UI по подтвержденным вкладкам и полям.
- Реализовать UX-действия `Сохранить черновик`, `Подписать и отправить`, `Удалить черновик`.

**Acceptance criteria**
- Форма валидирует обязательные поля на submit.
- Черновик сохраняется неполным.
- Вкладки и layout соответствуют `prototype.html`.

**Risk**
- medium

**Notes**
- PR required: no.

### T6 — OPS Review and Protocol Attachment
**Scope**
- Реализовать очередь ОПС и действия `На доработку`, `Принять`, `Отказать`, `Прикрепить протокол`.
- Поддержать типизированные file slots через `files-service` + MinIO.

**Acceptance criteria**
- Протокол испытаний загружается и связывается с заявкой.
- Отказ приводит к архивированию и уведомлению.
- Проверена role-based видимость.

**Risk**
- medium

**Notes**
- PR required: no.

### T7 — Certificate Generation and Snapshot (Order 4 Start)
**Scope**
- Автоматически формировать сущность сертификата из одобренной заявки.
- Реализовать snapshot-перенос полей из заявки в сертификат.

**Acceptance criteria**
- Сертификат создается только по `APPROVED` заявке.
- Snapshot не зависит от последующего изменения заявки.
- Есть базовая история статусов сертификата.

**Risk**
- high

**Notes**
- PR required: yes (public contract and data semantics sensitive).

### T8 — Mock Signing, Publication, and Internal/Public Registry
**Scope**
- Реализовать действие `Подписать` и публикацию сертификата.
- Поднять внутренний реестр и публичный read-only реестр.

**Acceptance criteria**
- После подписи фиксируются signer + timestamp + событие публикации.
- Сертификат отображается во внутреннем и публичном реестре.
- Состояние сертификата переходит в `ACTIVE` (или эквивалент после `PUBLISHED`).

**Risk**
- high

**Notes**
- PR required: yes (public API/registry contract).

### T9 — Post-Issuance: Suspension and Termination
**Scope**
- Реализовать форму и процесс приостановления/прекращения.
- Поддержать seeded причины и required file-основание.

**Acceptance criteria**
- Поля причин активируются по типу действия.
- Успешный процесс обновляет статус сертификата и реестр.
- Отказная ветка архивирует заявку и уведомляет заявителя.

**Risk**
- medium

**Notes**
- PR required: no.

### T10 — Post-Issuance: Reissue and Certificate Versioning
**Scope**
- Реализовать переоформление и создание новой версии сертификата.
- Поддержать связи `post_issuance_application -> source_certificate`.

**Acceptance criteria**
- Успешное переоформление создает новую `certificate_version`.
- История версий доступна API.
- Актуальная версия и статус корректно видны в реестре.

**Risk**
- high

**Notes**
- PR required: yes (data/migration and public contract sensitive).

### T11 — Notifications, Realtime, and Event Pipeline
**Scope**
- Реализовать in-app уведомления + read/unread + привязку к объектам.
- Подключить WebSocket доставку событий с fallback refresh.

**Acceptance criteria**
- События по Ордер 3 и Ордер 5 генерируют уведомления.
- Новые уведомления приходят в UI в realtime.
- Шаблоны уведомлений хранят RU/KZ версии.

**Risk**
- medium

**Notes**
- PR required: no.

### T12 — Audit, Soft-Delete, and Field-Level Tracking
**Scope**
- Реализовать audit_log и field_audit_log для критичных полей.
- Включить soft-delete для доменных сущностей.

**Acceptance criteria**
- Критичные изменения логируются with before/after.
- Операции publish/sign/archive попадают в аудит.
- Удаления выполняются только soft-delete подходом.

**Risk**
- high

**Notes**
- PR required: yes (security/compliance impact).

### T13 — Test Matrix and Seeded Demo Dataset
**Scope**
- Добавить smoke/unit/integration/e2e/RBAC/workflow тесты.
- Подготовить seed-сценарии, закрывающие обязательные demo-состояния.

**Acceptance criteria**
- `make verify-local` и `make verify-ci` включают тестовые сценарии.
- Демо-данные позволяют пройти ручной walkthrough Applicant -> OPS -> Public Registry.
- Проверены основные негативные ветки.

**Risk**
- medium

**Notes**
- PR required: no.

### T14 — Readiness, Runbooks, and Production-Alignment Docs
**Scope**
- Закрыть документацию запуска/эксплуатации/переноса конфигураций.
- Подготовить контуры для последующей интеграции с внешним Keycloak.

**Acceptance criteria**
- README и runbook покрывают запуск, конфигурацию и troubleshooting.
- Описаны ограничения MVP и out-of-scope.
- Команда может воспроизвести демонстрацию на новой машине.

**Risk**
- low

**Notes**
- PR required: no.

## 5) Backlog / parking lot
- Возобновление сертификата (добавлять отдельным тикетом только после явного подтверждения scope).
- Реальные интеграции с ГБД ЮЛ, НУЦ и внешними реестрами.
- Реальная ЭЦП и юридически значимая подпись.
- Расширенные роли (Эксперт, Руководитель ОПС, УО, инспектор, админ) как активные actors.
- Расширенный публичный поиск и отдельная публичная карточка сертификата.
- Отдельный модуль UI-редактирования справочников.
