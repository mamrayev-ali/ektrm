#!/usr/bin/env bash
set -euo pipefail

# AgentKit verify.sh (Core)
# - Enforces DOC-gate: PROJECT_MAP.md must be updated on every ticket that changes repo files.
# - Runs Makefile contract targets (verify-local / verify-ci / verify-smoke).
#
# Usage:
#   ./.agentkit/scripts/verify.sh local
#   ./.agentkit/scripts/verify.sh ci
#   ./.agentkit/scripts/verify.sh smoke

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_MAP="$ROOT_DIR/.agentkit/docs/PROJECT_MAP.md"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

require_git_repo() {
  git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    || die "Not a git repository (expected at $ROOT_DIR)."
}

require_project_map_exists() {
  [[ -f "$PROJECT_MAP" ]] || die "Missing PROJECT_MAP.md at: $PROJECT_MAP"
}

# DOC-gate: If any repo file changed, PROJECT_MAP.md must be changed too.
#
# We interpret "repo file changed" as: there is any staged or unstaged change
# excluding the PROJECT_MAP itself.
#
# This is strict by design (no skip mode).
enforce_doc_gate() {
  local status
  status="$(git -C "$ROOT_DIR" status --porcelain)"

  # No changes at all -> nothing to enforce.
  if [[ -z "$status" ]]; then
    echo "✅ DOC-gate: no changes detected."
    return 0
  fi

  # Identify changes excluding PROJECT_MAP
  # We treat both staged and unstaged equally.
  local non_doc_changes
  non_doc_changes="$(echo "$status" | awk '{print $2}' | grep -vE '^\.agentkit/docs/PROJECT_MAP\.md$' || true)"

  # If only PROJECT_MAP changed, that's ok.
  if [[ -z "$non_doc_changes" ]]; then
    echo "✅ DOC-gate: only PROJECT_MAP.md changed."
    return 0
  fi

  # If other files changed, PROJECT_MAP must also be changed.
  local project_map_changed
  project_map_changed="$(echo "$status" | awk '{print $2}' | grep -E '^\.agentkit/docs/PROJECT_MAP\.md$' || true)"

  if [[ -z "$project_map_changed" ]]; then
    echo "❌ DOC-gate failed."
    echo ""
    echo "You changed repository files but did NOT update:"
    echo "  .agentkit/docs/PROJECT_MAP.md"
    echo ""
    echo "Changed files (excluding PROJECT_MAP):"
    echo "$non_doc_changes" | sed 's/^/  - /'
    echo ""
    die "Update PROJECT_MAP.md and rerun verification."
  fi

  echo "✅ DOC-gate: PROJECT_MAP.md updated alongside code changes."
}

run_make_target() {
  local target="$1"
  echo ""
  echo "==> Running: make $target"
  echo ""

  make -C "$ROOT_DIR" "$target"
}

usage() {
  cat <<EOF
Usage:
  ./.agentkit/scripts/verify.sh <mode>

Modes:
  local   -> make verify-local
  smoke   -> make verify-smoke
  ci      -> make verify-ci
EOF
  exit 2
}

main() {
  require_git_repo
  require_project_map_exists

  local mode="${1:-}"
  [[ -n "$mode" ]] || usage

  # Enforce doc gate before verification
  enforce_doc_gate

  case "$mode" in
    local) run_make_target "verify-local" ;;
    smoke) run_make_target "verify-smoke" ;;
    ci)    run_make_target "verify-ci" ;;
    *) usage ;;
  esac

  echo ""
  echo "✅ Verification complete: $mode"
}

main "$@"
