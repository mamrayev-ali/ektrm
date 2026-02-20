# Testing — Angular

Extends:
- `.agentkit/rules/common/testing.md`
- `.agentkit/rules/stacks/typescript/testing.md`

## Expectations
- Unit tests for components/services with meaningful logic
- Integration tests for feature flows (where feasible)
- UI E2E is required per ticket in CI (policy-driven); locally run smoke subset

## Unit tests
- Prefer testing behavior over implementation details
- Mock boundaries: HTTP services, facades, storage
- Keep tests deterministic (no real timeouts/network)

## Component tests
- Test inputs/outputs, rendering conditions, event handling
- Avoid over-mocking Angular internals; mock your services/facades instead

## E2E (Playwright recommended)
- Local: smoke subset that validates critical path quickly
- CI: full suite (UI + API where applicable)
- Treat E2E as the “acceptance criteria verifier”

## Accessibility (recommended)
- Basic checks for keyboard navigation and ARIA where relevant

## Checklist
- [ ] Unit tests updated/added for logic changes
- [ ] Component tests cover key UI behavior
- [ ] Playwright smoke is runnable locally (project-defined)
- [ ] Full UI E2E runs in CI
