/**
 * this file is part of amigahid-pico, (c) 2021 just nine <nine@aphlor.org>
 * please locate the full source at https://github.com/borb/amigahid-pico
 *
 * released under the terms of the Eclipse Public License 2.0 (EPL-2.0).
 * please find the complete license text at https://spdx.org/licenses/EPL-2.0
 *
 * real amiga keyboard receive path.
 *
 * when built with PORT2_ROLE=KEYBOARD, controller port 2 is repurposed as an
 * input for a physically attached amiga keyboard (rather than the amiga). the
 * pico acts as the host: a real keyboard is the clock master and clocks out
 * keycodes; a pio state machine samples them and drives the ~85us handshake
 * back autonomously. decoded keycodes are pushed into the same output queue the
 * usb/bluetooth path feeds, so the amiga-facing transmitter cannot tell a real
 * keypress from a usb one.
 *
 * the amiga keyboard frame is the mirror of the transmit path in
 * keyboard_serial_io.c: 8 bits, msb first, active low, with the byte rotated
 * left by one so the up/down flag is the last (lsb) bit on the wire. we undo
 * the active-low inversion and the rotate on the cpu side here.
 */

#include "config.h"
#include "keyboard_recv.h"

#ifdef PORT2_ROLE_KEYBOARD

#include "keyboard.h"
#include "keyboard_serial_io.h"
#include "keyboard_recv.pio.h" // generated at compile time
#include "util/debug_cons.h"

#include <stdint.h>
#include <stdbool.h>

#include "pico/stdlib.h"
#include "hardware/pio.h"

// pio is otherwise unused on this platform, so pio0 is ours to take
static PIO recv_pio = pio0;
static uint recv_sm;

void amiga_keyboard_recv_init(void)
{
    uint offset = pio_add_program(recv_pio, &amiga_recv_program);
    recv_sm = pio_claim_unused_sm(recv_pio, true);

    amiga_recv_pio_init(recv_pio, recv_sm, offset, KBD_REAL_CLK, KBD_REAL_DAT);
}

void amiga_keyboard_recv_task(void)
{
    while (!pio_sm_is_rx_fifo_empty(recv_pio, recv_sm)) {
        uint32_t word = pio_sm_get(recv_pio, recv_sm);

        // undo active-low sampling, then rotate right by one to recover the
        // original amiga code (bit 7 = up/down, bits 6..0 = keycode).
        uint8_t logical = (uint8_t)(~(uint8_t)(word & 0xff));
        uint8_t code = (uint8_t)((logical >> 1) | (logical << 7));

        switch (code) {
            // keyboard-mcu housekeeping codes: consume, never forward to the
            // amiga (we synthesise our own power-up codes on the output side).
            case AMIGA_LOSTSYNC:
            case AMIGA_OBOFLOW:
            case AMIGA_CTRFAIL:
            case AMIGA_KBDFAIL:
            case AMIGA_INITPOWER:
            case AMIGA_TERMPOWER:
            case AMIGA_UNKNOWN:
            case AMIGA_RESET: // ctrl-amiga-amiga also arrives as key events; see below
                dbgcons_amiga_key(0, code, "r");
                break;

            default: {
                bool up = (code & 0x80) != 0;
                uint8_t keycode = code & 0x7f;

                dbgcons_amiga_key(0, keycode, up ? "ru" : "rd");

                // ctrl-amiga-amiga reset is recognised from these key events by
                // amiga_send_rawkey's combo tracking, mirroring the usb path.
                amiga_send_rawkey(keycode, up);
                break;
            }
        }
    }
}

#else // !PORT2_ROLE_KEYBOARD

void amiga_keyboard_recv_init(void) {}
void amiga_keyboard_recv_task(void) {}

#endif // PORT2_ROLE_KEYBOARD
