#!/usr/bin/env bash
# dependency_scan.sh — STEP 0: grafo de dependências antes do flatten CRUD.
#
# Uso:
#   ./scripts/migration/dependency_scan.sh <module>
#
# Exemplo:
#   ./scripts/migration/dependency_scan.sh asset
#
# Retorna exit 0 sempre; revisão humana decide APPROVED Pn.
set -euo pipefail

MODULE="${1:-}"
if [[ -z "$MODULE" ]]; then
  echo "Usage: $0 <module>" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MOD_PATH="backend/app/modules/${MODULE}"
LEGACY_DOMAIN="modules/${MODULE}/domain"
LEGACY_APP="modules/${MODULE}/application"

echo "=============================================="
echo "DEPENDENCY SCAN — module: ${MODULE}"
echo "=============================================="
echo ""

if [[ ! -d "${ROOT}/${MOD_PATH}" ]]; then
  echo "ERROR: module path not found: ${MOD_PATH}" >&2
  exit 1
fi

echo "--- TREE (current) ---"
find "${ROOT}/${MOD_PATH}" -name "*.py" ! -path "*__pycache__*" | sort
echo ""

echo "--- LOC (module) ---"
total=0
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  n=$(wc -l < "$f" | tr -d ' ')
  total=$((total + n))
done < <(find "${ROOT}/${MOD_PATH}" -name "*.py" ! -path "*__pycache__*" 2>/dev/null || true)
echo "${total} total"
echo ""

echo "--- INBOUND imports (who uses this module) ---"
rg -l "modules\.${MODULE}|modules/${MODULE}" "${ROOT}/backend" "${ROOT}/backend/tests" 2>/dev/null \
  | grep -v "${MOD_PATH}" \
  | sort || echo "(none)"
echo ""

echo "--- INBOUND by legacy path (domain/application) ---"
rg -l "${MODULE}\.domain|${MODULE}\.application|modules/${MODULE}/domain|modules/${MODULE}/application" \
  "${ROOT}" 2>/dev/null | sort || echo "(none)"
echo ""

echo "--- OUTBOUND imports (from module files) ---"
rg "^from |^import " "${ROOT}/${MOD_PATH}" --no-heading 2>/dev/null | sort -u || true
echo ""

echo "--- PUBLIC SYMBOLS (class/def in module) ---"
rg "^class |^def " "${ROOT}/${MOD_PATH}" --no-heading 2>/dev/null | sort || true
echo ""

echo "--- COUPLING METRICS ---"
INBOUND_COUNT=$(rg -l "modules\.${MODULE}|modules/${MODULE}" "${ROOT}/backend" "${ROOT}/backend/tests" 2>/dev/null \
  | grep -v "${MOD_PATH}" | wc -l | tr -d ' ')
OUTBOUND_COUNT=$(rg "^from |^import " "${ROOT}/${MOD_PATH}" --no-heading 2>/dev/null | wc -l | tr -d ' ')
PKG_DEPTH=1
if [[ -d "${ROOT}/${MOD_PATH}/domain" ]] || [[ -d "${ROOT}/${MOD_PATH}/application" ]]; then
  PKG_DEPTH=3
fi
echo "Inbound file references:  ${INBOUND_COUNT}"
echo "Outbound import lines:    ${OUTBOUND_COUNT}"
echo "Package depth (est.):     ${PKG_DEPTH} (target flat: 1-2)"
echo ""

echo "--- TIER CHECK ---"
case "$MODULE" in
  booking|scheduling)
    echo "TIER: CORE — DO NOT FLATTEN"
    ;;
  identity|workflow|push)
    echo "TIER: CORE-SUPPORT — DO NOT FLATTEN"
    ;;
  inventory|customer|asset|catalog|invoice|order|waitlist|payments)
    echo "TIER: CRUD — flatten allowed if 12 criteria pass"
    ;;
  platform|observability|mobile|ai|marketplace)
    echo "TIER: OPS — reorganize only (Wave 3)"
    ;;
  *)
    echo "TIER: UNKNOWN — verify ModuleTieringPolicy.md"
    ;;
esac
echo ""
echo "Next: human approval APPROVED P<n> before editing code."
