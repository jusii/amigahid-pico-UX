/**
 * this file is part of amigahid-pico, (c) 2021 just nine <nine@aphlor.org>
 * please locate the full source at https://github.com/borb/amigahid-pico
 *
 * released under the terms of the Eclipse Public License 2.0 (EPL-2.0).
 * please find the complete license text at https://spdx.org/licenses/EPL-2.0
 *
 * status led indicators.
 */

#include "config.h"
#include "util/status_led.h"

#ifdef HAS_STATUS_LEDS

#include <stdbool.h>
#include <stdint.h>

#include "pico/stdlib.h"
#include "hardware/gpio.h"

// the leds sit on the 3v3 side behind a series resistor, so a high output
// lights them
#define STATUS_LED_ON   1
#define STATUS_LED_OFF  0

// led 1: half-period of the "nothing attached yet" heartbeat
#define STATUS_LED_HEARTBEAT_MS 500

// led 2: how long one forwarded input event lights the activity led. short
// enough that a burst of key events still reads as a flicker rather than a
// solid lamp, long enough to be visible at all
#define STATUS_LED_ACTIVITY_MS  40

// led 2: half-period of the pairing blink, deliberately faster than the
// heartbeat so the two cannot be confused
#define STATUS_LED_PAIRING_MS   120

static bool source_present[STATUS_LED_SOURCE_COUNT];

static uint32_t heartbeat_since;
static bool heartbeat_lit;

static bool activity_pending;
static uint32_t activity_since;

static bool pairing_active;
static uint32_t pairing_since;
static bool pairing_lit;

static inline bool status_led_any_source(void)
{
    for (uint8_t source = 0; source < STATUS_LED_SOURCE_COUNT; source++)
        if (source_present[source])
            return true;

    return false;
}

void status_led_init(void)
{
    gpio_init(LED_STATUS1);
    gpio_set_dir(LED_STATUS1, GPIO_OUT);
    gpio_put(LED_STATUS1, STATUS_LED_OFF);

    gpio_init(LED_STATUS2);
    gpio_set_dir(LED_STATUS2, GPIO_OUT);
    gpio_put(LED_STATUS2, STATUS_LED_OFF);

    heartbeat_since = to_ms_since_boot(get_absolute_time());
    pairing_since = heartbeat_since;
}

void status_led_source(status_led_source_t source, bool present)
{
    if (source >= STATUS_LED_SOURCE_COUNT)
        return;

    source_present[source] = present;
}

void status_led_activity(void)
{
    // just latch the time; the task owns the pins so that a pairing prompt can
    // take the activity led over without the two fighting for it
    activity_since = to_ms_since_boot(get_absolute_time());
    activity_pending = true;
}

void status_led_pairing(bool active)
{
    // the prompt is (re)painted by several bluetooth paths; only a change of
    // state restarts the blink, or it would never leave its first half-period
    if (pairing_active == active)
        return;

    pairing_active = active;
    pairing_since = to_ms_since_boot(get_absolute_time());
    pairing_lit = active;
}

/**
 * led 1: solid once anything is attached, heartbeat until then.
 */
static void status_led_source_task(uint32_t now)
{
    if (status_led_any_source()) {
        heartbeat_lit = true;
        heartbeat_since = now;
        gpio_put(LED_STATUS1, STATUS_LED_ON);
        return;
    }

    if ((uint32_t)(now - heartbeat_since) >= STATUS_LED_HEARTBEAT_MS) {
        heartbeat_since = now;
        heartbeat_lit = !heartbeat_lit;
    }

    gpio_put(LED_STATUS1, heartbeat_lit ? STATUS_LED_ON : STATUS_LED_OFF);
}

/**
 * led 2: activity flashes, overridden by the pairing blink.
 */
static void status_led_activity_task(uint32_t now)
{
    if (pairing_active) {
        if ((uint32_t)(now - pairing_since) >= STATUS_LED_PAIRING_MS) {
            pairing_since = now;
            pairing_lit = !pairing_lit;
        }

        gpio_put(LED_STATUS2, pairing_lit ? STATUS_LED_ON : STATUS_LED_OFF);
        return;
    }

    if (activity_pending && ((uint32_t)(now - activity_since) >= STATUS_LED_ACTIVITY_MS))
        activity_pending = false;

    gpio_put(LED_STATUS2, activity_pending ? STATUS_LED_ON : STATUS_LED_OFF);
}

void status_led_task(void)
{
    uint32_t now = to_ms_since_boot(get_absolute_time());

    status_led_source_task(now);
    status_led_activity_task(now);
}

#endif // HAS_STATUS_LEDS
