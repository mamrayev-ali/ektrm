# Ticket — <TICKET_ID>: <short title>

## Goal
One sentence: what outcome are we delivering?

## Scope
### In scope
- ...

### Out of scope
- ...

## Acceptance criteria
- [ ] ...
- [ ] ...

## Risk classification
- Risk: low / medium / high
- High-risk areas touched? (auth/permissions, migrations, public API contracts, security headers, payments/finance)
  - yes / no
  - If yes: PR required + templates required (threat-model / migration-plan)

## Design / Product references (if any)
- Figma:
- Notion/Docs:
- Other:

## Implementation plan
Numbered steps (small diffs):
1) ...
2) ...
3) ...

## Verification plan
### Local (required)
- [ ] `./.agentkit/scripts/verify.sh local` passes
- [ ] Coverage target met (project-defined)
- [ ] API e2e smoke passes (project-defined)

### CI (required for Done)
- [ ] `make verify-ci` passes in CI
- [ ] Full e2e UI+API passes (project-defined)
- [ ] Security scans/DAST pass (project-defined)

## Deliverables
- Files to change/add:
- New commands/scripts (if any):
- Migration plan? (yes/no)
- Threat model? (yes/no)

## Notes
- ...
