# Patterns — Angular

Extends:
- `.agentkit/rules/common/patterns.md`
- `.agentkit/rules/stacks/typescript/patterns.md`

## Preferred patterns
### 1) Feature modules / feature folders
- Group by feature, not by file type.
- Each feature owns:
  - components, services, routes, state (if any), tests, styles.

### 2) Container / presentational split (when useful)
- Container: data fetching, orchestration, state glue
- Presentational: pure inputs/outputs, minimal logic

### 3) Facade / service layer for business logic
- Put business logic behind a service/facade boundary.
- UI components call the facade/service.

### 4) Routing boundaries
- Lazy-load feature routes when applicable
- Keep route guards/resolvers small; delegate logic to services

## State management (generic)
This pack is neutral:
- If the project uses NgRx / Signals / RxJS services, follow local rules in `rules/local/`.

## Anti-patterns (avoid)
- Fat components that contain business rules
- Subscriptions without teardown
- Shared “god services” used by unrelated features
- Complex logic embedded in templates

## Checklist
- [ ] Feature boundaries respected
- [ ] Business logic extracted from UI components
- [ ] No unsafe RxJS subscription patterns
- [ ] Routing decisions are explicit and testable
