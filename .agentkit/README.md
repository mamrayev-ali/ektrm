# AgentKit (Core) — руководство для человека

Этот репозиторий использует **AgentKit** — каркас процесса работы с AI-агентом (Codex), где:
- всегда виден **git diff**,
- всегда ведётся **читаемый лог** действий агента,
- действует **строгий DOC-gate**: `PROJECT_MAP.md` обновляется **в каждом тикете**,
- проверки запускаются через **единый контракт** (`Makefile`), без “угадываний”.

---

## 0) Что где лежит

- **Процесс/правила/шаблоны/скрипты**: `.agentkit/`
- **Skills для Codex (авто-обнаружение)**: `.agents/skills/`
- **Конфиг Codex + MCP**: `.codex/config.toml`
- **Логи тикетов** (локально, gitignored): `logs/agent/`

---

## 1) Быстрый старт (типовой цикл)

### A) Discovery → ROADMAP (один чат)
1) Запусти агента и попроси выполнить skill **project-intake**
2) Результат: обновлённый `.agentkit/docs/ROADMAP.md`

### B) Выполнение тикета (один тикет = один чат)
1) **Разработчик** создаёт короткоживущую ветку (trunk-based)
2) Ты говоришь агенту: “делай T1” (или конкретную задачу)
3) Агент:
   - делает план
   - меняет код маленькими шагами
   - показывает diff
   - ведёт лог `logs/agent/<ticket>.md`
   - обновляет `.agentkit/docs/PROJECT_MAP.md`
   - запускает `./.agentkit/scripts/verify.sh local`
4) После push/PR (по политике) — CI должен пройти `make verify-ci`

---

## 2) Branching (trunk-based) — ветку создаёт разработчик

Шаблон:
- с Jira: `ticket/<JIRA>-<short-title>`
- без Jira: `ticket/<short-title>`

Команды:
```
git switch main
git pull --ff-only
git switch -c ticket/<short-title>
```

PR **не обязателен** по умолчанию, но для high-risk изменений PR **обязателен** (см. `AGENTS.md`).

---

## 3) Конфиг Codex и обязательные MCP

Все MCP настраиваются **только** в `.codex/config.toml`.

Обязательные MCP для этого каркаса:

* filesystem
* figma
* notion
* docs (OpenAI Developer Docs MCP)
* playwright

> Важно: не хранить секреты/токены в репозитории. OAuth-авторизации (Figma/Notion) выполняются стандартным образом через клиент.

---

## 4) Логи тикетов (обязательны)

* Каждый тикет ведётся в `logs/agent/<ticket>.md`
* Формат: `.agentkit/templates/agent-log.md`

Лог должен содержать:

  * `[PLAN]` план
  * `[ACT]` действия
  * `[DIFF]` краткое описание изменений + ссылка/вставка ключевого diff
  * `[TEST]` результаты локальных проверок
  * `[MCP:*]` использование MCP (filesystem/figma/notion/docs/playwright)
  * `[DOC]` что обновлено в `PROJECT_MAP.md`
  * `[DONE]` итог + как проверить руками

---

## 5) PROJECT_MAP — “память проекта” (строго всегда)

`.agentkit/docs/PROJECT_MAP.md` — единый документ, который агент:

* читает в начале тикета,
* обновляет в конце тикета,
* поддерживает актуальным на протяжении жизни репозитория.

**Правило:** если в тикете меняется любой файл репозитория — `PROJECT_MAP.md` должен быть обновлён **в этом же тикете**.
Исключений нет. Это жёстко проверяется `verify.sh` (DOC-gate).

---

## 6) Проверки: контракт Makefile + verify.sh

### Контракт (в корне репо)

`Makefile` объявляет цели:

* `make verify-local` — локальный DoD
* `make verify-smoke` — быстрые проверки (опционально)
* `make verify-ci` — CI DoD

### Как запускаем на практике

Агент и человек запускают **не make напрямую**, а:

* `./.agentkit/scripts/verify.sh local` → DOC-gate + `make verify-local`
* `./.agentkit/scripts/verify.sh ci` → DOC-gate + `make verify-ci`

### Почему так

* `verify.sh` гарантирует DOC-gate (PROJECT_MAP всегда обновлён)
* Makefile даёт 1 стабильную команду для CI и локального прогона
* Каркас не навязывает структуру проекта: конкретные команды реализуются на этапе “project adaptation”

---

## 7) Repo hygiene (обязательные ignore правила)

Добавь в `.gitignore` (минимум):

```gitignore
logs/agent/
```

Рекомендуется (обычно нужно):

```gitignore
# Playwright artifacts
playwright-report/
test-results/
blob-report/

# Python test/coverage artifacts
.coverage
coverage.xml
htmlcov/
.pytest_cache/

# Node artifacts
node_modules/

# Common caches
__pycache__/
.venv/
```

---

## 8) Правила: common / local / stacks

Правила лежат в `.agentkit/rules/`:

* `common/` — общие правила (будут вендориться)
* `local/` — правила конкретного проекта (ручные)
* `stacks/<stack>/` — пакеты правил по языку/фреймворку (Go/Python/Angular/...)

Rules Router устроен так, что агент:

* всегда читает `common/` и `local/`
* стековые правила подключает **только если релевантно**, определяя это по **изменяемым файлам** тикета
* фиксирует в логе: `[RULES] loaded dirs: ...`

Подробности: см. `.agentkit/rules/README.md` и `.agentkit/rules/stacks/README.md`.

---

## 9) Как добавить новый стек (пример: Go)

Коротко:

1. Скопировать шаблон: `.agentkit/rules/stacks/_template` → `.agentkit/rules/stacks/go`
2. Настроить детектор в `STACK.md` (маркеры `go.mod`, расширения `*.go`)
3. Заполнить `coding-style.md`, `patterns.md`, `security.md`, `testing.md`

Rules Router не меняется — он сам подхватит новый стек, когда увидит соответствующие изменяемые файлы.

---

## 10) Обновление вендор-правил и лицензий

Если мы вендорим правила из внешнего репозитория, обновление должно проходить через:

* `./.agentkit/scripts/vendor_rules.sh`

Этот скрипт обновляет:

* `.agentkit/rules/NOTICE`
* файлы в `.agentkit/rules/UPSTREAM_LICENSES/`

Не удаляй notice/license файлы.
