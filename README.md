# e-КТРМ — AgentKit Adaptation Repository

Репозиторий содержит процессный каркас и документы для реализации MVP Phase 1 сервиса сертификации продукции РК.

Текущий этап: **project intake + адаптация AgentKit**.
Бизнес-код микросервисов будет добавляться по тикетам из `.agentkit/docs/ROADMAP.md`.

## Источники требований
1. `.agentkit/_temp/TECH_SPEC.md` — главный источник истины.
2. `.agentkit/_temp/PDF_ORDERS_DETAILED.md` — детальная аналитика ордеров.
3. BPMN изображения в `.agentkit/_temp/order_*.jpg`.

## Ключевые документы
- `.agentkit/docs/ROADMAP.md` — milestones и ticket plan.
- `.agentkit/docs/PROJECT_MAP.md` — карта архитектуры и контрактов.
- `.agentkit/rules/local/*.md` — локальные проектные правила.
- `AGENTS.md` — обязательный процесс работы агента.

## Верификация
- Linux/macOS (bash):
  - `./.agentkit/scripts/verify.sh smoke`
  - `./.agentkit/scripts/verify.sh local`
  - `./.agentkit/scripts/verify.sh ci`
- Windows (PowerShell):
  - `pwsh -File .agentkit/scripts/verify.ps1 detect`
  - `pwsh -File .agentkit/scripts/verify.ps1 smoke`
  - `pwsh -File .agentkit/scripts/verify.ps1 local`

## Scope MVP (коротко)
- Ордер 3: первичная заявка и решение.
- Ордер 4: сертификат, mock-подпись, публикация в реестр.
- Ордер 5: переоформление, приостановление, прекращение (без возобновления).
- Роли: `Applicant`, `OPS`.

## Ограничения этапа
- Внешние интеграции (ГБД ЮЛ, НУЦ, госреестры) отключены.
- Реальная ЭЦП не реализуется.
- UI CRUD для справочников не реализуется.
