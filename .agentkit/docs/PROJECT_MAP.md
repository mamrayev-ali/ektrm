# PROJECT_MAP (template)

This file is the persistent, human-readable **map of the repository**.
It exists so that a new agent chat can quickly understand **what lives where**, **why it exists**, and **what contracts matter**.

**Strict rule:** If any repo files change in a ticket, this file must be updated in the same ticket.
This is enforced by `.agentkit/scripts/verify.sh` (DOC-gate). No exceptions.

---

## 0) TL;DR
- What this system does:
- Key user flows:
- Tech stack:
- Where to start reading the code:

## 1) Repo structure (high level)
> Describe directories as subsystems/modules. Do NOT dump the entire tree.

- `/...` — purpose, boundaries, ownership
- `/...` — purpose, boundaries, ownership

## 2) Key contracts & boundaries
- Architectural principles (layering, dependency direction, “clean architecture” expectations)
- Public interfaces (APIs, schemas, events)
- Error handling strategy
- Logging/observability conventions (where logs go, correlation IDs if any)

## 3) Domain map (important concepts)
- Core domain entities:
- Main business rules:
- Invariants (things that must always be true):

## 4) Public API surface (if applicable)
- Where the API contract lives (OpenAPI/Swagger/Proto/etc.):
- Versioning strategy:
- Critical endpoints / operations (only list critical ones):
  - ...
  - ...

## 5) Data & migrations (if applicable)
- Database(s):
- Migration approach:
- Rollback approach:
- Critical tables/collections (high level only):

## 6) Frontend / UI surface (if applicable)
- Routing approach:
- State management approach:
- Where styles/tokens live:
- How UI is verified vs design (Figma references, Playwright checks):

## 7) Testing & verification map
### Local DoD (must pass before asking to push)
- `make verify-local` does:
  - ...
- Coverage target:
- “API e2e smoke” definition:
  - ...

### CI DoD (must pass before ticket is Done)
- `make verify-ci` does:
  - ...
- Security scanning policy (high level):
  - ...

## 8) High-risk areas
> Only list areas that require extra scrutiny (auth/permissions, migrations, public contracts, headers, payments, etc.)

- Area:
  - Why risky:
  - What to check:
  - Where in the code:

## 9) File registry (only important files)
> Keep this tight. Add entries only for “high-leverage” files:
> entrypoints, public interfaces, complex business logic, high-risk code.

- `path/to/file` — purpose
  - public surface / key exports:
  - invariants / assumptions:
  - dependencies:
  - tests:

## 10) Runbook (minimal)
- How to run locally:
- Required env vars:
- Troubleshooting:

---

## Map changelog (most recent first)
- YYYY-MM-DD [TICKET] What changed in PROJECT_MAP and why
