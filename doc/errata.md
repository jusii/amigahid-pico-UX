# errata

## ux rev 1 (rev6) — fabricated, hand-built

the board as fabricated works. things to know before you build one:

* **slim micro-usb plug.** the pico's port sits under the oled's west edge and beside the
  module's own pins; a chunky overmoulded cable will not fit.
* **the image must match the module.** a pico w flashed with the pico 2 w image (or vice
  versa) is silent: no usb, no serial, no led. check the module before flashing.
* **only hand assembly has been tested.** the jlcpcb assembled variant (bom/cpl in `fab/`)
  has not been ordered or verified.
* **f1 ships unfitted.** the keyboard-connector 5 v leg is open until you pick a fuse from a
  bench measurement. first power goes in through the usb-c aux (j13), current-limited; see
  the board guide and [design notes](../kicad/rev6/DESIGN-NOTES.md) for the sequence.
* **d10–d30 are optional.** esd clamps on the amiga-facing lines; the board runs without them.
* **re-entering bootsel.** once flashed the pico's usb is a host. hold bootsel and short the
  RUN castellation to GND, or leave the board unpowered for 15 s.
* **south edge is tight.** 3.7 mm between each de9 and the usb-a: slim d-sub hoods, or a short
  usb extension.
* **jlcpcb may read the usb tap half-holes as castellation** and quote a surcharge. don't say
  "castellated" in the order remark; they are two plated holes on a slot.
* **j3 pin order is GND VCC SCL SDA.** check your oled module's silk before soldering the socket.
* **plain pico:** put kapton over its underside test points first (tp4 sits over copper).

the longer design reasoning lives in [kicad/rev6/DESIGN-NOTES.md](../kicad/rev6/DESIGN-NOTES.md).

## earlier upstream boards

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

