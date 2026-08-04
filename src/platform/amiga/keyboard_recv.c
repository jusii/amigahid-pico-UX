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
 *
 * the hold also strands a sampled bit in the state machine, so the receiver is
 * resynchronised after every reset. that is deliberately not tied to observing
 * the hold: a ctrl-amiga-amiga typed on the real keyboard is recognised from the
 * key events first, and asserting reset blocks the main loop for 500ms, so the
 * hold can begin and end without a single poll landing on it.
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

// a keyboard which never lets go of kclk is unplugged, unpowered or broken
// rather than asking for a reset. give up after this long: a reset also mutes
// the usb and bluetooth paths, so an unbounded hold would take the whole adapter
// down until it was power cycled.
#ifndef KBDIN_RESET_HOLD_MAX_MS
#  define KBDIN_RESET_HOLD_MAX_MS 3000
#endif

// the poll below runs from the main loop, which blocks for milliseconds at a
// time whilst it clocks a keycode out to the amiga - and for half a second
// whilst it asserts reset. two low samples either side of such a gap say nothing
// about the line in between (kclk is low a third of the time whilst a keyboard
// transmits), so only samples close enough together to count as one continuous
// observation may extend a hold.
#define KBDIN_POLL_GAP_MAX_MS 10

// how long the wire must have been quiet before a pending resynchronisation is
// safe to perform. restarting mid-byte would only move the misalignment, so wait
// until nothing can be in flight; a byte plus its handshake is well under 1ms.
#define KBDIN_RESYNC_IDLE_MS 5

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
static uint32_t clk_last_poll = 0;
static bool kbd_reset_held = false;
static bool kbd_reset_abandoned = false;

// resynchronisation tracking: armed when a reset begins, performed once the wire
// has been quiet for long enough that restarting cannot eat a byte in flight.
static bool reset_was_active = false;
static bool resync_pending = false;
static uint32_t recv_last_active = 0;

void amiga_keyboard_recv_init(void)
{
    recv_offset = pio_add_program(recv_pio, &amiga_recv_program);
    recv_sm = pio_claim_unused_sm(recv_pio, true);

    amiga_recv_pio_init(recv_pio, recv_sm, recv_offset, KBD_REAL_CLK, KBD_REAL_DAT);
}

/**
 * bring the receiver back to a known idle state. a kclk hold leaves a single
 * sampled bit stranded in the isr, so every frame after the hold would be
 * assembled from one stale bit plus seven new ones, permanently one bit out.
 * restarting discards the partial frame and realigns on the next byte - which is
 * only true if nothing is on the wire at the time, hence the idle check in
 * amiga_keyboard_recv_resync_task().
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
 * perform a resynchronisation armed by a reset, once it is safe to do so.
 */
static void amiga_keyboard_recv_resync_task(uint32_t now)
{
    if (!resync_pending)
        return;

    if ((uint32_t)(now - recv_last_active) < (KBDIN_RESYNC_IDLE_MS * 1000u))
        return;

    if (!pio_sm_is_rx_fifo_empty(recv_pio, recv_sm))
        return;

    resync_pending = false;
    amiga_keyboard_recv_restart();
    amiga_kbdin_restarted();
    ahprintf("[akb] real keyboard receiver resynchronised\n");
}

/**
 * watch kclk for the long low the keyboard uses to demand a hard reset.
 */
static void amiga_keyboard_recv_reset_task(void)
{
    uint32_t now = time_us_32();
    bool clk_low = gpio_get(KBD_REAL_CLK) == 0;
    bool continuous = (uint32_t)(now - clk_last_poll) <= (KBDIN_POLL_GAP_MAX_MS * 1000u);
    bool reset_active = amiga_in_reset();

    clk_last_poll = now;

    // every hard reset ends with the keyboard holding kclk low and restarting
    // itself, which strands a sampled bit in the state machine. arm the
    // resynchronisation on the assertion edge rather than on seeing the hold
    // end: whoever asserted, the hold can pass entirely inside the half second
    // amiga_assert_reset() blocks the main loop for.
    if (reset_active && !reset_was_active)
        resync_pending = true;
    reset_was_active = reset_active;

    if (clk_low)
        recv_last_active = now;

    if (!clk_low) {
        clk_was_low = false;
        clk_seen_idle = true;

        if (kbd_reset_held) {
            // keyboard has let go of kclk: bring the amiga back out of reset
            kbd_reset_held = false;
            kbd_reset_abandoned = false;
            amiga_kbdin_reset(false);
            ahprintf("[akb] real keyboard released reset\n");
        }

        amiga_keyboard_recv_resync_task(now);
        return;
    }

    if (kbd_reset_held) {
        if (kbd_reset_abandoned)
            return;

        // nothing legitimate holds the line down this long; let the amiga run
        // rather than leaving every input source muted behind a keyboard which
        // is never going to let go
        if ((uint32_t)(now - clk_low_since) >= (KBDIN_RESET_HOLD_MAX_MS * 1000u)) {
            kbd_reset_abandoned = true;
            amiga_kbdin_reset(false);
            ahprintf("[akb] kclk still low; giving up on the reset\n");
            return;
        }

        // re-offer the assert: it does nothing whilst another source owns the
        // reset, but takes it over the moment that source lets go, so the amiga
        // cannot come back up whilst the keyboard is still demanding a reset
        amiga_kbdin_reset(true);
        return;
    }

    if (!clk_was_low || !continuous) {
        clk_was_low = true;
        clk_low_since = now;
        return;
    }

    // a line that has been low ever since boot is an unconnected or unpowered
    // input, not a reset request; holding the amiga down forever over that would
    // be a poor failure mode, so wait until we have seen the bus idle once
    if (!clk_seen_idle)
        return;

    if ((uint32_t)(now - clk_low_since) < (KBDIN_RESET_HOLD_MS * 1000u))
        return;

    kbd_reset_held = true;
    ahprintf("[akb] real keyboard held kclk low; asserting reset\n");
    amiga_kbdin_reset(true);
}

void amiga_keyboard_recv_task(void)
{
    while (!pio_sm_is_rx_fifo_empty(recv_pio, recv_sm)) {
        uint32_t word = pio_sm_get(recv_pio, recv_sm);

        // the wire is busy; a resynchronisation has to wait for a gap
        recv_last_active = time_us_32();

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
