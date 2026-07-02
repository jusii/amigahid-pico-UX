# amigahid-pico

**about this fork:** this fork adds support for attaching a *real amiga keyboard* to controller port 2 (build with `-DPORT2_ROLE=KEYBOARD`; see [installation](./doc/installation.md) and [hardware](./doc/hardware.md)). it is based on upstream [pr #44](https://github.com/borb/amigahid-pico/pull/44) (bluetooth support by stefan reinauer) — see that pr for details of the bluetooth work. tested configuration: rev 5 pcb, standard pico (non-w), `BOARD_HIDPICO_REV4` firmware target with `PORT2_ROLE=KEYBOARD`. the original project lives at [borb/amigahid-pico](https://github.com/borb/amigahid-pico).

## introduction

amigahid-pico uses the rp2040 microcontroller (e.g. the raspberry pi pico) in a carrier board to attach usb input devices to a standard amiga without the need for a usb stack on the amiga itself.

it currently supports keyboards and mice and provides connection via the internal keyboard connector, the rj11/din socket on big-box amigas, and via the controller ports.

**this project is very much a work in progress.**

## **important note**

* current kicad files are for the r5 pcb, which is mostly identical to r4. there is no separate r5 firmware target: build `BOARD_HIDPICO_REV4` (the default) — this fork has been built and tested on an r5 board with the rev 4 target. controller port 2 can now be used as an input for a real amiga keyboard via `-DPORT2_ROLE=KEYBOARD` (see the [hardware](./doc/hardware.md) guide for wiring).

* **always read the [errata](./doc/errata.md) section for the current pcb layout before deciding whether or not to build.**

![rev 5 pcb](./doc/images/board-rev-5.jpg)

## documentation

* [installation](./doc/installation.md)
* [hardware](./doc/hardware.md)
* [errors in revisions (errata)](./doc/errata.md)

## history

this project is a rewrite of the [amigahid](https://github.com/borb/amigahid) project to the rp2040 microcontroller.

originally, after the retirement of the arduino adk board and shortening availability of the max3421e "usb host shield" for arduino boards, the need for a cheap, easy and continually available replacement was sought.

at first, the uhs mini via a level shifter seemed ideal, but significant issues were found convincing it to work with a variety of arduino boards.

the rp2040 made sense as a target because it is widely available, has sufficient physical connections and is powerful enough to meet multiple needs.

## what is the latency of this?

i have not measured the latency, but the keyboard signals are sent out the moment they are received on the usb bus. the potential latency is likely fractionally longer than the amiga mcu but bear in mind the rp2040 is significantly faster than the standard amiga keyboard controller.

## roadmap

please see the issues tab on the [github repository](https://github.com/borb/amigahid-pico) for the current list of planned features. the tl;dr is:

normal:
* i<sup>2</sup>c display for config/status
* controller emulation
    * keyboard-based controller emulation (use udlr for directions?)
* flash memory-based configuration
* possible amiga-side control panel (using bidirectional controller port signals)
* rotary control simulation (for controlling gotek drives)

crazy talk:
* non-amiga support
* non-hidbp support
* analogue/paddle emulation
* fix some tinyusb issues (hotplug, timing-related instability)

## license

on the fence at the moment, but the current license choice is Eclipse Public License 2.0 (EPL-2.0).

## third party licenses

* µgui: this code contains 'µgui' by achim döbler; the license for this can be read at in the [display readme](./src/display/README.md)

## whuh... who?

nine <[nine@aphlor.org](mailto:nine@aphlor.org)>
