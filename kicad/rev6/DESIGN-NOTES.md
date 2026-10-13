# UX rev 1 (rev6) design notes

working notes made while the board was being designed, kept for reference. the short list of
things a builder actually needs is in [doc/errata.md](../../doc/errata.md); the board guide is
[doc/ux-rev1.md](../../doc/ux-rev1.md).

**module test points.** revision 4's downside above — carrier copper under the pico's
underside test points — is back in a worse form on any carrier that solders the module
flat: revision 6 originally ran two live 5v-side shifter traces (`cont1_v`, `cont1_v_lo`)
straight under tp6 (bootsel / qspi_ss) and tp5, with ground pour under tp4. those two
traces have been rerouted and an f.cu copper keep-out now voids the band at x 35.40-42.50,
y 47.76-49.76. that band is completely clear of copper and it covers tp4, tp5 and tp6 of a
pico w or a pico 2 w — the modules this board is for — plus tp5 and tp6 of a plain pico.

a plain pico's tp4 sits 1.5 mm further out again, at x 42.25-43.75, and `cont1_v` crosses
there: the channel west of the keep-out only has room for one crossing and `cont1_v_lo`
took it, while east of x 43.75 `cont2_b1_lo` closes the gap. so if you bodge a plain pico
in, put kapton over its test points, exactly as for revision 4.

**pico, pico w and pico 2 w share tp1/tp2/tp3.** measured against the land patterns kicad
ships: tp1 (0, -21), tp2 (+1, -24.3) and tp3 (-1, -24.3), plus all four usb shell pads, are
identical on all three modules; only tp4/tp5/tp6 shift by 1.5 mm. the usb tap through the
milled slot therefore works unchanged on a plain pico — the only thing a plain pico
actually loses is swd, because it has no mid-board debug pads for u1 pads 41/42/43.

**the de9 land is the .318in family now.** the land revision 6 started with fitted exactly
one part — power dynamics pdi-09s-5 — because its two boardlock holes sat on the same line
as the near pin row, which is a pdi trait rather than an industry one. that part is dead
and unobtainable, so p1/p2 were retargeted to the industry .318in / 8.08 mm family. the
pin coordinates did not move (every d-sub family shares them); what moved is the boardlock
holes, from the near pin row to midway between the two rows, 1.42 mm behind the near row,
and the south board edge, so the near row sits the family's 7.70 mm behind it. the board
is 100 x 82.76 mm as a result, 2.76 mm deeper than it was, and the pin drills opened
1.0 -> 1.1 mm for the 1.09 mm pin.

buy kycon k22x-e9p-n. norcomp 182-009-113r531, te 5747840-x, wurth 618009231221 and
amphenol l717 code 33e are the same land. **hole position against the pin rows is the only
discriminator that matters** — a datasheet quoting the right backset can still be the wrong
family, which is how the pdi land got picked in the first place. and this land is drawn
from datasheets, not measured off a sample: put a real connector on a printout before
ordering boards.

**f1 is a placeholder.** it carries no lcsc code on purpose: the 750 ma draft has to be
re-sized from a bench measurement of the full stack before the board is ordered, and it
must trip before the host's own fuse. do not let it go out as an assembled part.

**usb-a socket overhang.** j4's mating face now sits about 1.2 mm proud of the south board
edge — it was about 4 mm until the de9 retarget moved the edge 2.76 mm south past it
(revision 5 had it flush). it is retained by four 1.0 mm pins and two 2.3 mm shield legs,
the nearest of which is 9.1 mm back from the edge, so the socket is far better supported
than it was: a fillet of epoxy under the front is now belt-and-braces rather than
necessary. it still takes cable load through its pins, so a bead against the board edge is
cheap insurance if the port will be plugged and unplugged often.

**south edge cable clearance.** the usb-a opening has only 3.68 mm to each de9 flange. a
slim d-sub hood plus a normal usb plug fits; a full-size moulded hood plus a fat plug or a
usb stick does not. use slim hoods, or a short usb extension. the lateral gap is unchanged
by the de9 retarget; the usb plug now simply sits closer to the board edge, where the d-sub
hoods are at their narrowest.

