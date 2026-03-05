# Makefile (AgentKit adaptation contract for e-КТРМ)
#
# Реальные проверки для текущего этапа репозитория:
# - process/docs/rules consistency
# - отсутствие template-заглушек
# - наличие обязательных артефактов
#
# По мере появления runtime-кода эти цели расширяются lint/test/e2e командами.

.PHONY: help detect verify-smoke verify-local verify-ci \
	check-required-files check-local-rules check-no-template-markers \
	check-roadmap-tickets check-project-map-changelog check-runtime-artifacts

REQUIRED_FILES = \
	.agentkit/docs/ROADMAP.md \
	.agentkit/docs/PROJECT_MAP.md \
	.agentkit/scripts/verify.sh \
	.agentkit/scripts/verify.ps1 \
	.agentkit/rules/local/README.md \
	.agentkit/rules/local/architecture.md \
	.agentkit/rules/local/domain.md \
	.agentkit/rules/local/security.md \
	.agentkit/rules/local/testing.md \
	.agentkit/rules/local/ci.md \
	.agentkit/rules/local/ui-design.md \
	.agentkit/rules/local/integrations.md

RUNTIME_ARTIFACTS = README.md .env.example

help:
	@echo "AgentKit verification targets (e-КТРМ adaptation):"
	@echo "  make detect       - tool-neutral structural detection checks"
	@echo "  make verify-smoke - fast integrity checks (files/rules presence)"
	@echo "  make verify-local - full local DoD checks for adaptation stage"
	@echo "  make verify-ci    - local checks + CI-level artifact checks"

detect: check-required-files check-local-rules
	@echo "OK: detect passed."

check-required-files:
	@python -c "from pathlib import Path; import sys; files=[r'.agentkit/docs/ROADMAP.md', r'.agentkit/docs/PROJECT_MAP.md', r'.agentkit/scripts/verify.sh', r'.agentkit/scripts/verify.ps1', r'.agentkit/rules/local/README.md', r'.agentkit/rules/local/architecture.md', r'.agentkit/rules/local/domain.md', r'.agentkit/rules/local/security.md', r'.agentkit/rules/local/testing.md', r'.agentkit/rules/local/ci.md', r'.agentkit/rules/local/ui-design.md', r'.agentkit/rules/local/integrations.md']; missing=[f for f in files if not Path(f).is_file()]; print('OK: required files exist.' if not missing else 'ERROR: missing required file(s):\\n- ' + '\\n- '.join(missing)); sys.exit(1 if missing else 0)"

check-local-rules:
	@python -c "from pathlib import Path; import sys; files=sorted(Path('.agentkit/rules/local').glob('*.md')); empty=[str(f) for f in files if f.stat().st_size == 0]; ok=bool(files) and not empty; msg='OK: local rule files are non-empty.' if ok else ('ERROR: no local rule files found.' if not files else 'ERROR: empty local rule file(s):\\n- ' + '\\n- '.join(empty)); print(msg); sys.exit(0 if ok else 1)"

check-no-template-markers:
	@python -c "from pathlib import Path; import re, sys; files=[Path('.agentkit/docs/ROADMAP.md'), Path('.agentkit/docs/PROJECT_MAP.md')] + sorted(Path('.agentkit/rules/local').glob('*.md')); pattern=re.compile(r'(<TICKET_ID>|<branch-name>|YYYY-MM-DD|ROADMAP \\(template\\)|PROJECT_MAP \\(template\\))'); hits=[]; \
[hits.extend([f'{p}:{i}:{line.strip()}' for i, line in enumerate(p.read_text(encoding='utf-8').splitlines(), start=1) if pattern.search(line)]) for p in files if p.exists()]; \
print('OK: no template markers found.' if not hits else 'ERROR: template marker(s) detected:\\n- ' + '\\n- '.join(hits)); sys.exit(1 if hits else 0)"

check-roadmap-tickets:
	@python -c "from pathlib import Path; import re, sys; text=Path('.agentkit/docs/ROADMAP.md').read_text(encoding='utf-8'); count=len(re.findall(r'^### T[0-9]+', text, flags=re.MULTILINE)); ok=count>=5; print(f'OK: ROADMAP ticket count = {count}.' if ok else f'ERROR: ROADMAP must include at least 5 concrete tickets, found {count}.'); sys.exit(0 if ok else 1)"

check-project-map-changelog:
	@python -c "from pathlib import Path; import sys; lines=Path('.agentkit/docs/PROJECT_MAP.md').read_text(encoding='utf-8').splitlines(); ok=False; \
[None for line in lines if (line.startswith('- ') and len(line) >= 13 and line[2:6].isdigit() and line[6] == '-' and line[7:9].isdigit() and line[9] == '-' and line[10:12].isdigit() and '[' in line and (ok := True))]; \
print('OK: PROJECT_MAP changelog entry present.' if ok else 'ERROR: PROJECT_MAP changelog entry not found.'); sys.exit(0 if ok else 1)"

check-runtime-artifacts:
	@python -c "from pathlib import Path; import sys; files=[r'README.md', r'.env.example']; missing=[f for f in files if not Path(f).is_file() or Path(f).stat().st_size == 0]; print('OK: runtime artifacts present.' if not missing else 'ERROR: missing runtime artifact(s):\\n- ' + '\\n- '.join(missing)); sys.exit(1 if missing else 0)"

verify-smoke: check-required-files check-local-rules
	@echo "OK: verify-smoke passed."

verify-local: verify-smoke check-no-template-markers check-roadmap-tickets check-project-map-changelog
	@echo "OK: verify-local passed."

verify-ci: verify-local check-runtime-artifacts
	@git diff --check --ignore-cr-at-eol
	@echo "OK: verify-ci passed."
