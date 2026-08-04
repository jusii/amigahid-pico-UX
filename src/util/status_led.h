/**
 * this file is part of amigahid-pico, (c) 2021 just nine <nine@aphlor.org>
 * please locate the full source at https://github.com/borb/amigahid-pico
 *
 * released under the terms of the Eclipse Public License 2.0 (EPL-2.0).
 * please find the complete license text at https://spdx.org/licenses/EPL-2.0
 *
 * status led indicators (boards with HAS_STATUS_LEDS).
 *
 * two leds tell you what the adapter is doing without a serial console or an
 * oled attached: led 1 is "am i usable" (heartbeat whilst nothing is attached,
 * solid once a usb or bluetooth device has mounted) and led 2 is "am i doing
 * something" (a short flash per input event forwarded to the amiga, replaced by
 * a fast blink whilst bluetooth is asking for a passkey).
 *
 * every entry point here is core0-only: the call sites are the hid callbacks,
 * the bluetooth state changes and the main loop. core1 runs the quadrature
 * mouse output loop and must not call into this module.
 *
 * core0 is not the same as "never concurrent", though. pico_cyw43_arch_none
 * builds btstack on the threadsafe-background async context, so the bluetooth
 * call sites run from an interrupt handler which can preempt status_led_task()
 * mid-update - the same reason bt_hid.c posts hid reports to a queue instead of
 * bridging them inline. the setters therefore only latch single words and the
 * task alone drives the pins, so the worst a preemption can do is paint one
 * stale led frame which the next pass corrects. anything added here which
 * accumulates across calls, or touches a pin from a setter, needs real mutual
 * exclusion first.
 */

#ifndef _UTIL_STATUS_LED_H
#define _UTIL_STATUS_LED_H

#include <stdbool.h>

#include "config.h"

/**
 * @brief Input transports which can satisfy the "hid source present" indicator.
 *
 * Each transport reports its own state and the module ors them together, so
 * the indicator describes whether anything usable is attached at all.
 */
typedef enum
{
    STATUS_LED_SOURCE_USB = 0,
    STATUS_LED_SOURCE_BT,
    STATUS_LED_SOURCE_COUNT
} status_led_source_t;

#ifdef HAS_STATUS_LEDS

/**
 * @brief Claim and blank the status led pins.
 */
void status_led_init(void);

/**
 * @brief Advance the led state machines.
 *
 * Call from the main loop. Non-blocking and allocation-free; all timing is
 * derived from the millisecond clock, so calling it more often only makes the
 * indicators more responsive.
 */
void status_led_task(void);

/**
 * @brief Report whether a transport currently has a usable device attached.
 *
 * @param source    Transport reporting its state
 * @param present   true if that transport has at least one device mounted
 */
void status_led_source(status_led_source_t source, bool present);

/**
 * @brief Flash the activity led; one call per input event sent to the amiga.
 */
void status_led_activity(void);

/**
 * @brief Report whether bluetooth is waiting on a pairing/passkey confirmation.
 *
 * @param active    true whilst a passkey or pin prompt is on display
 */
void status_led_pairing(bool active);

#else // !HAS_STATUS_LEDS

// boards without status leds compile the call sites away entirely
static inline void status_led_init(void) {}
static inline void status_led_task(void) {}
static inline void status_led_source(status_led_source_t source, bool present) { (void)source; (void)present; }
static inline void status_led_activity(void) {}
static inline void status_led_pairing(bool active) { (void)active; }

#endif // HAS_STATUS_LEDS

#endif // _UTIL_STATUS_LED_H
