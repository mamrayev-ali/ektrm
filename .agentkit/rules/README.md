# Rules (AgentKit)

This directory defines the **rule system** used by the agent. Rules are intentionally organized so the **Rules Router never needs to change**.

## Structure

- `common/`  
  General rules that apply to any repo and any stack (coding style, git workflow, security, testing, patterns, etc.).  
  These rules are typically **vendored** from upstream sources.

- `local/`  
  Project-specific rules (handwritten).  
  Use this for things that are unique to a specific repo or organization practices.

- `stacks/<stack>/`  
  Optional stack packs by language/framework (e.g., `go`, `python`, `angular`, `java`, ...).  
  The agent loads a stack pack only when relevant **based on changed files** in the ticket.

- `UPSTREAM_LICENSES/` and `NOTICE`  
  Vendor metadata. When we copy rules from upstream repositories, we keep license texts and a small notice.

## How the agent loads rules (Rules Router)

The Rules Router logic is defined in `AGENTS.md`.

**Always load:**
- `common/`
- `local/`

**Optionally load stack packs:**
- The agent decides which `stacks/<stack>/` directories to load by inspecting the **changed files** and any relevant marker files in the repo.

The agent must log loaded rule directories in the ticket log:
- `[RULES] loaded dirs: common, local, stacks/<name> (reason: ...)`

## Vendoring common rules from upstream

When we vendor rule content, it goes into:
- `common/` and/or `stacks/<stack>/`

And we update:
- `NOTICE`
- `UPSTREAM_LICENSES/*`

Use:
- `./.agentkit/scripts/vendor_rules.sh`

Do not remove vendor notices or licenses.

## Adding a new stack pack (example: Go)

### 1) Create a stack directory
Copy the template:

- from: `stacks/_template/`
- to: `stacks/go/`

### 2) Configure detection in `STACK.md`
`STACK.md` describes how the agent should recognize when this stack is relevant.
Typical markers:
- file extensions (e.g., `*.go`)
- marker files (e.g., `go.mod`)

### 3) Fill out the stack rules
Recommended core files to include (you may add more):
- `coding-style.md`
- `patterns.md`
- `security.md`
- `testing.md`

### 4) Done
No router changes are needed. The agent will load `stacks/go/` when the ticket touches Go-related files.

## Writing rules (format)
Rules are plain Markdown files. Keep them:
- concise and actionable
- consistent with the rest of the rule set
- written as instructions the agent can follow
