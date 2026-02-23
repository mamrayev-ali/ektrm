---
name: ticket-planning
description: Plan and de-risk a ticket with small execution steps, verification, and DoD gates
---

# SKILL: ticket-planning (Tn → execution plan + DoD)

## Goal
Take a ticket (e.g., `T3`) and turn it into:
- a detailed execution plan (small diffs)
- commands to run
- explicit DoD (local + CI)
- required templates (threat-model / migration plan) based on risk

This skill prepares the agent to implement the ticket safely and audibly.

## When to use
Use at the start of every ticket.

## Inputs
- Ticket ID (e.g., `T3`)
- `.agentkit/docs/ROADMAP.md`
- `.agentkit/docs/PROJECT_MAP.md`
- Relevant rule directories:
  - `.agentkit/rules/common/`
  - `.agentkit/rules/local/`
  - stack packs if relevant (by changed files heuristic)

## Process
1) **Load context**
   - open ROADMAP and locate the ticket
   - open PROJECT_MAP
   - open rules: common + local (+ stack packs if clearly relevant)

2) **Classify risk**
   - Determine risk: low/medium/high
   - If high-risk areas are touched:
     - require PR
     - require templates:
       - `.agentkit/templates/threat-model.md` for auth/permissions, headers, public API, payments
       - `.agentkit/templates/migration-plan.md` for migrations

3) **Generate plan**
   - break down into small steps
   - list likely files
   - list commands to run
   - include test plan and security checks

4) **Create ticket artifacts**
   - create a ticket doc (optional) using `.agentkit/templates/ticket.md`
   - create/open ticket log `logs/agent/<ticket>.md` using `.agentkit/templates/agent-log.md`

5) **Enforce DOC discipline**
   - ensure plan includes updating `.agentkit/docs/PROJECT_MAP.md`
   - remind that `verify.sh` will fail without it (DOC-gate)

## Output expectations
The result should be ready for execution:
- small-step plan
- clear acceptance criteria confirmation
- explicit verification commands:
  - `./.agentkit/scripts/verify.sh local`
  - CI will run `make verify-ci`

## Common pitfalls
- Planning without reading PROJECT_MAP
- Not identifying high-risk areas early
- Forgetting PROJECT_MAP updates
- Unclear DoD