**the oled plugs straight in, on two posts.** j3 is no longer a pin header next to the
pico: it is a 1x4 *female* socket at x 81.74-89.36, y 40.5, and the generic 0.96in ssd1306
module (27.5 x 27.8 mm pcb, holes 23.5 x 23.8 mm on 2.0 mm insets, 4-pin header centred on
the top-hole line) plugs down onto it with its glass facing up. the module then sits at
x 71.8-99.3, y 38.5-66.3, flush inside the east edge, and two m2 posts hold the other
edge: h1 (97.3, 40.5) and h2 (97.3, 64.3), 2.2 mm npth, no copper. the other two corners
have no post on purpose - the lower-left one lands on q18 and six of the port-2 nets, and
the upper-left one sits in the corridor the i2c pair had to cross - so the socket carries
the north edge and the posts the east edge; a 3 g module on a 1 mm fr4 plate needs nothing
more. post length = socket body + 2.54 mm (the module's own male header body): 11 mm for the
8.4 mm socket in hand (10.94 mm; the socket contacts absorb the difference). keep the posts at 8 mm or more regardless, because the pico's
micro-usb cable passes UNDER the module's west edge at up to ~7 mm.

the socket's pin order is the module's, GND VCC SCL SDA west to east, which is why j3's
pins 1 and 2 swapped nets (the old header was 3V3 GND SCL SDA); check your module's silk
before soldering the socket, a VCC-GND module wants the labels swapped back. the display
image's top is the header edge, i.e. north, towards the keyboard connectors; the firmware
inits with segment + com remap, two bytes flip it if the case wants it the other way.

moving j3 45 mm east cost real routing: the i2c pair leaves the pico through the lane the
redundant +3V3 f.cu loop used to occupy (the pull-ups and j7 are now fed from the west via a
via at the old j3 pad-1 spot and one link down to the pico-side +3V3), /swclk /swdio and
/cont1_b2_lo were lifted out of the socket's pad row and re-threaded north of it, and three
gnd stitch vias re-link pour patches the new lanes had walled off. the credit block moved to
the bottom silkscreen because the module covers where it was.

**power the keyboard connector first — but know that f1 ships empty.** the nineteen
high-side pull-ups tie every amiga-facing line to sys5v, and sys5v is fed only from the
keyboard connector (via f1 then d1) or the usb-c aux input (d2) — the de9 ports take no
power. cabling only the joystick ports to a running amiga leaves sys5v dead and drags all
fourteen port lines low through 10k, so the machine sees stuck directions and buttons
while the board looks simply dead. connect keyboard-connector or aux 5 v before the de9
cables. note the trap: until f1 is hand-fitted (see first power below), the
keyboard-connector leg is an OPEN CIRCUIT and only the aux input (or the pico's own usb)
powers the board.

**first power / bring-up order (f1 is unfitted by design).** f1's final value is a bench
decision (mf-msmf030/050/075 share the land), so a fresh board has an open fuse position
and the amiga/keyboard-connector 5 v leg is dead. do NOT begin by feeding bench 5 v into
the din-out/kbd 5 v pin — through the empty fuse it proves nothing on a perfectly good
board. instead:
1. assemble: bottom smd, then top smd, then tht connectors. leave f1 empty; fit f2/f3.
2. first power = bench supply into the usb-c aux (j13), current-limited to ~300 ma. the
   aux leg is unfused (j13 → d2 → sys5v), so the bench limit is the only protection — use
   a real bench supply, not a phone charger.
3. expect sys5v ≈ 4.5–4.6 v (one schottky drop) and, once u1 is fitted, +3v3 from the
   module. this exercises everything downstream of d1: f2/f3 legs, all pull-up rails.
4. ohm out the f1 leg by hand (kbd-connector 5 v pin ↔ f1 pad 1; f1 pad 2 ↔ d1 anode).
5. fit/flash the module (pc usb powers it via the module's own vbus→vsys schottky; safe
   alongside aux power — everything meets at diodes).
6. measure the full running stack's current draw at the aux input — that current is
   exactly what f1 will carry.
7. pick and hand-fit f1 (plan predicts 350–500 ma for the full stack; 750 ma is the
   draft value on the schematic), then re-test powered from the keyboard connector.
8. only then cable a real amiga.

**reflashing in a powered amiga.** u1 pad 30 (run) has no net and vsys is fed through
f1/d1, so plugging the pc usb cable does not reset the rp2040 while the amiga is powering
the board. unplug the keyboard-connector cable (and aux 5 v), then hold bootsel while
plugging usb. if that gets tiresome, pad 30 is a netless castellation with 0.79 mm of land
exposed outboard of the module edge — a reset button can be tacked between it and any
ground castellation after the fact.
