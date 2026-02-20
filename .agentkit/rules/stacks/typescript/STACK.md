# Stack Pack: typescript

This stack pack contains rules for TypeScript / JavaScript projects (frontend and tooling).

## Load this stack pack when (detection)
### Primary signal: changed files in this ticket
Load `stacks/typescript/` if the ticket changes any of:
- `**/*.ts`, `**/*.tsx`
- `**/*.js`, `**/*.jsx` (if JS is part of the same toolchain)
- `package.json`
- `pnpm-lock.yaml`, `package-lock.json`, `yarn.lock`
- `tsconfig*.json`
- `eslint*`, `.eslintrc*`
- `prettier*`, `.prettierrc*`
- `vite.config.*`, `webpack.config.*`, `angular.json` (if applicable)
- Playwright test files and configs (common patterns):
  - `playwright.config.*`
  - `**/*playwright*`
  - `**/e2e/**` (frontend e2e)

### Secondary signal: repo markers (if changed-files are unclear)
If the diff is not available yet, load this pack when the repo contains:
- `package.json` AND (`tsconfig.json` OR `pnpm-lock.yaml` OR `yarn.lock`)

## Do NOT load when
- The ticket is strictly backend-only and no TS/JS/tooling files are touched.
- The ticket only edits docs with no TS/JS/tooling changes.

## Notes for the agent
- If the ticket touches UI behavior, state management, frontend tests, build tooling, or web security headers configured in frontend proxy layers, this pack is relevant.
- If both backend and frontend files are changed, load both relevant packs (e.g., python + typescript).
- Log usage in the ticket log:
  - `[RULES] loaded dirs: common, local, stacks/typescript (reason: <trigger>)`
