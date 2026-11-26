#!/usr/bin/env bash
#
# Rebuild the 3D-printable case STLs from the original laser-cut SVGs, then
# verify the meshes against the source geometry.
#
#   ./scripts/case.sh          # build + verify
#   ./scripts/case.sh build    # build only
#   ./scripts/case.sh verify   # verify only
#
# The Python environment is created once at ~/Development/ladispad-case-venv
# (kept outside iCloud: venvs are thousands of small files).
#
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"

CASE_DIR="$LADISPAD_ROOT/case/3d"
VENV="${LADISPAD_CASE_VENV:-$HOME/Development/ladispad-case-venv}"
MODE="${1:-all}"

if [[ ! -x "$VENV/bin/python" ]]; then
    log "creating case venv: $VENV"
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet shapely trimesh matplotlib numpy manifold3d networkx rtree
fi

cd "$CASE_DIR"
case "$MODE" in
    build)  "$VENV/bin/python" build_case.py ;;
    verify) "$VENV/bin/python" verify_case.py ;;
    all)    "$VENV/bin/python" build_case.py && "$VENV/bin/python" verify_case.py ;;
    *)      die "unknown mode: $MODE (use build|verify|all)" ;;
esac
