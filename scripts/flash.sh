#!/usr/bin/env bash
#
# Build and flash Ladispad firmware onto the Pro Micro (ATmega32U4).
#
#   ./scripts/flash.sh                       # vial keymap, auto-detect bootloader
#   ./scripts/flash.sh default
#   ./scripts/flash.sh via --bootloader caterina
#   ./scripts/flash.sh via --no-build        # flash the existing build/*.hex
#
# Entering the bootloader (Pro Micro with Caterina):
#   * bridge RST to GND briefly twice, releasing between touches
#   * the second reset should be within about 750 ms; Caterina then appears
#     as a temporary /dev/cu.usbmodem* port
#
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"

KEYMAP_ARG=""
BOOTLOADER="auto"
DO_BUILD=1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --bootloader) BOOTLOADER="$2"; shift 2 ;;
        --no-build)   DO_BUILD=0; shift ;;
        -h|--help)    sed -n '2,20p' "$0"; exit 0 ;;
        *)            KEYMAP_ARG="$1"; shift ;;
    esac
done
KEYMAP="${KEYMAP_ARG:-$KEYMAP}"

detect_bootloader() {
    if dfu-programmer atmega32u4 get bootloader-version >/dev/null 2>&1; then
        echo "atmel-dfu"; return
    fi
    if compgen -G "/dev/cu.usbmodem*" >/dev/null 2>&1 || compgen -G "/dev/tty.usbmodem*" >/dev/null 2>&1; then
        echo "caterina"; return
    fi
    echo "unknown"
}

if [[ "$BOOTLOADER" == "auto" ]]; then
    detected="$(detect_bootloader)"
    case "$detected" in
        unknown)
            warn "no board detected in bootloader mode - assuming the declared 'caterina'"
            warn "put the board in bootloader mode: briefly bridge RST to GND twice"
            BOOTLOADER="caterina"
            ;;
        *)  log "detected bootloader: $detected"; BOOTLOADER="$detected" ;;
    esac
fi

if [[ "$DO_BUILD" == "1" ]]; then
    "$(dirname "$0")/build.sh" "$KEYMAP"
else
    require_qmk
fi

require_avr_toolchain
cd "$QMK_FIRMWARE"
log "flashing ladis:$KEYMAP (bootloader: $BOOTLOADER)"
make "ladis:${KEYMAP}:flash" PYTHON="$(qmk_python)" BOOTLOADER="$BOOTLOADER"
log "flash complete - the pad should re-enumerate as a keyboard"
