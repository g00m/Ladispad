#!/usr/bin/env bash
#
# Shared environment for Ladispad firmware work. Source this from the other
# scripts:  source "$(dirname "$0")/env.sh"
#
# Layout:
#   $LADISPAD_ROOT/qmk/ladis         <- source of truth for the QMK keyboard
#   $QMK_FIRMWARE/keyboards/ladis   <- synced build copy
#
# Overridable environment variables:
#   QMK_FIRMWARE           Vial-QMK checkout (default ~/Development/vial-qmk)
#   QMK_PYTHON_VENV        QMK venv          (default ~/Development/qmk-venv)
#   AVR_TOOLCHAIN_PREFIX   AVR toolchain     (default ~/Development/avr-toolchain)
#   KEYMAP                 default keymap    (default vial)

set -euo pipefail

LADISPAD_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export LADISPAD_ROOT

export QMK_FIRMWARE="${QMK_FIRMWARE:-$HOME/Development/vial-qmk}"
export QMK_PYTHON_VENV="${QMK_PYTHON_VENV:-$HOME/Development/qmk-venv}"
if [[ -d "$QMK_PYTHON_VENV/bin" ]]; then
    export PATH="$QMK_PYTHON_VENV/bin:$PATH"
fi
export AVR_TOOLCHAIN_PREFIX="${AVR_TOOLCHAIN_PREFIX:-$HOME/Development/avr-toolchain}"
export KEYMAP="${KEYMAP:-vial}"

export QMK_HOME="$QMK_FIRMWARE"
export LADISPAD_KEYBOARD_SOURCE="$LADISPAD_ROOT/qmk/ladis"
export LADISPAD_KEYBOARD_DIR="$QMK_FIRMWARE/keyboards/ladis"
export LADISPAD_BUILD_DIR="$LADISPAD_ROOT/build"

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!!\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31mERR\033[0m %s\n' "$*" >&2; exit 1; }

# --- AVR toolchain -----------------------------------------------------------
# Order: explicit prefix -> our source-built toolchain -> whatever is on PATH.
find_avr_bin() {
    if [[ -n "${AVR_TOOLCHAIN_PREFIX:-}" && -x "$AVR_TOOLCHAIN_PREFIX/bin/avr-gcc" ]]; then
        echo "$AVR_TOOLCHAIN_PREFIX/bin"; return 0
    fi
    if command -v avr-gcc >/dev/null 2>&1; then
        dirname "$(command -v avr-gcc)"; return 0
    fi
    return 1
}

require_avr_toolchain() {
    local bin
    if ! bin="$(find_avr_bin)"; then
        cat >&2 <<'EOF'
No AVR toolchain found.

  Homebrew no longer ships avr-gcc, and the prebuilt macOS AVR toolchains are
  x86_64 only (they need Rosetta 2). Build a native one once:

      ./scripts/build_avr_toolchain.sh        # ~30 min, installs to ~/Development/avr-toolchain

  Or point AVR_TOOLCHAIN_PREFIX at an existing toolchain.
EOF
        exit 1
    fi
    export PATH="$bin:$PATH"
    log "AVR toolchain: $bin/avr-gcc ($("$bin/avr-gcc" -dumpversion))"
}

# --- QMK ---------------------------------------------------------------------
require_qmk() {
    [[ -d "$QMK_FIRMWARE" ]] || die "Vial-QMK tree not found at $QMK_FIRMWARE - run ./scripts/setup.sh first"
    [[ -f "$QMK_FIRMWARE/Makefile" ]] || die "$QMK_FIRMWARE does not look like a QMK checkout"
    [[ -f "$QMK_FIRMWARE/quantum/vial.c" ]] || die "$QMK_FIRMWARE is not Vial-QMK; set QMK_FIRMWARE to a vial-kb/vial-qmk checkout"
}

qmk_python() {
    if [[ -x "$QMK_PYTHON_VENV/bin/python3" ]]; then
        echo "$QMK_PYTHON_VENV/bin/python3"
    else
        echo "python3"
    fi
}

# Copy qmk/ladis into the QMK tree (the tree is a build workspace, not a
# source of truth - never edit keyboards/ladis by hand).
sync_keyboard() {
    require_qmk
    mkdir -p "$LADISPAD_KEYBOARD_DIR"
    rsync -a --delete "$LADISPAD_KEYBOARD_SOURCE/" "$LADISPAD_KEYBOARD_DIR/"
    log "qmk/ladis -> keyboards/ladis"
}
