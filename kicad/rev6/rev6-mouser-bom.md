# amigahid-pico rev6 — complete Mouser BOM (final-check copy)

Generated from the schematic's own sourcing fields (`board-rev6` @ `700f727`). Two ways to build:
**(A) JLC-assembled SMD** — everything in the "SMD" section is already pinned to in-stock LCSC parts and placed by JLCPCB; you then hand-solder only the "Hand-solder" section.
**(B) Full hand-build from Mouser** — order both sections.

Links are Mouser part-number searches (`mouser.fi/c/?q=…`) so they can't rot; each lands on the exact part or a one-result list.

## Hand-solder parts (needed in BOTH build routes)

| Ref | Part | Qty/board | Order | Mouser |
|---|---|---|---|---|
| U1 | Raspberry Pi Pico W (SC0918) — or Pico 2 W | 1 | 2 | [SC0918](https://www.mouser.fi/en/c/?q=SC0918) |
| P1, P2 | DE9 male, right-angle THT, **.318″ / 8.08 mm footprint family** — Kycon K22X-E9P-N (per schematic). Boardlock screws bolt THROUGH the pcb: 2× 3.2 mm plated holes, 25 mm apart, sitting **midway between the two pin rows**, 1.42 mm behind the near row; near pin row 7.70 mm from edge; pin holes 1.1 mm. | 2 | 3 | [K22X-E9P-N](https://www.mouser.fi/en/c/?q=K22X-E9P-N) — Mouser 806-K22X-E9P-N. Digi-Key FI fallback: 9990172, ~€1.79, deep stock. Same land: NorComp 182-009-113R531, TE 5747840-x, Würth 618009231221, Amphenol L717 code 33E. **The discriminator is where the boardlock holes sit relative to the pin rows — not the backset on its own.** |
| J9, J11 | DIN5 180° socket (A2000/A3000 kbd) — Kycon KCDX-5S-N | 2 | 3 | [KCDX-5S-N](https://www.mouser.fi/en/ProductDetail/Kycon/KCDX-5S-N) |
| J10, J12 | Mini-DIN6 / PS-2 socket (A4000 kbd) — Same Sky MD-60S | 2 | 3 | [MD-60S](https://www.mouser.fi/en/c/?q=MD-60S) (exactly MD-60S, not MD-60SM) |
| J4 | USB-A receptacle, RA THT — Molex 67643-3910 | 1 | 2 | [67643-3910](https://www.mouser.fi/en/c/?q=67643-3910) (67643-0910 = same land) |
| J13 | USB-C power-only 6P — GCT USB4135-GF-A | 1 | 2 | [USB4135-GF-A](https://www.mouser.fi/en/c/?q=USB4135-GF-A) (fallback: Farnell/TME) |
| J1, J8 | Pin header 1×8, 2.54 mm vertical | 2 | — | one 1×40 breakaway covers all headers: [M20-9994046](https://www.mouser.fi/en/c/?q=M20-9994046) ×1 |
| J2 | Pin header 1×6 | 1 | — | (from the same breakaway) |
| J3 | **Pin socket 1×4 female** (8.4 mm body — the standard height, in hand; the 0.96″ OLED plugs straight in, pin order GND·VCC·SCL·SDA) | 1 | 2 | [PPTC041LFBN-RC](https://www.mouser.fi/en/c/?q=PPTC041LFBN-RC) (Sullins, 8.5 mm) — any 2.54 mm 1×4 female header of the same height; taller only if the posts follow |
| J7 | Pin header 1×3 | 1 | — | (from the same breakaway) |
| — | Female header 1×20, 2.54 mm (proto socketing of U1) | 2 | 2 | [M20-7822046](https://www.mouser.fi/en/c/?q=M20-7822046) or any 1×20 female |
| JP1 | Solder jumper — no part | — | — | — |
| F1 | **PLACEHOLDER — hand-fit after bench measurement.** Order all three: | 1 | 1+1+1 | [MF-MSMF030-2](https://www.mouser.fi/en/c/?q=MF-MSMF030-2) + [MF-MSMF050-2](https://www.mouser.fi/en/c/?q=MF-MSMF050-2) + [MF-MSMF075-2](https://www.mouser.fi/en/c/?q=MF-MSMF075-2) — same 1812 land |

## SMD parts (JLC-assembled in route A; order from Mouser only for hand-build route B)

| Ref | Part | Qty/board | Order | LCSC (JLC route) | Mouser equivalent |
|---|---|---|---|---|---|
| Q1–Q19 | BSS138 N-FET, SOT-23 | 19 | 25 | C78284 | [onsemi BSS138](https://www.mouser.fi/en/c/?q=BSS138%20onsemi) |
| R1–R38 | 10 kΩ 0603 1% | 38 | 100 | C25804 | [RC0603FR-0710KL](https://www.mouser.fi/en/c/?q=RC0603FR-0710KL) |
| R39, R40 | 1 kΩ 0603 | 2 | 10 | C21190 | [RC0603FR-071KL](https://www.mouser.fi/en/c/?q=RC0603FR-071KL) |
| R41, R42 | 4.7 kΩ 0603 (I²C pull-ups) | 2 | 10 | C23162 | [RC0603FR-074K7L](https://www.mouser.fi/en/c/?q=RC0603FR-074K7L) |
| R43, R44 | 5.1 kΩ 0603 (USB-C CC) | 2 | 10 | C23186 | [ERJ-3EKF5101V](https://www.mouser.fi/en/c/?q=ERJ-3EKF5101V) (Panasonic) |
| R45 | 470 Ω 0603 (JP1 LED ballast) | 1 | 10 | C23179 | [RC0603FR-07470RL](https://www.mouser.fi/en/c/?q=RC0603FR-07470RL) |
| C1 | 220 µF 16 V SMD alu, D6.3×7.7 — Panasonic EEE-FK1C221XP | 1 | 2 | C128533 | [EEE-FK1C221XP](https://www.mouser.fi/en/c/?q=EEE-FK1C221XP) |
| C4 | 150 µF 16 V SMD alu, D6.3×7.7 — Panasonic EEE-FKC151XAP | 1 | 2 | C413656 | [EEE-FKC151XAP](https://www.mouser.fi/en/c/?q=EEE-FKC151XAP) (any FK-series 150 µF/16 V in 6.3×7.7 fits) |
| C2, C6 | 10 µF 0805 X5R ≥16 V | 2 | 10 | C15850 | [C2012X5R1V106K0C](https://www.mouser.fi/en/c/?q=C2012X5R1V106K0C) or equiv |
| C3, C5, C7 | 100 nF 0603 X7R 50 V | 3 | 10 | C14663 | [C0603C104K5RACTU](https://www.mouser.fi/en/c/?q=C0603C104K5RACTU) or equiv |
| D1, D2 | SS34 Schottky 3 A 40 V, SMA | 2 | 5 | C8678 | [B340A-13-F](https://www.mouser.fi/en/c/?q=B340A-13-F) (Diodes Inc) or any SS34-class 3A/40V SMA |
| D10–D30 | PESD5V0S1BA ESD clamp, SOD-323 | 21 | 30 | C19224 | [CDSOD323-T05C](https://www.mouser.fi/en/c/?q=CDSOD323-T05C) (Bourns; or Nexperia PESD5V0S1BA ,135 packing if stocked) |
| F2, F3 | Polyfuse 500 mA hold, 1812 — Bourns MF-MSMF050-2 | 2 | 4 | C17313 | [MF-MSMF050-2](https://www.mouser.fi/en/c/?q=MF-MSMF050-2) |
| LED1 | Red 0603 | 1 | 5 | C2286 | [LTST-C190KRKT](https://www.mouser.fi/en/c/?q=LTST-C190KRKT) or equiv red 0603 |
| LED2 | Yellow-green 0603, **Vf ≈ 2.0–2.2 V** (not blue/white-class InGaN) | 1 | 5 | C2289 (KT-0603YG) | [LTST-C190GKT](https://www.mouser.fi/en/c/?q=LTST-C190GKT) or equiv |
| U2 | USBLC6-2SC6 USB ESD array, SOT-23-6 | 1 | 2 | C7519 | [USBLC6-2SC6](https://www.mouser.fi/en/c/?q=USBLC6-2SC6) (ST) |

## Optional / accessories (not on the board)

- 0.96″ SSD1306 I²C OLED module, 4-pin **GND·VCC·SCL·SDA**, 27.5 × 27.8 mm PCB with 23.5 × 23.8 mm hole spacing — the socket and posts are laid out for exactly this module (a VCC·GND module needs J3's pins 1/2 swapped back; a 1.3″ SH1106 still works electrically but does not fit the posts); firmware auto-detects at 0x3C (SH1106 needs `-DDISPLAY_CONTROLLER=DISPLAY_SH1106`)
- Cables: DB9 **straight-through** F-F ×2 (beware: most F-F serial cables are null-modem!); PS/2 male-male **6-wire** (A4000); DIN5 male-male **all-5-pins wired** (A2000/A3000 — beware MIDI cables that omit pin 1 = KCLK)
- M3 standoffs/screws ×4; micro-USB cable for flashing
- **OLED posts:** M2 × 11 mm standoffs ×2 (= socket body 8.4 + module header body 2.54 = 10.94) with M2 screws/nuts, for H1/H2 (Ø2.2 NPTH at (97.3, 40.5) and (97.3, 64.3)); ≥ 8 mm whatever the socket, the Pico's micro-USB cable runs under the module's west edge

## BOM audit 2026-10-13

Cross-checked against the board file (115 placed footprints; H1/H2 are bare holes): every reference designator is covered by exactly one line of `rev6-mouser-bom.csv`, and every purchasable line is in `rev6-ux-mouser-cart.csv`. JP1 is a solder bridge, no part. Fixed in this pass: the cart lacked J3's female socket and still described J3 as part of the header breakaway; the csv carried older part numbers for C2/C6, C3/C5/C7, R43/R44, D1/D2 and D10–D30 than the cart actually ordered. The cart now carries spares on the hand-soldered small SMDs (BSS138 25, 10 k 45, other 0603s 5, ESD 25, SMA 3, LEDs 3) — one dropped 0603 should not stall a build.

Not on Mouser and not in the cart: the 0.96″ OLED module, M2 × 11 mm posts + M2 screws/nuts ×2, M3 standoffs ×4, cables.

## Notes for the final check

1. Every SMD line's LCSC part was stock-verified at pin time; the Mouser column is a functional equivalent, not necessarily the identical brand.
2. C4's exact Panasonic suffix is worth one look on the Mouser page (150 µF/16 V, case 6.3×7.7 mm is what matters).
3. F1 ships unfitted — bench measurement picks 035/050/075.
4. The DE9 rule for any substitution: **.318″ / 8.08 mm footprint family only** — the two 3.2 mm boardlock holes must sit midway between the pin rows (1.42 mm behind the near row) on 25 mm centres, with the near pin row 7.70 mm from the board edge. Neither the 5.34 mm family (Power Dynamics PDI-09S-5, which the land targeted until the rev6 retarget, and which is discontinued) nor the 9.4 mm "European" family (L717SDE09P, Assmann A-DS 09, Triopak XYDB9RP94) fits. Judge a candidate by the hole position against the pin rows, never by the backset alone — that is exactly how the dead PDI part got picked. F1's schematic draft value is 750 mA (MF-MSMF075-2) — it ships unfitted; final value chosen at bench (see doc/errata.md "first power").
5. Any Triopak RP94-series DE9s already on the shelf are the 9.4 mm European family: **keep them as spares, do not fit them**.
6. Physical sample check against the footprints (DIN5, mini-DIN6, DE9 especially) remains the gate before ordering boards.
