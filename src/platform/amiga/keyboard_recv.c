/**
 * this file is part of amigahid-pico, (c) 2021 just nine <nine@aphlor.org>
 * please locate the full source at https://github.com/borb/amigahid-pico
 *
 * released under the terms of the Eclipse Public License 2.0 (EPL-2.0).
 * please find the complete license text at https://spdx.org/licenses/EPL-2.0
 *
 * real amiga keyboard receive path.
 *
 * on boards with a keyboard input (HAS_KBD_IN: a dedicated pin pair on rev6, or
 * controller port 2 repurposed on rev4 with PORT2_ROLE=KEYBOARD), a physically
 * attached amiga keyboard can drive the amiga alongside the usb/bluetooth path.
 * the pico acts as the host: a real keyboard is the clock master and clocks out
 * keycodes; a pio state machine samples them and drives the ~85us handshake
 * back autonomously. decoded keycodes are pushed into the same output queue the
 * usb/bluetooth path feeds, so the amiga-facing transmitter cannot tell a real
 * keypress from a usb one.
 *
 * the amiga keyboard frame is the mirror of the transmit path in
 * keyboard_serial_io.c: 8 bits, msb first, active low, with the byte rotated
 * left by one so the up/down flag is the last (lsb) bit on the wire. we undo
 * the active-low inversion and the rotate on the cpu side here.
 *
 * hard reset is signalled out of band: a real keyboard holds kclk low for at
 * least 500ms, which on big-box machines (a2000/3000/4000) is the only reset
 * signalling there is. the state machine just sees silence, so the hold is
 * detected here by polling the line and forwarded with amiga_kbdin_reset().
 */

#include "config.h"
#include "keyboard_recv.h"

#ifdef HAS_KBD_IN

#include "keyboard.h"
#include "keyboard_serial_io.h"
#include "keyboard_recv.pio.h" // generated at compile time
#include "util/debug_cons.h"
#include "util/output.h"

#include <stdint.h>
#include <stdbool.h>

#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "hardware/pio.h"

// how long kclk must sit low before we call it a reset rather than a data
// strobe. keyboards hold for >=500ms, a bit strobe is low for ~20us, so
// anything in between works; overridable from the build for bench tuning.
#ifndef KBDIN_RESET_HOLD_MS
#  define KBDIN_RESET_HOLD_MS 250
#endif

// pio is otherwise unused on this platform, so pio0 is ours to take
static PIO recv_pio = pio0;
static uint recv_sm;
static uint recv_offset;

// kclk low-hold tracking; kbd_reset_held describes the state of the *wire*,
// whether or not we ended up being the one to assert reset (a real keyboard
// also holds kclk after a ctrl-amiga-amiga, which the key events themselves
// have already actioned in keyboard_serial_io.c).
static bool clk_was_low = false;
static bool clk_seen_idle = false;
static uint32_t clk_low_since = 0;
static bool kbd_reset_held = false;

void amiga_keyboard_recv_init(void)
{
    recv_offset = pio_add_program(recv_pio, &amiga_recv_program);
    recv_sm = pio_claim_unused_sm(recv_pio, true);

    amiga_recv_pio_init(recv_pio, recv_sm, recv_offset, KBD_REAL_CLK, KBD_REAL_DAT);
}

/**
 * bring the receiver back to a known idle state. a kclk hold leaves a single
 * sampled bit stranded in the isr, so the frame that follows the hold would be
 * assembled from one stale bit plus seven new ones. restarting discards the
 * partial frame (and anything queued behind it) rather than injecting garbage.
 */
static void amiga_keyboard_recv_restart(void)
{
    pio_sm_set_enabled(recv_pio, recv_sm, false);
    pio_sm_clear_fifos(recv_pio, recv_sm);
    pio_sm_restart(recv_pio, recv_sm);
    pio_sm_clkdiv_restart(recv_pio, recv_sm);

    // the program's first instruction returns kdat to hi-z, so a jump to the
    // start also undoes a handshake the hold may have interrupted
    pio_sm_exec(recv_pio, recv_sm, pio_encode_jmp(recv_offset));
    pio_sm_set_enabled(recv_pio, recv_sm, true);
}

/**
 * watch kclk for the long low the keyboard uses to demand a hard reset.
 */
static void amiga_keyboard_recv_reset_task(void)
{
    bool clk_low = gpio_get(KBD_REAL_CLK) == 0;

    if (!clk_low) {
        clk_was_low = false;
        clk_seen_idle = true;

        if (!kbd_reset_held)
            return;

        // keyboard has let go of kclk: bring the amiga back out of reset and
        // resynchronise the receiver before the keyboard resumes sending
        kbd_reset_held = false;
        amiga_kbdin_reset(false);
        amiga_keyboard_recv_restart();
        ahprintf("[akb] real keyboard released reset\n");
        return;
    }

    if (!clk_was_low) {
        clk_was_low = true;
        clk_low_since = time_us_32();
        return;
    }

    // a line that has been low ever since boot is an unconnected or unpowered
    // input, not a reset request; holding the amiga down forever over that would
    // be a poor failure mode, so wait until we have seen the bus idle once
    if (kbd_reset_held || !clk_seen_idle)
        return;

    if ((uint32_t)(time_us_32() - clk_low_since) < (KBDIN_RESET_HOLD_MS * 1000u))
        return;

    kbd_reset_held = true;
    ahprintf("[akb] real keyboard held kclk low; asserting reset\n");
    amiga_kbdin_reset(true);
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

    // drain first, act on the line state second: the key events leading up to a
    // ctrl-amiga-amiga reach the combo tracking before the keyboard's kclk hold
    // is considered, so the two paths agree on who owns the reset
    amiga_keyboard_recv_reset_task();
}

#else // !HAS_KBD_IN

void amiga_keyboard_recv_init(void) {}
void amiga_keyboard_recv_task(void) {}

#endif // HAS_KBD_IN
