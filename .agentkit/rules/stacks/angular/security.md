# Security — Angular

Extends:
- `.agentkit/rules/common/security.md`
- `.agentkit/rules/stacks/typescript/security.md`

## Client-side security principles
- Treat all client inputs as untrusted (even internal UI fields)
- Never trust client-side checks for authorization
- Avoid leaking secrets to the client bundle

## Common Angular/Web risks to guard against
### XSS
- Prefer Angular template bindings (auto-escaping) over manual HTML injection
- Avoid bypassing sanitization (`DomSanitizer.bypassSecurityTrust*`) unless explicitly approved and justified
- Never render unsanitized HTML from user content

### CSRF
- If using cookie-based auth, ensure CSRF protections exist (usually backend responsibility)
- Avoid unsafe state-changing requests without CSRF strategy

### CORS
- CORS is backend-controlled; frontend should not assume permissive CORS
- Log and document any CORS-related requirements in local rules (project-specific)

### Token/session storage
- Avoid storing sensitive tokens in `localStorage` unless explicitly approved
- Prefer secure HTTP-only cookies (backend decision)

### Dependency supply chain
- Lockfile required
- Avoid adding new dependencies without explicit approval (policy in AGENTS.md)

## High-risk reminder
If the ticket touches security headers, auth flows, or payment-related UI:
- PR is required
- Threat model is required (`.agentkit/templates/threat-model.md`)
- Log evidence in the ticket log `[SECURITY]`

## Checklist
- [ ] No unsafe sanitization bypass
- [ ] No secrets in client bundle
- [ ] Auth/UI changes have threat model when applicable
- [ ] Dependencies changes are approved and minimal
