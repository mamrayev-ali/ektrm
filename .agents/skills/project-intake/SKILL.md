---
name: project-intake
description: Discovery to roadmap workflow for AgentKit
---

# SKILL: project-intake (Discovery → ROADMAP)

## Goal
Convert a messy, incomplete project idea into a **clear ROADMAP**:
- milestones
- ordered tickets `T1..Tn`
- risks and assumptions
- verification expectations (high level)

Output is written to:
- `.agentkit/docs/ROADMAP.md`

## When to use
Use this skill when:
- starting a new project or major feature
- requirements are incomplete and need clarification
- you need a structured plan before implementation

## Inputs
Ask the user for (as needed):
- product goal & users
- constraints (security/compliance/timeline)
- key flows
- integrations
- existing repo state (if any)
- acceptance criteria
- known risks / high-risk areas

If Notion/Docs are available, request links and read them via MCP.

## Process (steps)
1) **Interview**
   - ask clarifying questions until goals and constraints are concrete
   - capture assumptions explicitly

2) **Synthesize**
   - define milestones
   - define a ticket list with clear scopes
   - mark high-risk tickets

3) **Write ROADMAP**
   - update `.agentkit/docs/ROADMAP.md` using the repository template
   - keep it readable and action-oriented
   - avoid implementation details that belong in ticket execution

4) **Log**
   - If this is done in a ticket context, record in the ticket log:
     - `[DOC] Updated ROADMAP.md`
     - `[MCP:*]` usage if any

## Output format rules
- Tickets must be ordered and scoped for “one agent chat per ticket”
- Each ticket must include:
  - scope
  - acceptance criteria
  - risk (low/medium/high)
  - notes (optional)

## Common pitfalls
- Over-scoping tickets (too big)
- Vague acceptance criteria
- Missing risk tagging for high-risk areas
- Planning without clarifying constraints
