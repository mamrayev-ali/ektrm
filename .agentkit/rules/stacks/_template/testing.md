# Testing — <stack-name> (template)

These rules extend:
- `.agentkit/rules/common/testing.md`

## Expectations
- Tests must cover critical paths and regressions
- Prefer fast tests locally; full suite in CI
- Every ticket must update `.agentkit/docs/PROJECT_MAP.md` (DOC-gate)

## Test pyramid (fill for this stack)
### Unit tests
- Framework: <name>
- What belongs here:
- What does NOT belong here:

### Integration tests
- What integrations are covered (DB, HTTP, queues, etc.):
- How to run locally:

### E2E tests
- Required for each ticket?
  - Local: smoke (fast)
  - CI: full e2e
- Tooling: <name> (e.g., Playwright, Cypress, Karate, k6)

## Coverage
- Target: <N%> (project-defined)
- How to measure: <tool/command>

## Determinism rules
- No flaky tests
- Avoid network where possible (mock/stub)
- Use fixed seeds/time when relevant

## Checklist
- [ ] Unit tests added/updated for logic changes
- [ ] Integration tests updated for system boundaries
- [ ] E2E smoke is defined for local (if applicable)
- [ ] Full E2E runs in CI
- [ ] Coverage target respected
