# Local rules (project-specific)

This directory is reserved for **project-specific rules** that should NOT be mixed with:
- `.agentkit/rules/common/` (general rules for any repo)
- `.agentkit/rules/stacks/*` (language/framework-specific rule packs)

## What belongs here
Use `local/` for rules that are unique to **this repository** or organization context, for example:
- architectural decisions specific to this repo (module boundaries, layering, naming conventions)
- domain-specific constraints and invariants
- required documentation locations (PRD links, runbooks, ADRs)
- CI/CD conventions specific to this repo (ONLY what is safe to describe; do not store secrets)
- required security headers/policies used in this repo
- code ownership conventions
- release/versioning conventions
- environments and deployment expectations (high level)

## What does NOT belong here
Do not put these here:
- general coding style rules (use `common/`)
- language/framework rules (use `stacks/<stack>/`)
- secrets, keys, tokens, credentials (never store in repo)

## Recommended files
You can structure local rules as multiple focused files, for example:
- `architecture.md`
- `domain.md`
- `security.md`
- `testing.md`
- `ci.md`
- `ui-design.md` (if you have specific design system constraints)
- `integrations.md`

Keep files small and specific.

## How the agent should use local rules
- The agent MUST always load `local/` (even if it is empty).
- The agent must mention in the ticket log:
  - `[RULES] loaded dirs: common, local, ...`

## Template: minimal `architecture.md` (copy/paste)
# Architecture (local)

## Modules / boundaries
- ...

## Dependency direction
- ...

## Data flow
- ...

## High-risk areas
- ...

## Naming conventions
- ...

## Template: minimal security.md (copy/paste)
# Security (local)

## Auth / permissions model
- ...

## Security headers
- ...

## Sensitive data handling
- ...

## Allowed origins / CORS
- ...

## Logging (redaction)
- ...
