# Stack packs (AgentKit)

A **stack pack** is a directory under `stacks/<stack>/` that contains extra rules relevant to a specific language/framework.

Examples:
- `stacks/go/`
- `stacks/python/`
- `stacks/angular/`

The goal is to keep the **Rules Router stable**: adding new stacks should not require changing `AGENTS.md`.

---

## Required file: `STACK.md`

Every stack pack must include a `STACK.md` file. It tells the agent **how to detect** whether the stack is relevant for the current ticket.

### Detection sources
The agent uses the following signals (prefer in this order):
1) **Changed files** in the ticket (primary)
2) **Repository marker files** (secondary)

### What to put in `STACK.md`
Use this structure:

- Stack name
- Detection rules:
  - file extensions (glob patterns)
  - marker files (names/paths)
- Notes:
  - what kinds of changes should load this pack
  - what should NOT trigger loading

---

## Recommended rule files

A stack pack should contain these files (you can extend beyond this list):

- `coding-style.md`
- `patterns.md`
- `security.md`
- `testing.md`

The agent may open all or some of these depending on the task.

---

## Template directory

Use `stacks/_template/` as a starting point when creating new stacks.

Suggested workflow:
1) Copy `_template/` to `stacks/<your-stack>/`
2) Update `STACK.md`
3) Fill in the rule files

---

## How the agent should use stack packs

- The agent should only load stack packs that are relevant to the ticket.
- The agent must record loaded stack packs in the ticket log:
  - `[RULES] loaded dirs: common, local, stacks/<stack> (reason: ...)`

---

## Naming conventions

- Directory name should be lowercase and concise: `go`, `python`, `angular`, `java`, `dotnet`, etc.
- Avoid spaces and special characters.
