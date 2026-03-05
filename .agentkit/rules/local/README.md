# Local Rules — e-КТРМ

Этот каталог содержит только **локальные правила проекта e-КТРМ**.
Главный источник требований: `.agentkit/_temp/TECH_SPEC.md`.

## Source precedence
1. `.agentkit/_temp/TECH_SPEC.md`
2. `.agentkit/_temp/PDF_ORDERS_DETAILED.md`
3. BPMN-изображения из `.agentkit/_temp/order_*.jpg`
4. Общие инженерные правила из `.agentkit/rules/common/*`

Если есть конфликт между локальными правилами и `TECH_SPEC.md`, приоритет у `TECH_SPEC.md`.

## File index
- `architecture.md` — границы сервисов, dependency direction, ownership данных, event-model.
- `domain.md` — роли, статусы, переходы и инварианты по Ордер 3/4/5.
- `security.md` — Keycloak/JWT/RBAC правила, redaction и политика секретов.
- `testing.md` — обязательная матрица тестов и минимальный acceptance набор.
- `ci.md` — verification/DoD контракт и policy gates по тикетам.
- `ui-design.md` — UI/UX правила и ограничения вкладок/состояний.
- `integrations.md` — допустимые и запрещенные интеграции MVP, конфигурационный контракт.

## What must not be placed here
- Общие coding-style правила (для этого есть `common/`).
- Специфичные правила языка/фреймворка (для этого `stacks/<stack>/`).
- Любые секреты (ключи, токены, пароли, certs).

## Agent usage contract
- Agent всегда загружает `common + local`.
- Agent обязан писать в лог тикета:
  - `[RULES] loaded dirs: common, local, ...`
- При любых изменениях в репозитории Agent обновляет `.agentkit/docs/PROJECT_MAP.md` в том же тикете.
