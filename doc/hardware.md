# hardware

## how do i attach this to my amiga?

### ux rev 1 (rev6) board: cables, no wiring

the ux rev 1 board has the amiga's own keyboard connectors on it. big-box amigas connect with
off-the-shelf **straight-through male-male** cables: din5 for the a2000, a3000 and a4000t,
mini-din6 (ps/2 style) for the a4000. the real keyboard plugs into the matching input socket
(j11/j12). controller ports use straight-through de9 female-female cables, not null-modem.
nothing below applies to it; see the [board guide](./ux-rev1.md). the rest of this page is
for the earlier header-based boards.

### a500

the standard board is designed to be mounted atop the amiga 500 keyboard header. mount a strip of eight 2.54mm pitch sockets with sufficient clearance from the nearby custom chips (cia, mostly). the drill holes are m3 - use some nylon supports to support the board and stop it flexing.

for other amigas, you will need to refer to your model's keyboard socket. instead of a socket on the underside, mount 2.54mm pitch idc pin strip to the top of the board and use dupont connections to attach to the amiga in your favoured manner. most amigas except for the a1000 (which uses an rj11 connector) use some form of din plug. the signalling is identical across the entire range.

the pcb has a key for signals; only kclk, kdat, power and ground are required. reset is not required for big-box amigas, which use clock to signal reset.

### a600/a1200

the amiga 600 and 1200 have a surface mounted keyboard mcu; until a design has been put together, you can tap kclk, kdat and reset from the chip (use an upturned plcc socket). find the pin information at [amigapcb.org](https://www.amigapcb.org/). please be **really** careful attaching to these machines.

attach these lines to the standard amigahid-pico header in the correct position.

### a1000/a2000/a3000/a4000/cdtv/cd32

the din socket (rj11 on the a1000) for these models should map the +5v, kclk and kdat. these models do not have a reset signal, instead they rely on holding kclk low for a period to signal the hard reset signal to the amiga.

map these pins to the corresponding signals on the a500 keyboard header on the amigahid-pico pcb.

## amiga 500 keyboard header

all signals are active low.

| pin# | signal | meaning  | notes |
|------|--------|----------|-------|
| 1    | kclk   | clock    |       |
| 2    | kdat   | data     |       |
| 3    | /res   | reset    | issues a hard reset |
| 4    | +5v    | 5v power |       |
| 5    | nc     | nc       | not connected (often physically absent) |
| 6    | gnd    | ground   | though if powering arduino/avr from psu, may be able to use that ground line |
| 7    | pwr    | power    | provides power to keyboard power led to indicate amiga is on/audio filter status |
| 8    | drv    | drive    | indicates floppy drive activity |

7 and 8 are not connected to the pico in any way, so you may want to investigate another way of indicating floppy drive and power status.

## what about controllers?

please see the silkscreen for the short-term connection notes. the wiring guide is detailed there for simplicity.

using 2.54mm pitch idc pin plug (female type), insert 9 strands of 1.25mm pitch ribbon cable, aligning to pin one of the connector (usually with a red stripe on the ribbon), pressing with a vise or suitable ribbon cabling tool. using a ribbon-type d-sub, align pin 1 of the ribbon to pin 1 of the d-sub, and complete the attachment using the vise/ribbon cabling tool.

whilst the idc header has an interleave meaning the ribbon is ordered incrementally (1-2-3-4-5-6-7-8-9), the d-sub ribbon ordering goes 1-6-2-7-3-8-4-9-5; this is compensated for by the board design.

if you have a r2 pcb, i'm very sorry, you'll need to read the silkscreen and build a custom attachment, likely from dupont pins. i would strongly suggest switching to r4 or later.

## real amiga keyboard input (controller port 2)

a firmware build with `-DPORT2_ROLE=KEYBOARD` (see [installation](./installation.md)) repurposes **controller port 2** as an input for a *physically attached* real amiga keyboard, instead of (future) joystick emulation. this lets a real amiga keyboard and the usb/bluetooth path (e.g. a kvm for remote use) drive the amiga at the same time, with no switch and no bus contention: keycodes from the real keyboard are decoded and merged into the same output queue the usb path feeds, so the amiga cannot tell them apart.

in this mode port 2 is wired to the **real keyboard, not to the amiga**. the amiga only ever sees its normal keyboard header (j1). the keyboard becomes another *input* to the pico:

```
real keyboard --kclk/kdat--> port 2 (j6) --> pico (pio receiver) --> shared key queue --> amiga keyboard header (j1) --> amiga
```

the pico plays the host role: the keyboard is the clock master and clocks out keycodes; the pico samples them on a pio state machine and drives the protocol handshake (kdat low ~85us per byte) back automatically. only two of port 2's lines are used:

* `h` (gpio26) -> **kclk** (keyboard clock, pico input only)
* `v` (gpio27) -> **kdat** (keyboard data, bidirectional: read, and driven low for the handshake)

these reuse the existing bss138 level shifters on port 2, so the board already provides the pull-ups (both 3v3 and +5v sides) — **the adapter is wires only, no extra resistors**.

### wiring the adapter (j6 -> real keyboard)

unlike a joystick/mouse you do **not** use the d-sub ribbon interleave here; wire j6 directly to the keyboard. j6 is the 2x5 idc "controller 2" header (pin 1 is marked on the silkscreen):

```
        +---------------+
  kdat  | (1) o   o (2) | b1
  kclk  | (3) o   o (4) | -
   vq   | (5) o   o (6) | gnd
   hq   | (7) o   o (8) | b2
   b3   | (9) o   o(10) | -
        +---------------+
```

| real keyboard (din-5) | amigahid-pico | gpio | notes |
|-----------------------|---------------|------|-------|
| kclk                  | j6 pin 3      | 26   | clock, pico reads it |
| kdat                  | j6 pin 1      | 27   | data, bidirectional |
| gnd                   | j6 pin 6      | -    | common ground (mandatory) |
| +5v                   | j1 pin 4      | -    | **not on j6** - tap the amiga keyboard header's +5v (or pico vbus) |
| /reset                | -             | -    | leave **unconnected**; ctrl-amiga-amiga is recognised from the key events |

all signals are active low / open collector, exactly as the amiga-facing side.

> **caution**
> * in keyboard mode j6 must go to the keyboard, **never to the amiga**. do not confuse j1 (amiga-facing keyboard output, the 1x8 header) with j6 (port 2).
> * the rp2040 is not 5v tolerant; this works only because port 2's signals pass through the on-board bss138 shifters. do not bypass them.
> * **meter the +5v and gnd pins on your keyboard's din-5 before connecting** - documented pinouts disagree and a reversed power pin will damage the keyboard's mcu. on big-box keyboards pin 1 is kclk, pin 2 is kdat, pin 3 is /reset (leave it unconnected).
