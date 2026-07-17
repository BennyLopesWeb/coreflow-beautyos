#!/usr/bin/env bash
# architecture_lint.sh — lint pós-flatten CRUD; falha em camadas fake remanescentes.
#
# Uso:
#   ./scripts/migration/architecture_lint.sh <module>
#
# Exit 1 = ABORT migration commit.
set -euo pipefail

MODULE="${1:-}"
if [[ -z "$MODULE" ]]; then
  echo "Usage: $0 <module>" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MOD_PATH="${ROOT}/backend/app/modules/${MODULE}"
FAILED=0

abort() {
  echo "ABORT: $1" >&2
  FAILED=1
}

echo "=============================================="
echo "ARCHITECTURE LINT — module: ${MODULE}"
echo "=============================================="

# CRUD modules must not have .py files under domain/ or application/ after migration
for layer in domain application; do
  if find "${MOD_PATH}/${layer}" -name "*.py" 2>/dev/null | grep -q .; then
    abort "${layer}/ contains .py files in ${MODULE}"
  fi
done

# Prohibited path references (post-migration)
for pattern in "${MODULE}\\.domain" "${MODULE}\\.application" "modules/${MODULE}/domain" "modules/${MODULE}/application"; do
  MATCHES=0
  if out=$(rg -c "${pattern}" "${ROOT}/backend" "${ROOT}/backend/tests" 2>/dev/null); then
    MATCHES=$(echo "$out" | awk -F: '{s+=$2} END {print s+0}')
  fi
  if [[ "${MATCHES}" -gt 0 ]]; then
    abort "prohibited path '${pattern}' found (${MATCHES} matches)"
    rg "${pattern}" "${ROOT}/backend" "${ROOT}/backend/tests" 2>/dev/null || true
  fi
done

# Fake hexagonal folders in CRUD (ports/adapters inside module)
for sub in ports adapters infrastructure; do
  if [[ -d "${MOD_PATH}/${sub}" ]]; then
    abort "forbidden subfolder '${sub}/' in CRUD module ${MODULE}"
  fi
done

# Global grep for leftover QueryService aliases (informational)
echo ""
echo "--- Info: legacy QueryService names in module ---"
rg "QueryService" "${MOD_PATH}" 2>/dev/null || echo "(none)"

echo ""
if [[ "$FAILED" -eq 1 ]]; then
  echo "RESULT: FAIL — do not commit"
  exit 1
fi

echo "RESULT: PASS"
exit 0
