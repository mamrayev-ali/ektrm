```md
# AGENTS.md (AgentKit Core)

## Purpose
This repository uses **AgentKit**: a repeatable workflow for working with an AI agent (Codex) with **auditable steps**, **mandatory diffs**, **mandatory human-readable logs**, and **strict safety gates**.

- **Process framework**: `.agentkit/` (rules, docs, templates, scripts)
- **Codex skills**: `.agents/skills/` (auto-discovered by Codex)

Do not mix these directories.

---

## Non-negotiables (always)
1) **Show code diff** after every meaningful change (or at least before any verification/push request).  
2) **Maintain a readable ticket log** in `logs/agent/<ticket>.md` using `.agentkit/templates/agent-log.md`.  
3) **Update `.agentkit/docs/PROJECT_MAP.md` on every ticket** that changes anything in the repo (DOC-gate is strict; no exceptions).  
4) **Follow the verification workflow**: local checks must pass before asking for permission to push; CI checks must pass before calling a ticket “Done”.  
5) **Use MCP intentionally and log it** (see “MCP usage & logging”).

---

## Safety / Approval gates (ask first)
The agent MUST ask for explicit permission (and explain why) before doing any of the following:

### A) Outside-repo access
- Reading/writing files **outside the repository**
- Using network access / downloading new dependencies / fetching remote resources (except normal MCP read usage when already configured)
- Running tools that exfiltrate data

### B) High-risk changes (PR required)
The following areas are **high-risk**. A **PR is required** (even if PRs are optional otherwise), and the agent must include extra notes in the ticket log:
- Auth / permissions / roles / access control
- Database migrations (requires **migration plan + rollback**)
- Public API contracts (breaking changes, versioning, OpenAPI, etc.)
- Security headers and security-related middleware
- Payments / finance-related logic

### C) Protected infrastructure
- CI/CD config changes
- Docker / k8s manifests
- Authn/Authz infrastructure
- Secret/key generation or writing secrets to files (forbidden; see below)

### D) Forbidden without explicit approval + separate ticket
- “Large refactors” (wide-ranging rename/move/rewrite). Must be split into a dedicated ticket.

---

## Absolute prohibitions
- **Never** write secrets/keys/tokens into the repo (any file).  
- **Never** auto-generate secrets/keys and store them in files.  
- **Never** run DB migrations without a migration plan + rollback (see templates).  
- **Never** change CI/CD/Docker/k8s manifests without explicit approval.  
- **Never** change auth/permissions without adding a threat-model note in the ticket log.

---

## Mandatory workflow (how to run a ticket)
A “ticket” = one scoped unit of work, typically executed in one agent chat until Done.

### Step 0 — Branch (developer-owned)
Developer creates a short-lived branch (trunk-based):
- `ticket/<jira-id>-<short-title>` if Jira-id exists, else `ticket/<short-title>`

### Step 1 — Load context (always)
At the start of a ticket, the agent must:
1) Open and read:
   - `.agentkit/docs/ROADMAP.md` (if working from roadmap)
   - `.agentkit/docs/PROJECT_MAP.md`
   - `.agentkit/rules/common/`
   - `.agentkit/rules/local/`
2) Create or open the ticket log:
   - `logs/agent/<ticket>.md` (from `.agentkit/templates/agent-log.md`)

### Step 2 — Plan (always)
Before changing code, produce a detailed plan:
- broken into small steps
- includes files likely touched
- includes verification steps and expected commands
- includes risk classification (low/medium/high)
- includes whether a PR is required

### Step 3 — Execute in small diffs
Work incrementally. After each meaningful step:
- update the ticket log
- show a diff
- state what changed and why

### Step 4 — Verification gates
- **Local verification**: run `.agentkit/scripts/verify.sh local` and ensure it passes.
- **CI verification**: ensure CI pipeline passes the `verify-ci` contract before marking Done.

### Step 5 — Closeout
A ticket is “Done” only when:
- local verify passed
- CI verify passed (or is not applicable by policy)
- PROJECT_MAP updated
- ticket log includes final summary + how to test + risks + follow-ups

---

## Rules Router (directory-based, stack chosen by changed files)
Rules are organized in stable directories:
- `.agentkit/rules/common/` (always)
- `.agentkit/rules/local/` (always)
- `.agentkit/rules/stacks/<stack>/` (optional stacks)

The agent must decide which stack rules to load based on **changed files** in the ticket:
- If changes include language/framework markers or file extensions for a stack, load that stack directory.
- If both backend and frontend markers are present, load both relevant stacks.

**How to decide (general):**
1) Inspect current diff or planned touched files.
2) If unsure, open the repo tree and identify relevant config files.
3) Load stack rules only when relevant.

**Always log what you loaded:**
- In `logs/agent/<ticket>.md`, record:
  - `[RULES] loaded dirs: common, local, stacks/<name> (reason: ...)`

---

## MCP usage & logging
MCP servers are configured in `.codex/config.toml`. The agent must:
- Use MCP tools when they provide authoritative context (Figma, Notion, Docs, Playwright, filesystem).
- Log every MCP usage in the ticket log with a clear tag:
  - `[MCP:filesystem] ...`
  - `[MCP:figma] ...`
  - `[MCP:notion] ...`
  - `[MCP:docs] ...`
  - `[MCP:playwright] ...`

---

## Documentation discipline: PROJECT_MAP is mandatory (strict)
`.agentkit/docs/PROJECT_MAP.md` is the persistent “memory” of the repo.

**Rule:** If any repo files change in a ticket, the agent must update PROJECT_MAP in the same ticket.  
There is **no skip mode**. This is enforced by the `verify.sh` DOC-gate.

The ticket log must include:
- `[DOC] Updated PROJECT_MAP.md sections: ...`

---

## Verification contract (Makefile)
Verification is defined by Makefile targets. The agent must not guess commands.

- Local DoD: `make verify-local`
- Smoke checks (optional): `make verify-smoke`
- CI DoD: `make verify-ci`

The agent runs verification through:
- `.agentkit/scripts/verify.sh local` → invokes `make verify-local` (and DOC-gate)
- `.agentkit/scripts/verify.sh ci` → invokes `make verify-ci` (and DOC-gate)

---

## Repo hygiene
- `logs/agent/` is gitignored (local audit logs).
- Test artifacts (Playwright reports, test-results, etc.) should be gitignored unless explicitly required and approved.

---

## Vendoring upstream rules
Some rule content may be vendored into `.agentkit/rules/common/` and `.agentkit/rules/stacks/*`.

When vendor rules are updated, `.agentkit/rules/NOTICE` and upstream licenses must be updated via:
- `.agentkit/scripts/vendor_rules.sh`

Do not remove license notices.
```
