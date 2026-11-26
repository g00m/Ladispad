#!/usr/bin/env bash
#
# Build Ladispad firmware.
#
#   ./scripts/build.sh [keymap]        # default keymap: vial
#   ./scripts/build.sh default
#   ./scripts/build.sh all             # every keymap in firmware/ladis/keymaps
#
# The resulting .hex is copied to build/ladis_<keymap>.hex
#
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"

TARGET="${1:-$KEYMAP}"
if [[ "$TARGET" == "all" ]]; then
    TARGETS=()
    for d in "$LADISPAD_KEYBOARD_SOURCE"/keymaps/*/; do
        TARGETS+=("$(basename "$d")")
    done
else
    TARGETS=("$TARGET")
fi

require_qmk
require_avr_toolchain
sync_keyboard
mkdir -p "$LADISPAD_BUILD_DIR"

PY="$(qmk_python)"
log "using python: $PY"
if ! "$PY" -c "import milc" 2>/dev/null; then
    warn "QMK python requirements missing in $PY - run ./scripts/setup.sh"
fi

cd "$QMK_FIRMWARE"
for km in "${TARGETS[@]}"; do
    log "building ladis:$km"
    make "ladis:$km" PYTHON="$PY"
    hex="$QMK_FIRMWARE/ladis_${km}.hex"
    if [[ -f "$hex" ]]; then
        cp "$hex" "$LADISPAD_BUILD_DIR/ladis_${km}.hex"
        log "  -> build/ladis_${km}.hex  ($(stat -f%z "$hex") bytes)"
    fi
done

log "build complete"
ls -la "$LADISPAD_BUILD_DIR"/*.hex 2>/dev/null || true
