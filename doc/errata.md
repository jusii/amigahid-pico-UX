# errata

this project is still in the relatively early stages in terms of hardware design and i'm learning things like kicad as i go along. it's likely i'll make mistakes, so this section documents those mistakes.

## board revision 1

revision 1 was based around using the txs0108 bidirectional level shifter, which proved to be a mistake: whilst it worked for keyboard functionality, the voltage drop once connected to a controller port was so significant the amiga was held in reset. this would not have been an issue for big-box amigas as they have no dedicated reset line on the keyboard port, but it would have proved difficult for the amiga 500, 600 and 1200.

## board revision 2

revision 2 of the board was the first successful test. this will change in the near future as some quirks were discovered during assembly. the design was changed to be mosfet-centric using the bss138; this may change in future. long-term, i'd like to use an ic rather than a series of (at present) 17 mosfets, but i have not yet found a part which provides all of the desired features.

the pico is attached using castellated edges to pads on the surface. ensure the alignment is straight and flood the edges with solder, ensuring the solder makes contact with both the edge and the pad (check). buzz the attachment out with a multimeter to ensure it's worked and not shorted.

for the amiga 500, the keyboard connector can use 2.54mm pitch sockets on the seven pin header and attach directly to the motherboard, though for simplicity of placement you may want to use short dupont wires for attachment.

the programming & debug header provides serial wire debug and uart connections. you can program either via swdio or the usb port & bootsel button.

the four pin i<sup>2</sup>c header is suitable for the generally available ssd1306 displays to mount directly to, assuming the pin layout is identical. the display is not currently used but will be used in future versions.

attach a usb otg adapter to the pico's usb port. usb hubs are supported, but only at a single level. multiple mice and keyboards can be attached and used concurrently, allowing you to attach a keyboard for desk and one for remote usage (e.g. sofa).

the controller ports mapping will change after revision 2: the assumption was made that 2x5 pin idc connectors were wired the same way as d-sub 9-pin connectors, and this was wrong. the numerical wiring works 1-2-3-4-5-6-7-8-9 vs 1-6-2-7-3-8-4-9-5, making ribbon attachment difficult in revision 2. this will be changed in revision 3.

## board revision 3 (not in version control)

was a reworking of revision two but with the intention of being smaller and introducing a castellated edge for attaching to the usb test pads; this version was never put into version control and has the same idc numbering problem as revision 2.

## board revision 4

warning: don't build this version; it's just for testing.

sticking with the mosfet design, this version fixes the idc to d-sub pin wiring so a flat 1.27mm pitch can be used.

downside: there are vias beneath the pico's keepouts for the bootsel/ground/power test points. if your board manufacturer doesn't coat the vias with solder mask sufficiently then these could make contact with the test points. if this happens, either use some polyamide (kapton) tape or clear nail varnish to insulate the test points before mounting the pico.

erroneously, pin 30 (run) was attached as the horizontal/down line on the second controller port. as a result, h/down has been moved to 31, and v/up has been moved to 32 on revision 5.

## board revision 6 (not yet fabricated)

revision 6 is a pico w / pico 2 w board with real amiga keyboard input, two controller
ports and a usb-a host socket. the notes below are things to know before ordering or
building it, not mistakes found after the fact.

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
