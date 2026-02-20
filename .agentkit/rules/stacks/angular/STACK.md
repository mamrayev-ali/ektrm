# Stack Pack: angular

This stack pack contains rules specific to Angular projects.

## Load this stack pack when (detection)

### Primary signal: changed files in this ticket
Load `stacks/angular/` if the ticket changes any of:
- Angular workspace/config:
  - `angular.json`
  - `project.json` (Nx-style)
  - `workspace.json` (older Nx)
  - `nx.json`
- Angular/TS source files commonly used in Angular apps:
  - `**/*.component.ts`
  - `**/*.component.html`
  - `**/*.component.scss`, `**/*.component.css`
  - `**/*.directive.ts`
  - `**/*.pipe.ts`
  - `**/*.service.ts`
  - `**/*.guard.ts`
  - `**/*.resolver.ts`
  - `**/*.module.ts` (if NgModules are used)
  - `**/*.routes.ts` / `**/*routing*.ts`
- Angular app markers / entrypoints:
  - `src/main.ts`
  - `src/app/**`
  - `src/environments/**`
- Angular tooling often edited in Angular tickets:
  - `tsconfig*.json`
  - `eslint*`, `.eslintrc*`
  - `prettier*`, `.prettierrc*`
  - `karma.conf.*`, `jest.config.*`
  - `playwright.config.*` (if UI E2E is in same repo)

### Secondary signal: repo markers (if changed-files are unclear)
Load this pack if the repo contains:
- `angular.json` OR `nx.json` and `src/app/`

## Do NOT load when
- Only generic TypeScript tooling changes occur and no Angular markers are touched.
- Backend-only changes with no Angular-related files.

## Notes for the agent
- This pack is for Angular-specific architecture, patterns, testing, and UI verification practices.
- If Angular and general TypeScript rules both apply, load both:
  - `stacks/typescript` + `stacks/angular`
- Always log:
  - `[RULES] loaded dirs: common, local, stacks/angular (reason: <trigger>)`
