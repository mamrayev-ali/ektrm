# Stack Pack: python

This stack pack contains rules for Python projects.

## Load this stack pack when (detection)
### Primary signal: changed files in this ticket
Load `stacks/python/` if the ticket changes any of:
- `**/*.py`
- `pyproject.toml`
- `uv.lock`
- `requirements*.txt`, `constraints*.txt`, `pipfile*`
- `pytest.ini`, `tox.ini`, `.coveragerc`
- `ruff.toml`, `.ruff.toml`
- `mypy.ini`
- `alembic.ini`
- `**/alembic/**`, `**/migrations/**` (if used for schema migrations)

### Secondary signal: repo markers (if changed-files are unclear)
If the diff is not available yet, load this pack when the repo contains:
- `pyproject.toml` OR `uv.lock` OR `requirements.txt`

## Do NOT load when
- The ticket is strictly frontend-only and no Python/tooling files are touched.
- The ticket only edits docs (README, markdown) with no Python changes.

## Notes for the agent
- If the ticket touches backend runtime behavior, API logic, data access, or migrations, this pack is almost always relevant.
- If both backend and frontend files are changed, load both relevant packs (e.g., python + typescript).
- Log usage in the ticket log:
  - `[RULES] loaded dirs: common, local, stacks/python (reason: <trigger>)`
