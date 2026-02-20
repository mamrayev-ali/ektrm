# Security — <stack-name> (template)

These rules extend:
- `.agentkit/rules/common/security.md`

## Core principles
- Assume untrusted input everywhere (requests, files, UI inputs, integrations)
- Least privilege (authz checks close to business decisions)
- Secure defaults (deny by default; explicit allow-lists)

## Stack-specific security hotspots (fill)
### Input validation & injection
- Primary injection risks for this stack:
  - <risk 1> (e.g., SQL injection, template injection, command injection)
  - <risk 2>
- Required mitigations:
  - Parameterized queries / escaping rules:
  - Validation libraries:
  - Reject unknown fields / strict schemas:

### Auth / session / permissions
- Where auth checks live:
- Rules for permission checks:
- Common mistakes to avoid (IDOR/BOLA, missing tenant checks):

### Web security (if applicable)
- CORS rules:
- CSRF rules:
- Security headers handling:
- Cookies/session flags:

### Supply chain
- Dependency policy:
- Lockfiles:
- Update approach:

## High-risk rule
If the ticket touches auth/permissions, public API contracts, security headers, or payments:
- PR is mandatory
- Threat model is mandatory (`.agentkit/templates/threat-model.md`)
- Log evidence in ticket log `[SECURITY]`

## Checklist
- [ ] No secrets written to repo
- [ ] Inputs validated; injection mitigations applied
- [ ] Authz checks included where needed
- [ ] Sensitive data not logged
- [ ] High-risk changes include threat model + PR
