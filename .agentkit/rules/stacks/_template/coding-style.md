# Coding Style — <stack-name> (template)

These rules extend:
- `.agentkit/rules/common/coding-style.md`

## Goals
- Consistent, readable code
- Predictable formatting and naming
- Minimal cleverness, maximal clarity

## Conventions (fill for this stack)
### Formatting
- Formatter tool: <name> (e.g., gofmt, prettier, black)
- Linter(s): <name>
- Import ordering: <rule/tool>
- Line length (if relevant): <N>

### Naming
- Files/folders: <rules>
- Types/classes: <rules>
- Functions/methods: <rules>
- Variables: <rules>
- Constants/enums: <rules>

### Error handling
- Preferred strategy: <rules>
- What to avoid: <rules>

### Logging
- Preferred logger: <rules>
- Redaction/sensitive data: never log secrets/PII unless explicitly approved

## Review checklist (agent + human)
- [ ] Formatting is enforced by tooling
- [ ] Naming is consistent with stack conventions
- [ ] Errors are handled consistently
- [ ] Logs contain no sensitive data
- [ ] Diff is small and readable (avoid large refactors without separate ticket)
