/**
 * this file is part of amigahid-pico, (c) 2021 just nine <nine@aphlor.org>
 * please locate the full source at https://github.com/borb/amigahid-pico
 *
 * released under the terms of the Eclipse Public License 2.0 (EPL-2.0).
 * please find the complete license text at https://spdx.org/licenses/EPL-2.0
 *
 * real amiga keyboard receive path (port 2 in PORT2_ROLE=KEYBOARD mode).
 */

#ifndef _PLATFORM_AMIGA_KEYBOARD_RECV_H
#define _PLATFORM_AMIGA_KEYBOARD_RECV_H

/**
 * @brief Set up the PIO receiver for a real amiga keyboard on port 2.
 *
 * Claims a PIO state machine that clocks in keycodes from a physically
 * attached amiga keyboard and drives the protocol handshake autonomously.
 * No-op unless built with PORT2_ROLE=KEYBOARD.
 */
void amiga_keyboard_recv_init(void);

/**
 * @brief Drain any received keycodes and inject them into the amiga output.
 *
 * Call from the main loop. Decodes bytes received from the real keyboard and
 * forwards decoded keys to the shared keyboard event queue (the same merge
 * point the USB/BT path feeds). No-op unless built with PORT2_ROLE=KEYBOARD.
 */
void amiga_keyboard_recv_task(void);

#endif // _PLATFORM_AMIGA_KEYBOARD_RECV_H
