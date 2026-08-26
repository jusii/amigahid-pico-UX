# amigahid-pico rev6 — complete Mouser BOM (final-check copy)

Generated from the schematic's own sourcing fields (`board-rev6` @ `3d6f485`). Two ways to build:
**(A) JLC-assembled SMD** — everything in the "SMD" section is already pinned to in-stock LCSC parts and placed by JLCPCB; you then hand-solder only the "Hand-solder" section.
**(B) Full hand-build from Mouser** — order both sections.

Links are Mouser part-number searches (`mouser.fi/c/?q=…`) so they can't rot; each lands on the exact part or a one-result list.

## Hand-solder parts (needed in BOTH build routes)

| Ref | Part | Qty/board | Order | Mouser |
|---|---|---|---|---|
| U1 | Raspberry Pi Pico W (SC0918) — or Pico 2 W | 1 | 2 | [SC0918](https://www.mouser.fi/c/?q=SC0918) |
| P1, P2 | DE9 male, right-angle THT, **5.34 mm footprint family** — Power Dynamics PDI-09S-5 (per schematic). Flange screws bolt THROUGH the pcb: 2× 3.2 mm plated holes, 25 mm apart, 4.94 mm from edge; near pin row 7.78 mm from edge. | 2 | 3 | PDI-09S-5 via TME/Farnell; Mouser-verified equivalents being confirmed — see sourcing note. **CORRECTION: the 9.4 mm "European footprint" family (incl. L717SDE09P, Assmann A-DS 09, Triopak XYDB9RP94) does NOT fit this board — earlier revisions of this BOM were wrong.** |
| J9, J11 | DIN5 180° socket (A2000/A3000 kbd) — Kycon KCDX-5S-N | 2 | 3 | [KCDX-5S-N](https://www.mouser.fi/ProductDetail/Kycon/KCDX-5S-N) |
| J10, J12 | Mini-DIN6 / PS-2 socket (A4000 kbd) — Same Sky MD-60S | 2 | 3 | [MD-60S](https://www.mouser.fi/c/?q=MD-60S) (exactly MD-60S, not MD-60SM) |
| J4 | USB-A receptacle, RA THT — Molex 67643-3910 | 1 | 2 | [67643-3910](https://www.mouser.fi/c/?q=67643-3910) (67643-0910 = same land) |
| J13 | USB-C power-only 6P — GCT USB4135-GF-A | 1 | 2 | [USB4135-GF-A](https://www.mouser.fi/c/?q=USB4135-GF-A) (fallback: Farnell/TME) |
| J1, J8 | Pin header 1×8, 2.54 mm vertical | 2 | — | one 1×40 breakaway covers all headers: [M20-9994046](https://www.mouser.fi/c/?q=M20-9994046) ×1 |
| J2 | Pin header 1×6 | 1 | — | (from the same breakaway) |
| J3 | Pin header 1×4 | 1 | — | (from the same breakaway) |
| J7 | Pin header 1×3 | 1 | — | (from the same breakaway) |
| — | Female header 1×20, 2.54 mm (proto socketing of U1) | 2 | 2 | [M20-7822046](https://www.mouser.fi/c/?q=M20-7822046) or any 1×20 female |
| JP1 | Solder jumper — no part | — | — | — |
| F1 | **PLACEHOLDER — hand-fit after bench measurement.** Order all three: | 1 | 1+1+1 | [MF-MSMF035-2](https://www.mouser.fi/c/?q=MF-MSMF035-2) + [MF-MSMF050-2](https://www.mouser.fi/c/?q=MF-MSMF050-2) + [MF-MSMF075-2](https://www.mouser.fi/c/?q=MF-MSMF075-2) — same 1812 land |

## SMD parts (JLC-assembled in route A; order from Mouser only for hand-build route B)

| Ref | Part | Qty/board | Order | LCSC (JLC route) | Mouser equivalent |
|---|---|---|---|---|---|
| Q1–Q19 | BSS138 N-FET, SOT-23 | 19 | 25 | C78284 | [onsemi BSS138](https://www.mouser.fi/c/?q=BSS138%20onsemi) |
| R1–R38 | 10 kΩ 0603 1% | 38 | 100 | C25804 | [RC0603FR-0710KL](https://www.mouser.fi/c/?q=RC0603FR-0710KL) |
| R39, R40 | 1 kΩ 0603 | 2 | 10 | C21190 | [RC0603FR-071KL](https://www.mouser.fi/c/?q=RC0603FR-071KL) |
| R41, R42 | 4.7 kΩ 0603 (I²C pull-ups) | 2 | 10 | C23162 | [RC0603FR-074K7L](https://www.mouser.fi/c/?q=RC0603FR-074K7L) |
| R43, R44 | 5.1 kΩ 0603 (USB-C CC) | 2 | 10 | C23186 | [RC0603FR-075K1L](https://www.mouser.fi/c/?q=RC0603FR-075K1L) |
| R45 | 470 Ω 0603 (JP1 LED ballast) | 1 | 10 | C23179 | [RC0603FR-07470RL](https://www.mouser.fi/c/?q=RC0603FR-07470RL) |
| C1 | 220 µF 16 V SMD alu, D6.3×7.7 — Panasonic EEE-FK1C221XP | 1 | 2 | C128533 | [EEE-FK1C221XP](https://www.mouser.fi/c/?q=EEE-FK1C221XP) |
| C4 | 150 µF 16 V SMD alu, D6.3×7.7 — Panasonic EEE-FKC151XAP | 1 | 2 | C413656 | [EEE-FKC151XAP](https://www.mouser.fi/c/?q=EEE-FKC151XAP) (any FK-series 150 µF/16 V in 6.3×7.7 fits) |
| C2, C6 | 10 µF 0805 X5R ≥16 V | 2 | 10 | C15850 | [CL21A106KAYNNNE](https://www.mouser.fi/c/?q=CL21A106KAYNNNE) or equiv |
| C3, C5, C7 | 100 nF 0603 X7R 50 V | 3 | 10 | C14663 | [CL10B104KB8NNNC](https://www.mouser.fi/c/?q=CL10B104KB8NNNC) or equiv |
| D1, D2 | SS34 Schottky 3 A 40 V, SMA | 2 | 5 | C8678 | [SS34 (SMA)](https://www.mouser.fi/c/?q=SS34%20SMA) — any brand |
| D10–D30 | PESD5V0S1BA ESD clamp, SOD-323 | 21 | 30 | C19224 | [PESD5V0S1BA](https://www.mouser.fi/c/?q=PESD5V0S1BA) (Nexperia) |
| F2, F3 | Polyfuse 500 mA hold, 1812 — Bourns MF-MSMF050-2 | 2 | 4 | C17313 | [MF-MSMF050-2](https://www.mouser.fi/c/?q=MF-MSMF050-2) |
| LED1 | Red 0603 | 1 | 5 | C2286 | [LTST-C190KRKT](https://www.mouser.fi/c/?q=LTST-C190KRKT) or equiv red 0603 |
| LED2 | Yellow-green 0603, **Vf ≈ 2.0–2.2 V** (not blue/white-class InGaN) | 1 | 5 | C2289 (KT-0603YG) | [LTST-C190GKT](https://www.mouser.fi/c/?q=LTST-C190GKT) or equiv |
| U2 | USBLC6-2SC6 USB ESD array, SOT-23-6 | 1 | 2 | C7519 | [USBLC6-2SC6](https://www.mouser.fi/c/?q=USBLC6-2SC6) (ST) |

## Optional / accessories (not on the board)

- 0.96″ SSD1306 **or** 1.3″ SH1106 I²C OLED module, 4-pin (3V3/GND/SCL/SDA) — any vendor; firmware auto-detects at 0x3C (SH1106 needs `-DDISPLAY_CONTROLLER=DISPLAY_SH1106`)
- Cables: DB9 **straight-through** F-F ×2 (beware: most F-F serial cables are null-modem!); PS/2 male-male **6-wire** (A4000); DIN5 male-male **all-5-pins wired** (A2000/A3000 — beware MIDI cables that omit pin 1 = KCLK)
- M3 standoffs/screws ×4; micro-USB cable for flashing

## Notes for the final check

1. Every SMD line's LCSC part was stock-verified at pin time; the Mouser column is a functional equivalent, not necessarily the identical brand.
2. C4's exact Panasonic suffix is worth one look on the Mouser page (150 µF/16 V, case 6.3×7.7 mm is what matters).
3. F1 ships unfitted — bench measurement picks 035/050/075.
4. The DE9 rule for any substitution: **5.34 mm footprint family only** (flange holes through the pcb at 4.94 mm from edge, 25 mm centres; pin rows 7.78 mm from edge). Neither the 9.4 mm "European" family nor .318″/8.08 mm parts fit. F1's schematic draft value is 750 mA (MF-MSMF075-2) — it ships unfitted; final value chosen at bench (see doc/errata.md "first power").
5. Physical sample check against the footprints (DIN5, mini-DIN6, DE9 especially) remains the gate before ordering boards.
