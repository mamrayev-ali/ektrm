# Threat Model — <TICKET_ID>

> Required for high-risk changes: auth/permissions, security headers, public API contracts, payments/finance.

## Summary
- What is changing?
- Why is it needed?
- What is the security-sensitive surface?

## Assets (what we must protect)
- User identities / credentials:
- Tokens / sessions:
- Sensitive data:
- Financial/payment integrity:
- Service availability:

## Actors
- Legitimate user:
- Admin/operator:
- External attacker:
- Insider threat (if relevant):

## Entry points / attack surface
- Public endpoints:
- Internal endpoints:
- UI surfaces:
- Webhooks/integrations:
- Data inputs (files/forms/requests):

## Threats (top risks)
List the relevant threats. Examples:
- Authentication bypass
- Authorization escalation (IDOR/BOLA)
- Injection (SQL/NoSQL/command/template)
- SSRF
- XSS / CSRF
- CORS misconfiguration
- Session fixation / cookie issues
- Sensitive data leakage (logs, errors)
- Rate limiting / brute force
- Supply chain risk (dependencies)
- Misconfigured security headers

## Mitigations
Map each threat to mitigations:
- Validation/sanitization:
- AuthZ checks:
- Rate limiting:
- CSRF/CORS:
- Headers:
- Secret handling:
- Logging strategy (avoid sensitive data):
- Monitoring/alerting:

## Verification & evidence
- Local checks performed:
- SAST tools (if any):
- DAST tools (if any):
- Manual test cases:
- Negative tests:
- Playwright checks (if UI relevant):

## Residual risk
- What remains risky and why acceptable?
- Follow-up tickets:

## Notes
- ...
