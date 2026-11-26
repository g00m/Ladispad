---
name: ladispad-firmware-update
description: Safely build, back up, flash, restore, and verify LadisPad Vial firmware. Use whenever changing, building, obtaining, flashing, or restoring LadisPad firmware, Vial mappings, layers, encoders, or macros.
---

# LadisPad firmware update

Use this workflow for every firmware update that could affect the connected LadisPad. The controller is an ATmega32U4 Pro Micro using Caterina; GitHub Actions builds the firmware, and flashing happens locally.

## 1. Verify the checkout and artifact

1. Locate the Git repository and inspect `git status`, current branch, and commit. Preserve uncommitted work. Do not switch to or push directly to `main`.
2. Build the Vial firmware from the current intended commit. Prefer the repository's GitHub Actions build when local AVR tooling is unavailable. Confirm the workflow succeeded and the HEX artifact belongs to that commit; never flash a stale or unidentified artifact.
3. Keep the current keymap sources straight: `qmk/ladis/keymaps/vial/keymap.c` defines firmware defaults; `vial.json` defines Vial's physical UI layout; the live Vial configuration is stored on the keyboard and exported as `.vil`.

## 2. Back up the live Vial configuration before flashing

1. Confirm `vitaly` is installed and `vitaly devices` identifies the connected device as `LadisPad`. If the device is absent or ambiguous, stop.
2. Vial can hold exclusive access to the HID device. If `vitaly save` reports an HID/exclusive-access error, stop and ask the user to close Vial; do not flash or terminate the app automatically.
3. Save a **new, uniquely named** snapshot outside the repository, for example:
   ```bash
   backup_dir="$HOME/Downloads/ladispad-vial-backups"
   mkdir -p "$backup_dir"
   backup="$backup_dir/ladispad-vial-$(date +%Y%m%d-%H%M%S).vil"
   vitaly save -f "$backup"
   ```
4. Validate the snapshot as JSON and confirm it contains `layout`, `encoder_layout`, `macro`, `uid`, `via_protocol`, and `vial_protocol`. Report the layer count and macro count. Compare `uid` with `VIAL_KEYBOARD_UID` in `qmk/ladis/keymaps/vial/config.h` (the exported integer represents those UID bytes in little-endian order) and confirm protocol metadata matches the intended firmware.
5. If the user expects macros but the snapshot has no macros, stop and ask before flashing. Never substitute the tracked `qmk/ladis/keymaps/vial/ladispad.vil` baseline for this fresh snapshot; it may be stale.
6. If saving or validation fails, stop. A successful fresh backup is a hard precondition for flashing.

## 3. Flash with Caterina and no automatic erase

1. Use the HEX artifact verified in step 1 and the Caterina AVR109 protocol. Do not use DFU tools for this controller.
2. Tell the user to enter the Pro Micro bootloader with the documented double reset (RST-to-GND twice). Wait for the temporary `/dev/cu.usbmodem*` port, then flash with AVRDUDE's `-D` option, for example:
   ```bash
   avrdude -D -p atmega32u4 -c avr109 -P "$PORT" -b 57600 \
     -U "flash:w:${HEX}:i"
   ```
   `-D` disables AVRDUDE's automatic chip erase. Keep the `.vil` backup even when using `-D`.
3. If the expected port does not appear, the board identity is wrong, or AVRDUDE fails verification, stop and report the error. Keep the backup; do not retry with a different programmer or erase option by guesswork.

## 4. Verify and restore Vial data

1. Wait for the board to reboot, then confirm `vitaly devices` again identifies the same LadisPad.
2. Read the post-flash configuration into a separate temporary `.vil` file and compare `layout`, `encoder_layout`, and `macro` with the pre-flash snapshot.
3. If those fields differ, confirm the device UID and protocol metadata still match, then restore the fresh snapshot:
   ```bash
   vitaly load -f "$backup"
   ```
   Re-read the device and verify the same fields match the backup. If identity/protocol checks fail or restore/readback fails, stop and report the backup path; do not load it onto a different device.
4. Report the artifact commit, flash verification result, backup path, and whether restoration was needed. Keep the backup until the user confirms the keyboard works.

## Guardrails

- Never flash unless a fresh, validated `.vil` snapshot exists.
- Never assume EEPROM survives a firmware update; `-D` reduces erase risk, and the `.vil` is the recovery path for keys, layers, encoder mappings, and macros.
- Do not edit `vial.json` to preserve user mappings. Update `keymap.c` defaults only when requested; the live `.vil` remains the authoritative backup.
- Do not overwrite or delete existing backups. Do not flash as part of a build-only request.