# Agent Ticket Log — <TICKET_ID>

> Location: logs/agent/<ticket>.md  
> This log must be **human-auditable**. Use tags consistently.

## Meta
- Ticket: <TICKET_ID>
- Branch: <branch-name>
- Date (local): <YYYY-MM-DD>
- Risk: low / medium / high
- PR required: yes / no
- Related links: (Jira/Notion/Docs/Figma/etc.)

## [RULES]
- loaded dirs:
  - common
  - local
  - stacks/<name> (if any)
- reason:
  - ...

## [CONTEXT]
- What is being changed and why?
- Constraints / assumptions:
- Out of scope:

## [PLAN]
Numbered plan (small steps). Include:
- files likely touched
- verification steps
- rollback considerations (if relevant)

## [ACT]
Chronological actions. Keep each entry small and explicit:
- what you changed
- where (files)
- why

## [MCP]
Record every MCP usage:
- [MCP:filesystem] ...
- [MCP:figma] ...
- [MCP:notion] ...
- [MCP:docs] ...
- [MCP:playwright] ...

## [DIFF]
Summarize meaningful diffs:
- Key changes:
- Files changed:
- Notes:

(Optionally paste small critical diff snippets or link to git diff view.)

## [TEST]
### Local verification (required before push request)
- Command: `./.agentkit/scripts/verify.sh local`
- Result: PASS / FAIL
- Notes:

### CI verification (required before Done)
- Trigger: push/PR per policy
- Result: PASS / FAIL
- Notes / links:

## [SECURITY]
- Any security impact?
- If high-risk area touched (auth/migrations/public API/headers/payments):
  - threat-model file created/updated: yes/no
  - migration plan created/updated: yes/no
  - extra checks performed:

## [DOC]
**PROJECT_MAP is mandatory (strict).**
- Updated `.agentkit/docs/PROJECT_MAP.md` sections:
  - ...
- Map changelog entry added: yes/no

## [DONE]
- Summary of what changed:
- How to test manually:
- Follow-ups / TODOs:
- Known limitations:
