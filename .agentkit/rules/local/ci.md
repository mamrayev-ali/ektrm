# CI and Verification Rules (e-КТРМ)

## Verification entrypoints
- Локально:
  - `./.agentkit/scripts/verify.sh local` (bash),
  - `pwsh -File .agentkit/scripts/verify.ps1 local` (Windows).
- CI:
  - `./.agentkit/scripts/verify.sh ci` или эквивалент через `make verify-ci`.

## Mandatory gates
- DOC-gate:
  - при изменении любых файлов в репозитории должен обновляться `.agentkit/docs/PROJECT_MAP.md`.
- DIFF-gate:
  - meaningful diff обязателен до этапа финальной верификации.
- LOG-gate:
  - `logs/agent/<ticket>.md` должен содержать PLAN/ACT/DIFF/TEST/DOC/DONE.

## PR policy
- PR обязателен для high-risk зон:
  - auth/permissions;
  - DB migrations;
  - public API contract changes;
  - security middleware/headers;
  - payments/finance logic.
- Для non-high-risk тикетов допускается прямой merge по внутренней политике команды.

## Ticket execution policy
- Один тикет = один агент-чат end-to-end.
- Изменения делаются малыми шагами с постоянным обновлением лога.
- Перед запросом на push обязательно PASS локальной проверки.
- Тикет считается Done только после PASS CI (или явной policy-оговорки).

## Failure policy
- Если требуемые инструменты отсутствуют (`make`, `python`, `uv`, `pnpm` и т.д.):
  - запрещено добавлять fake-раннеры;
  - нужно явно зафиксировать причину и запросить установку зависимостей.
