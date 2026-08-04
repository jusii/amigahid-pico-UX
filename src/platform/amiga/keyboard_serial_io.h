/**
 * this file is part of amigahid-pico, (c) 2021 just nine <nine@aphlor.org>
 * please locate the full source at https://github.com/borb/amigahid-pico
 *
 * released under the terms of the Eclipse Public License 2.0 (EPL-2.0).
 * please find the complete license text at https://spdx.org/licenses/EPL-2.0
 *
 * amiga keyboard serial interface.
 */

#ifndef _PLATFORM_AMIGA_KEYBOARD_SERIAL_IO_H
#define _PLATFORM_AMIGA_KEYBOARD_SERIAL_IO_H

#include <stdint.h>
#include <stdbool.h>

#include "class/hid/hid.h"

/**
 * @brief Setup Amiga keyboard communication
 *
 * Starts clocks, sets up ISRs and sends init codes to the host
 */
void amiga_init();

/**
 * @brief Get the caps lock status
 *
 * @return true     Caps lock is on
 * @return false    Caps lock is off
 */
bool amiga_caps_lock();

/**
 * @brief Send a HID keycode to the Amiga, translating along the way
 *
 * @param hidcode   HID keycode to send
 * @param up        true if key release, false if press
 */
void amiga_hid_send(uint8_t hidcode, bool up);

/**
 * @brief Send a modifier keycode to the Amiga, translating along the way
 *
 * @param modifier  Modifier being sent
 * @param up        Up or down? true if release, false if press
 */
void amiga_hid_modifier(hid_keyboard_modifier_bm_t modifier, bool up);

/**
 * @brief Queue a keycode for transmission to the Amiga
 *
 * @param keycode   Keycode to send to the host
 * @param up        Boolean press status; if true, code is & 0x80 before rol
 */
void amiga_send(uint8_t keycode, bool up);

/**
 * @brief Inject an Amiga keycode received from a real Amiga keyboard
 *
 * Shares the output queue with the USB/BT path (the merge point) but handles
 * the stateful concerns differently: a real keyboard already toggles caps lock
 * natively (down to engage, up to disengage) and tracks its own ctrl-amiga-amiga
 * reset combo independently of the USB source.
 *
 * @param keycode   Amiga keycode (0x00-0x7f), already decoded from the wire
 * @param up        true if key release, false if press
 */
void amiga_send_rawkey(uint8_t keycode, bool up);

/**
 * @brief Is the Amiga currently being held in reset?
 *
 * True whilst any source owns the reset: a ctrl-amiga-amiga from USB, Bluetooth
 * or the real keyboard, a hold forwarded by amiga_kbdin_reset(), or a reset the
 * Amiga asserted itself. Keycodes are discarded whilst this is true.
 *
 * @return true     A reset is in progress
 * @return false    Normal operation
 */
bool amiga_in_reset(void);

/**
 * @brief Note that the real keyboard's receiver has been resynchronised
 *
 * Called once per reset, after keyboard_recv.c restarts its state machine. The
 * keyboard resets its own mcu when it demands a hard reset, and the restart
 * discards whatever was mid-flight, so the real keyboard's tracked key state is
 * dropped here. A ctrl-amiga-amiga held from that keyboard is released too: the
 * up codes which would otherwise end it are never going to arrive.
 */
void amiga_kbdin_restarted(void);

/**
 * @brief Forward a hard reset demanded by a real Amiga keyboard
 *
 * A real keyboard asks for a hard reset by holding its clock line low for at
 * least 500ms; on big-box machines that is the only reset signalling there is,
 * so keyboard_recv.c watches for the hold and calls this. Drives exactly what a
 * held ctrl-amiga-amiga drives (/rst low plus the outgoing clock held low, which
 * covers A500-style and big-box targets alike) but owns its reset separately, so
 * neither this nor the combo path can release the other's.
 *
 * Idempotent: asserting whilst any reset is already in progress does nothing,
 * and releasing does nothing unless this path is the one holding it. The caller
 * therefore keeps offering the assert for as long as the clock line is held, so
 * that ownership transfers if the other source releases first.
 *
 * @param asserted  true to hold the Amiga in reset, false to release it
 */
void amiga_kbdin_reset(bool asserted);

/**
 * @brief Assert the reset signal - Amiga will hold in reset until released
 */
void amiga_assert_reset();

/**
 * @brief Release reset signal - Amiga will initiate startup once released
 */
void amiga_release_reset();

/**
 * @brief Regular jobs to run whilst passing through the event check loop;
 *        keep host maintained so that it believes a keyboard is still
 *        attached
 */
void amiga_service();

#endif // _PLATFORM_AMIGA_KEYBOARD_SERIAL_IO_H
