# Coding Style — Angular

Extends:
- `.agentkit/rules/common/coding-style.md`
- `.agentkit/rules/stacks/typescript/coding-style.md`

## Goals
- Predictable Angular structure
- Consistent naming for components/services/modules
- Readable templates and styles
- Small diffs and low coupling

## Naming conventions (Angular)
- Components:
  - `*.component.ts`, selector `app-<name>` (or org prefix)
  - Class name: `<Name>Component`
- Services:
  - `*.service.ts`
  - Class name: `<Name>Service`
- Guards/resolvers:
  - `*.guard.ts`, `*.resolver.ts`
- Pipes:
  - `*.pipe.ts`
- Directives:
  - `*.directive.ts`
- Routes:
  - Prefer explicit `routes.ts` naming, avoid “magic” exports

## Structure rules
- Keep components “thin”: UI composition + orchestration only
- Put business logic in services/facades/use-cases (project-dependent)
- Avoid importing across feature boundaries without explicit reason
- Prefer feature folders over “mega shared” unless truly shared

## Template style
- Keep templates readable (avoid deeply nested structural directives)
- Prefer `async` pipe over manual subscriptions in components
- Avoid calling heavy functions in templates

## RxJS / async
- Prefer `async` pipe for observable data
- Use `takeUntilDestroyed` or equivalent lifecycle-safe patterns
- Avoid nested subscriptions

## Checklist
- [ ] Angular naming conventions followed
- [ ] Component stays thin (logic extracted)
- [ ] Subscriptions are lifecycle-safe
- [ ] Templates avoid heavy computation
- [ ] Diff is small and auditable
