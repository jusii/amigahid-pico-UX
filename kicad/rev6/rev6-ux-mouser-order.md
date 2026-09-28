# hid-pico Amiga UX — Mouser order list (hand-solder build, exact links)

One order covers everything on the board. Links are exact Mouser product pages (host-swapped to mouser.fi — Mouser shares product paths across regions). ✔ = link path confirmed via distributor/search cross-check; (p) = canonical pattern link, paste the MPN into Mouser search if it 404s. Mouser blocks robots, so no live stock numbers here — check stock as you order.

## Connectors (the main event)

| Ref | Part | Buy | Link |
|---|---|---|---|
| P1, P2 | **DE9 male — Kycon K22X-E9P-N** (.318″ family; board is being retargeted to it) | 3 | ✔ [mouser.fi/en/ProductDetail/Kycon/K22X-E9P-N](https://www.mouser.fi/en/ProductDetail/Kycon/K22X-E9P-N) — Mouser # 806-K22X-E9P-N. Alt: NorComp 182-009-113R531, TE 5747840-x, Würth 618009231221. **Do NOT buy the 9.4 mm "European" or any part chosen on backset alone — hole position vs pin rows is the discriminator.** |
| J9, J11 | **DIN5 socket — Kycon KCDX-5S-N** (A2000/A3000 keyboard) | 3 | ✔ [mouser.fi/en/ProductDetail/Kycon/KCDX-5S-N](https://www.mouser.fi/en/ProductDetail/Kycon/KCDX-5S-N) |
| J10, J12 | **Mini-DIN6 / PS-2 socket — Same Sky MD-60S** (A4000 keyboard) | 3 | ✔ [mouser.fi/en/ProductDetail/Same-Sky/MD-60S](https://www.mouser.fi/en/ProductDetail/Same-Sky/MD-60S) — exactly **MD-60S** (not SM/SV/SP variants) |
| J4 | **USB-A host — Molex 67643-3910** | 2 | ✔ [mouser.fi/en/ProductDetail/Molex/67643-3910](https://www.mouser.fi/en/ProductDetail/Molex/67643-3910) (67643-0910 = same land if out of stock) |
| J13 | **USB-C aux 5V — GCT USB4135-GF-A** (power-only, 6P) | 2 | ✔ [mouser.fi/en/ProductDetail/GCT/USB4135-GF-A](https://www.mouser.fi/en/ProductDetail/GCT/USB4135-GF-A) |
| U1 | **Raspberry Pi Pico W (SC0918)** — and/or Pico 2 W (SC1633) | 1+1 | ✔ [mouser.fi/en/ProductDetail/Raspberry-Pi/SC0918](https://www.mouser.fi/en/ProductDetail/Raspberry-Pi/SC0918) · ✔ [SC1633](https://www.mouser.fi/en/ProductDetail/Raspberry-Pi/SC1633) |
| J1,J2,J7,J8 | **Pin headers** — one 1×40 breakaway covers 8+8+6+3 | 1 | ✔ [mouser.fi/en/ProductDetail/Harwin/M20-9994046](https://www.mouser.fi/en/ProductDetail/Harwin/M20-9994046) (any 2.54 mm 1×40 breakaway works) |
| J3 | **OLED socket** — 1×4 female, 8.4 mm body (in hand); the 0.96″ module plugs straight in | 2 | (p) [mouser.fi/en/ProductDetail/Sullins/PPTC041LFBN-RC](https://www.mouser.fi/en/ProductDetail/Sullins/PPTC041LFBN-RC) — any 2.54 mm 1×4 female header; the posts are sized for 8.5 mm |
| (proto) | **Female headers 1×20** ×2 — socketing the Pico W | 2 | (p) [mouser.fi/en/ProductDetail/Harwin/M20-7822046](https://www.mouser.fi/en/ProductDetail/Harwin/M20-7822046) — or any 2.54 mm 1×20 female strip |

## SMD (you hand-solder these too)

| Ref | Part | Buy | Link |
|---|---|---|---|
| Q1–Q19 | BSS138, SOT-23 | 25 | ✔ [mouser.fi/en/ProductDetail/onsemi/BSS138](https://www.mouser.fi/en/ProductDetail/onsemi/BSS138) — Mouser # 512-BSS138 |
| R1–R38 | 10 kΩ 0603 1% — Yageo RC0603FR-0710KL | 100 | (p) [mouser.fi/en/ProductDetail/YAGEO/RC0603FR-0710KL](https://www.mouser.fi/en/ProductDetail/YAGEO/RC0603FR-0710KL) |
| R39,R40 | 1 kΩ 0603 — RC0603FR-071KL | 10 | (p) [link](https://www.mouser.fi/en/ProductDetail/YAGEO/RC0603FR-071KL) |
| R41,R42 | 4.7 kΩ 0603 — RC0603FR-074K7L | 10 | (p) [link](https://www.mouser.fi/en/ProductDetail/YAGEO/RC0603FR-074K7L) |
| R43,R44 | 5.1 kΩ 0603 — Panasonic ERJ-3EKF5101V | 10 | (p) [link](https://www.mouser.fi/en/ProductDetail/Panasonic/ERJ-3EKF5101V) |
| R45 | 470 Ω 0603 — RC0603FR-07470RL | 10 | (p) [link](https://www.mouser.fi/en/ProductDetail/YAGEO/RC0603FR-07470RL) |
| C1 | 220 µF 16 V alu SMD 6.3×7.7 — Panasonic EEE-FK1C221XP | 2 | (p) [link](https://www.mouser.fi/en/ProductDetail/Panasonic/EEE-FK1C221XP) |
| C4 | 150 µF 16 V alu SMD 6.3×7.7 — Panasonic EEE-FKC151XAP | 2 | (p) [link](https://www.mouser.fi/en/ProductDetail/Panasonic/EEE-FKC151XAP) — any FK 150 µF/16 V in 6.3×7.7 fits |
| C2,C6 | 10 µF 0805 X5R — TDK C2012X5R1V106K0C | 10 | (p) [link](https://www.mouser.fi/en/ProductDetail/TDK/C2012X5R1V106K0C) |
| C3,C5,C7 | 100 nF 0603 X7R — KEMET C0603C104K5RACTU | 10 | (p) [link](https://www.mouser.fi/en/ProductDetail/KEMET/C0603C104K5RACTU) |
| D1,D2 | SS34 Schottky 3 A 40 V, SMA — any brand | 5 | [B340A-13-F](https://www.mouser.fi/en/c/?q=B340A-13-F) (Diodes Inc, SS34 equivalent; any SS34-class 3A/40V SMA works) |
| D10–D30 | PESD5V0S1BA, SOD-323 — Nexperia | 30 | [CDSOD323-T05C](https://www.mouser.fi/en/c/?q=CDSOD323-T05C) (Bourns, 5V bidirectional SOD-323; or Nexperia PESD5V0S1BA `,135` packing if stocked) |
| F2,F3 | Polyfuse 500 mA 1812 — Bourns MF-MSMF050-2 | 4 | ✔ [mouser.fi/en/ProductDetail/Bourns/MF-MSMF050-2](https://www.mouser.fi/en/ProductDetail/Bourns/MF-MSMF050-2) |
| F1 | **Unfitted at first power!** Buy all three, fit after bench measurement | 1+1+1 | ✔ [MF-MSMF050-2](https://www.mouser.fi/en/ProductDetail/Bourns/MF-MSMF050-2) + (p) [MF-MSMF030-2](https://www.mouser.fi/en/ProductDetail/Bourns/MF-MSMF030-2) + (p) [MF-MSMF075-2](https://www.mouser.fi/en/ProductDetail/Bourns/MF-MSMF075-2) |
| LED1 | Red 0603 — Lite-On LTST-C190KRKT | 5 | (p) [link](https://www.mouser.fi/en/ProductDetail/Lite-On/LTST-C190KRKT) |
| LED2 | Yellow-green 0603 (Vf ≈ 2 V!) — Lite-On LTST-C190GKT | 5 | (p) [link](https://www.mouser.fi/en/ProductDetail/Lite-On/LTST-C190GKT) |
| U2 | USBLC6-2SC6, SOT-23-6 — ST | 2 | (p) [link](https://www.mouser.fi/en/ProductDetail/STMicroelectronics/USBLC6-2SC6) |

JP1 = solder bridge, no part.

## Fittings & cables (Mouser or anywhere)

- **M3 nylon standoffs + screws** ×4 — any hardware kit; [search: M3 nylon standoff](https://www.mouser.fi/en/c/?q=M3%20nylon%20standoff%20kit)
- **M2 × 11 mm standoffs + M2 screws/nuts** ×2 — the OLED posts (H1/H2); 11 = 8.4 mm socket + 2.54 mm module header (10.94)
- **OLED module**: 0.96″ SSD1306, I²C 4-pin **GND·VCC·SCL·SDA**, 27.5 × 27.8 mm, holes 23.5 × 23.8 mm — hobby vendors; the socket and posts fit exactly this board
- **Cables** (hobby/retro vendors are better than Mouser for these): DB9 **straight-through** F-F ×2 (⚠ most F-F serial cables are null-modem — verify pin 2→2 3→3); PS/2 male-male **6-wire full** (A4000); DIN5 male-male **all 5 pins wired** (A2000/A3000 — MIDI cables often omit pin 1 = KCLK); micro-USB cable (flashing)

## Reminders

1. **DE9 done**: the board is retargeted to the Kycon .318″ land (commit 700f727, all gates green) — order the K22X-E9P-N (or listed equivalents) freely. The Triopak RP94s you have: keep as spares, they don't fit this land.
2. Physical fit-check of DIN5 / mini-DIN6 / DE9 samples on a 1:1 printout stays the last gate before the JLCPCB order.
3. F1 stays off the board at first power — bring-up procedure is in doc/errata.md.
