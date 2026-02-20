# Makefile (AgentKit Core contract)
#
# This Makefile defines the verification entrypoints referenced by AGENTS.md.
# In "Core" it is intentionally a placeholder. During project adaptation, you
# implement these targets with real commands for your repo.
#
# Contract targets:
# - make verify-local  (local DoD)
# - make verify-smoke  (optional fast subset)
# - make verify-ci     (CI DoD)

.PHONY: help verify-local verify-smoke verify-ci

help:
	@echo "AgentKit verification targets:"
	@echo "  make verify-local  - local DoD: format/lint/type + unit/integration + coverage + API e2e smoke"
	@echo "  make verify-smoke  - optional fast checks subset"
	@echo "  make verify-ci     - CI DoD: full e2e + security + DAST + container scans"
	@echo ""
	@echo "Core mode: these targets are placeholders."
	@echo "Project adaptation: implement real commands inside this Makefile."

verify-local:
	@echo "ERROR: verify-local is not implemented for this repo yet."
	@echo "Implement real commands in Makefile during project adaptation."
	@exit 2

verify-smoke:
	@echo "ERROR: verify-smoke is not implemented for this repo yet."
	@echo "Implement real commands in Makefile during project adaptation."
	@exit 2

verify-ci:
	@echo "ERROR: verify-ci is not implemented for this repo yet."
	@echo "Implement real commands in Makefile during project adaptation."
	@exit 2
