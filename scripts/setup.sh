#!/usr/bin/env bash
#
# One-time setup for Ladispad firmware development.
#
#   ./scripts/setup.sh [--skip-toolchain]
#
# Does:
#   1. clone Vial-QMK (shallow) if missing
#   2. create a Python venv with QMK's requirements
#   3. sync qmk/ladis into the Vial-QMK tree
#   4. report the AVR toolchain / flashing tool status
#
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"

SKIP_TOOLCHAIN=0
[[ "${1:-}" == "--skip-toolchain" ]] && SKIP_TOOLCHAIN=1

# 1. QMK ---------------------------------------------------------------------
if [[ ! -d "$QMK_FIRMWARE" ]]; then
    log "cloning Vial-QMK -> $QMK_FIRMWARE"
    git clone --depth 1 https://github.com/vial-kb/vial-qmk.git "$QMK_FIRMWARE"
else
    log "Vial-QMK checkout already present: $QMK_FIRMWARE"
fi
require_qmk
log "initializing Vial-QMK submodules"
git -C "$QMK_FIRMWARE" submodule update --init --recursive

# 2. Python venv with QMK's requirements -------------------------------------
if [[ ! -x "$QMK_PYTHON_VENV/bin/python3" ]]; then
    log "creating QMK python venv: $QMK_PYTHON_VENV"
    python3 -m venv "$QMK_PYTHON_VENV"
fi
log "installing QMK python requirements"
"$QMK_PYTHON_VENV/bin/pip" install --quiet --upgrade pip
"$QMK_PYTHON_VENV/bin/pip" install --quiet -r "$QMK_FIRMWARE/requirements.txt"
"$QMK_PYTHON_VENV/bin/pip" install --quiet qmk

# 3. Keyboard ---------------------------------------------------------------
sync_keyboard

# 4. Toolchain status -------------------------------------------------------
echo
log "toolchain status"
if bin="$(find_avr_bin)"; then
    log "  avr-gcc      : $bin/avr-gcc ($("$bin/avr-gcc" -dumpversion))"
elif [[ "$SKIP_TOOLCHAIN" == "1" ]]; then
    warn "  avr-gcc      : MISSING (skipped by request)"
else
    warn "  avr-gcc      : MISSING"
    warn "                 build it with: ./scripts/build_avr_toolchain.sh"
fi
for tool in dfu-programmer dfu-util avrdude; do
    if command -v "$tool" >/dev/null 2>&1; then
        log "  $tool: $(command -v "$tool")"
    else
        warn "  $tool: missing (brew install $tool)"
    fi
done

echo
log "next steps"
cat <<'EOF'
    ./scripts/build.sh vial         # build the Vial keymap
    ./scripts/flash.sh vial         # build + flash (board in bootloader)
    ./scripts/build.sh default      # build the standard QMK keymap
    ./scripts/case.sh               # rebuild and verify the case STLs
EOF
