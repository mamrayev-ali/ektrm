# Stack Pack: <stack-name>

This stack pack contains rules for <stack-name> projects.

## Load this stack pack when (detection)

### Primary signal: changed files in this ticket
Load `stacks/<stack-name>/` if the ticket changes any of:

- File extensions:
  - `<glob-1>` (e.g., `**/*.go`)
  - `<glob-2>` (e.g., `**/*.rs`)

- Tooling / config files:
  - `<marker-1>` (e.g., `go.mod`)
  - `<marker-2>` (e.g., `Cargo.toml`)
  - `<marker-3>` (e.g., `Makefile` if it is stack-specific)

- Test / e2e conventions (if applicable):
  - `<test-marker-1>` (e.g., `**/e2e/**`)
  - `<test-marker-2>` (e.g., `playwright.config.*`)

### Secondary signal: repo markers (if changed-files are unclear)
If the diff is not available yet, load this pack when the repo contains:
- `<repo-marker-1>` (e.g., `go.mod`)
- and/or `<repo-marker-2>` (e.g., `go.sum`)

## Do NOT load when
- The ticket is strictly unrelated to this stack and no stack markers are touched.
- The ticket only edits documentation (markdown) with no stack/tooling changes.

## Notes for the agent
- If the ticket changes runtime behavior, core business logic, data access, or tests in this stack, this pack is relevant.
- If multiple stacks are touched in the same ticket, load all relevant packs.
- Always log what you loaded:
  - `[RULES] loaded dirs: common, local, stacks/<stack-name> (reason: <trigger>)`

## Maintenance checklist (for authors)
When you create a new stack pack directory:
- [ ] Update `<stack-name>` in this file
- [ ] Fill in file globs + repo markers
- [ ] Ensure `coding-style.md`, `patterns.md`, `security.md`, `testing.md` exist
