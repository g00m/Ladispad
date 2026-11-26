/* Copyright 2021 ajmandourah
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#pragma once

/*
 * Hardware configuration now lives in keyboard.json:
 *   - processor / bootloader
 *   - matrix_pins.direct (D3 B1 D4 C6 D7 E6 B4 B5 F4 F7 B3)
 *   - encoder.rotary pins (F6/F5 and B2/B6)
 *   - USB VID/PID
 *   - features (bootmagic, mousekey, extrakey, nkro, encoder, oled)
 *
 * Only settings without a keyboard.json equivalent stay here.
 */

/* Debounce */
#define DEBOUNCE 5

/* Mechanical locking support. Use KC_LCAP, KC_LNUM or KC_LSCR instead in keymap */
#define LOCKING_SUPPORT_ENABLE

/* Locking resynchronize hack */
#define LOCKING_RESYNC_ENABLE

/* VIA: number of dynamic (remappable) layers */
#define DYNAMIC_KEYMAP_LAYER_COUNT 4
