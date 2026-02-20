# Migration Plan — <TICKET_ID>

> Required for any DB schema change. Must include a rollback plan.

## Summary
- What is changing in the schema?
- Why is it needed?
- Expected impact (tables/columns/indexes/constraints/data shape):

## Preconditions
- Current schema version / migration head:
- Environment assumptions:
- Backups / safety prerequisites:

## Forward migration steps
1) Create migration:
2) Apply migration in a safe environment:
3) Validate:
   - data integrity checks
   - performance considerations
   - application compatibility

## Data migration (if applicable)
- Is there data backfill/transform?
- Idempotency strategy:
- Batch size / locking strategy:
- Monitoring during backfill:

## Rollback plan (mandatory)
- How to revert schema changes:
- How to revert/handle data changes:
- Conditions that trigger rollback:
- Expected downtime / risk during rollback:

## Compatibility
- Will old app version work with new schema?
- Will new app version work with old schema?
- Deployment order (if relevant):

## Verification
### Local
- Steps to run migration locally:
- Steps to run app against migrated DB:

### CI / Staging
- Automated checks:
- Manual checks:

## Risks & mitigations
- Risks:
- Mitigations:

## Notes
- ...
