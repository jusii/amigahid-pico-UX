# amigahid-pico rev6 — JLCPCB **bare-board** order checklist

**Package:** `amigahid-pico-ux-rev1-gerbers.zip` (9 files, 1.24 MB uncompressed)
**Cut from:** `board-rev6` @ `031f865`, working tree clean, `kicad/rev6/amigahid-pico-rev6.kicad_pcb`
**Generated:** 2026-09-27 with `kicad-cli` 10.0.6 — re-cut for the OLED socket + posts (J3 moved, H1/H2 added, I²C re-routed, credit silk on the bottom)
**Audit:** package structure, drill table, outline, apertures and silk re-verified (see §7); the board itself passed all four gates at this commit

> **BARE PCBS ONLY — no assembly service.** Every part is hand-soldered from Mouser/local stock
> (`kicad/rev6/rev6-mouser-bom.md`). Do not upload a BOM or CPL. Do not tick "PCB Assembly".
> Roughly half of the old pre-fab checklist evaporates because of this — §6 says exactly which half.

---

## 0. STOP — one gate is still open

The pre-fab report's blocking gate is **not** closed by this package:

> **Physical connector samples have not been fit-checked against the footprints.**
> `rev6.pretty`'s `DIN5_180deg_Socket_Kycon_KCDX-5S-N.kicad_mod` and
> `MiniDIN6_PS2_Socket_CUI_MD-60S.kicad_mod` still carry `VERIFY AGAINST A PHYSICAL SAMPLE BEFORE
> FAB`, and `rev6-mouser-bom.md` note 5 repeats it. Commit `b19bac9` previously caught **both** DIN
> footprints X-mirrored — which would have shorted Amiga +5 V to GND on first plug-in.

Put a caliper on real J9/J11 (Kycon KCDX-5S-N), J10/J12 (Same Sky MD-60S), P1/P2 (DE9 **.318″ / 8.08 mm
family — Kycon K22X-E9P-N; boardlocks midway between the pin rows; the 9.4 mm "European" family does NOT
fit**), J4 (Molex 67643-3910) and J13 (GCT USB4135-GF-A) **before** paying. The drill table in §7 is the
thing to measure against — it is the physical truth of what gets drilled.

Also on the bench before ordering: the 0.96″ OLED module (27.5 × 27.8 mm, holes 23.5 × 23.8 mm c-c, 4 pins
on the top-hole line, silk **GND VCC SCL SDA**) against J3's socket pads (x 81.74–89.36, y 40.5) and the
two M2 posts H1 (97.3, 40.5) / H2 (97.3, 64.3). A VCC-GND module means J3's pins 1/2 are wrong for it.

Everything below assumes that check has passed.

---

## 1. Order form — field by field

Values that are **not** the JLC default are marked ⚠.

| Field | Value | Why |
|---|---|---|
| Base Material | **FR-4** | default |
| Layers | **2** | `.gbrjob` declares `LayerNumber: 2` |
| Dimension | **100 × 82.76 mm** | Edge.Cuts routed centreline is exactly 100.000 × 82.760 (south edge moved for the DE9 retarget) |
| PCB Qty | **5** ⚠ | see §2 |
| Product Type | Industrial/Consumer electronics | default |
| Different Design | **1** | one design, not panelised |
| Delivery Format | **Single PCB** | see §5 — no assembly rail needed any more |
| PCB Thickness | **1.6 mm** | matches the `.gbrjob` `BoardThickness` and the module's castellation reach |
| PCB Color | Green | fastest/cheapest; **avoid black** — the silk is dense (3236 F + 3101 B strokes) and 0.15 mm strokes read poorly on black |
| Silkscreen | White | |
| Surface Finish | **ENIG** ⚠ | see §3 |
| Outer Copper Weight | **1 oz** | design is drawn to 1 oz rules (0.2 mm min track) |
| Via Covering | **Tented** | all 363 vias are tented in the mask gerbers — the mask layers carry pad and NPTH openings only |
| Board Outline Tolerance | ±0.2 mm (regular) | see §4 on the M3 holes |
| Gold Fingers | No | |
| **Castellated Holes** | **YES** ⚠ | see §4 — this is the order-stopper |
| Remove Order Number | **NO → "Specify a location"** ⚠ | see §4 |
| Flying Probe Test | Fully test | default |
| **Confirm Production File** | **YES** ⚠ | ~$1.50, and worth every cent here — it lets you see JLC's CAM interpretation of the internal-slot castellation before they cut copper |

**Upload:** `amigahid-pico-ux-rev1-gerbers.zip` as-is. Do not unzip and re-zip a folder — the archive is
deliberately flat (no directory entries), which is what JLC's parser wants.

**File extensions:** the gerbers use KiCad's `.gbr` extension, not Protel `.gtl/.gbl/.gts/...`
(`--no-protel-ext`). JLC auto-detects layer roles from the embedded X2 `%TF.FileFunction%`
attributes and from the included `.gbrjob`, both of which are present and correct. If the preview
ever mis-assigns a layer, the `.gbrjob` is the file to point support at.

---

## 2. Quantity — why 5

100 × 80 mm is inside JLC's 100 × 100 mm price tier, where 5 pcs is the base quantity and 10 pcs
often costs only a little more. Take **5** anyway on this spin:

- The board is unproven — no rev6 has ever been built, and the connector fit-check (§0) is the
  only thing standing between the footprints and a respin.
- 5 gives you one build, one spare for a mistake, and three to hold until the F1 value and the
  keyboard-connector fit are confirmed on real hardware.
- If rev6.0 proves out, a re-order of 10 with any silk fixes folded in costs less than scrapping 10
  now.

---

## 3. Surface finish — take ENIG

**Recommendation: ENIG.** The free default (HASL) is defensible; lead-free HASL is the one to avoid.

This board is 100 % hand-soldered, and the hand-soldering load is unusually SMD-heavy:

- **83 of the 115 footprints are on the bottom side, all SMD** — 19 × BSS138 SOT-23, 38 × 0603
  resistors, 21 × PESD5V0S1BA SOD-323, plus the 0603/0805 passives.
- **64 via-in-pad incursions across 52 refs** (my own count; the pre-fab report's polygonised count
  was 65/53 — same conclusion). Five of those vias sit essentially dead-centre in their pad:
  **C2.2, C7.2, R18.2, F1.2, F2.1**.
- **2 castellated half-holes** on an internal slot wall that get soldered by hand with a wire.
- The module (U1) attaches by **castellated edge** to surface pads — the join that historically
  goes wrong on this design (`doc/errata.md`: "flood the edges with solder … buzz the attachment
  out with a multimeter").

Why ENIG wins here:

1. **Flat, coplanar pads.** HASL leaves an uneven domed solder blob on every pad. On a 0603 land or
   a SOT-23's 0.95 mm pitch that is a placement nuisance — parts rock and skate before the iron
   lands. ENIG's pads are dead flat, so hand-placed parts stay put.
2. **Shelf life.** This build will not happen in one sitting: F1's value is pending a bench
   measurement, and the connector samples are still being checked. ENIG's gold stays solderable for
   ~12 months in a drawer; HASL's exposed flux residue and bare edges dull much faster.
3. **Castellations wet more predictably.** Hot-air levelling on half-holes is inconsistent — it can
   leave the half-barrel rough, or blow a solder bead into it. ENIG plates the barrel wall evenly,
   which matters for both the module edge and the two USB-tap half-holes.
4. **Via-in-pad behaves better.** HASL's levelling air pushes solder into an open 0.30 mm barrel and
   leaves an unpredictable plug or crater right where you need a flat land. ENIG leaves the barrel
   clean and the surrounding land flat, so you can see and control the wicking yourself.
5. The upcharge at 5 pcs / 80 cm² is small — a few dollars against a board carrying a ~€30 module.

**If you take the free finish instead:** choose **leaded HASL**, not lead-free. Leaded HASL wets at
a lower temperature and is the friendlier of the two under a hand iron. **Lead-free HASL is the
worst option here** — it keeps HASL's uneven pads *and* adds the higher process temperature, giving
you neither ENIG's flatness nor leaded HASL's easy wetting.

*(The `.gbrjob` records `"Finish": "None"` — that is just KiCad's stackup placeholder, not a
request. The order form is what decides.)*

---

## 4. The three things you must state by hand

### 4a. Castellated holes on an **internal slot wall** — the likely order-stopper

**In the form: set "Castellated Holes" = Yes.**

What is actually there (verified from the drill file and Edge.Cuts):

- Drill tool **T6, Ø1.300 mm, exactly 2 hits**, tagged `TA.AperFunction,Plated,PTH,CastelletedDrill`
- Drill-file coordinates: **`X49.8 Y-50.26`** and **`X49.8 Y-52.26`**
- Both are bisected by a **3.81 × 2.00 mm internal milled slot** (drill-file/gerber coords
  `X48.66…52.47`, `Y-50.26…-52.26`), each centre sitting exactly on one of the slot's two long
  walls, 1.14 mm clear of the slot ends.
- The slot **touches no board edge** — the outer profile is one closed 100 × 80 mm chain and the
  slot is a separate closed internal chain. Confirmed by the audit (E2, E5, E7).

⚠ **This is what makes it unusual.** JLC's castellation process is written for half-holes on the
**board profile**. rev5's equivalent tap was an edge-open notch — ordinary edge castellations. rev6
puts them on an *internal* slot wall. Expect a query, not silent acceptance.

**Order remark — paste this verbatim:**

> The two Ø1.30 mm half-holes in the drill file at X49.8 Y-50.26 and X49.8 Y-52.26 are located on
> the long walls of a 3.81 × 2.00 mm internal milled slot near the centre of the board, NOT on the
> board profile. They are intentional plated castellations for a USB tap. Please confirm your
> process supports plated half-holes on an internal slot wall. If it does not, please fabricate the
> slot as a plain milled cutout and drill/plate the two Ø1.30 mm holes normally — bisecting them
> with the slot route is expected and acceptable. Do not delete the slot or the two holes, and do
> not move them.

**Fallback ladder if JLC declines:**

1. **Preferred fallback (already in the remark).** Ask them to drill + plate the two holes as
   ordinary PTHs and route the slot anyway. The finished part is physically identical; you simply
   lose the process guarantee on the cut barrel face. Deburr the two half-barrels with a needle
   file on arrival and tin them before soldering the tap wires.
2. **If they refuse to route the internal slot at all.** Order the board without the slot and cut
   it yourself: the two Ø1.30 mm plated holes are still drilled, 2.00 mm apart on a common
   x = 49.80 centreline, so filing the 2 mm-wide window between them with a small round/flat needle
   file (or a 2 mm end mill) reproduces the slot exactly. Work from the top side, U1 not yet fitted.
3. **Worst case, skip it.** The tap is only ever reached by hand-soldering (build sequence step 5c),
   so the plating is convenience, not function. Bodge wires direct to the module's TP2/TP3 pads.

Per `../DESIGN-NOTES.md`, TP1/TP2/TP3 and all four USB shell pads are **identical on Pico, Pico W and
Pico 2 W** — only TP4/TP5/TP6 shift by 1.5 mm — so the tap works on any of the three modules.

### 4b. M3 corner holes are Edge.Cuts-**milled**, not drilled

Four **Ø3.200 mm circles** on Edge.Cuts at board coordinates **(4, 4), (4, 78.76), (96, 4), (96, 78.76)**
— closed, correctly sized and correctly placed.

⚠ **They are not in the drill file.** The excellon's only `NonPlated` entries are the two **Ø2.200 mm
OLED posts H1/H2 at (97.3, 40.5) and (97.3, 64.3)** (tool T11 — ordinary NPTH, drilled). The four corner
holes exist *only* in `amigahid-pico-rev6-Edge_Cuts.gbr`, so they are **routed with the profile**: correctly
unplated, but at **routing tolerance (~±0.13 mm)** rather than drill tolerance (~±0.08 mm).

- Ø3.2 mm nominal ⇒ worst case ≈ 3.07–3.33 mm. An M3 screw's major diameter is 3.00 mm, so even the
  tight end still clears. **Fine for M3 clearance** — but do not expect a precision fit, and do not
  plan on the corner holes locating anything. Use them for standoffs, not alignment.
- They are unplated, so the corners make **no ground connection** to a metal chassis. Intentional.

**Say this in the remarks too:**

> The four Ø3.2 mm circles at the board corners are on the Edge.Cuts/profile layer intentionally.
> They are unplated M3 mounting holes to be routed with the outline. Please do NOT convert them to
> plated drills.

⚠ **And do not let anyone "fix" the other Ø3.2 mm holes.** Drill tool **T10, Ø3.200 mm, 4 hits** in
the drill file is a *different* feature: those are P1/P2's DE9 flange holes. They are **plated, on
GND, and correct as-is** — metal board-lock hardware grounds the D-sub shells through them.

### 4c. Order number → "Specify a location" (do **not** remove)

**Answer to "Remove Order Number": NO.** Select **"Specify a location"**.

The board already carries a `JLCJLCJLCJLC` token on **F.Silkscreen at (30.000, 52.300)**. U1 sits at
(25.5, 51.26) rotated −90°, so that token is **underneath the module** once it is fitted — the
marker is present, JLC is satisfied, and it is invisible on a built board. rev5 precedent.

- "Specify a location" is **free**. "Remove order number" costs extra *and* throws away a marker
  that is already deliberately hidden.
- Leaving JLC to choose the location is the failure mode: they will put it somewhere visible, quite
  possibly across the credit block or a connector legend.

---

## 5. Silkscreen — what shipped

The credit block is on **B.Silkscreen** now (mirrored, reads right from the underside) because the OLED
module covers its old top-side spot:

```
hid-pico Amiga UX
UX rev 1 - by Jusii
github.com/jusii/amigahid-pico
based on the rev5 design by borb
github.com/borb/amigahid-pico
```

Title 2.2 mm bold at y 27.2, then four 1.2 mm rows at y 30.5 → 37.4, centred on x = 77.5, 0.2 mm
strokes. On F.Silkscreen: `TO AMIGA`, `FROM KEYBOARD`, `ONE Amiga`, `PORT 1`, `PORT 2`, `PIN 1`,
`USB HOST`, `USB / BOOTSEL >`, `AUX 5V` (moved to y 37.4, just north of the module edge) and every
connector reference designator (PCB checker H1–H3 at HEAD). `J3` sits under the module — deliberate.

⚠ **Silk strokes bottom out at exactly 0.15 mm**, which is JLC's stated minimum, not a margin above it
(F.Silkscreen apertures 0.15 / 0.18 / 0.2 mm and up; B.Silkscreen 0.15 mm and up). Expect the finest
legend text to render slightly thin or locally broken. Nothing is below the floor, so it will be
fabricated — but this is the reason to take green/white rather than black/white.

No silkscreen ink falls inside the M3 holes, inside the USB-tap slot, or outside the board profile
(audit T4/T5/T6).

---

## 6. Pre-fab report items: VOID vs REMAIN

### ✅ VOID — killed outright by "bare boards, no assembly"

| Item | Why it is void now |
|---|---|
| **Epoxy Filled & Capped Vias** decision | The fee existed to protect **reflow** yield on 65 via-in-pad incursions. With no reflow there is no yield to protect. Do **not** tick it — it would charge you for all 345 vias to fix a problem you no longer have. *(The underlying via-in-pad is not gone — see REMAIN.)* |
| **CPL / POS file** and the header remap | No CPL is being sent. `rev6-cpl.csv` in the scratchpad was stale (114 rows) and is simply not used. |
| **JLC placement-preview rotation check** (D1/D2, C1/C4, U2, LED1/LED2) | Nothing is machine-placed, so there are no rotations to verify. *(The polarity risk moves to your bench — see REMAIN.)* |
| **PCBA = double-sided SMT, 2 setups / 100 parts, 17 top + 83 bottom** | No assembly ordered. |
| **15 `exclude_from_pos_files` refs** | Only meaningful to a CPL. |
| **Extended-part loading fees** (C1 C128533, C4 C413656, F2/F3 C17313) | No LCSC parts are being bought; everything comes from Mouser. |
| **LCSC stock confirmation before committing to a schedule** | Same. |
| **"F1 must NOT be assembled"** as an *order* instruction | Nothing is assembled. *(F1 sizing remains a build gate — see REMAIN.)* |
| **4 SMD parts inside JLC's ~5 mm assembly edge margin** (R7 3.13 mm, Q4 4.03 mm, LED1 3.23 mm, R39 3.23 mm) | This drove an expected **break-off rail or panelisation request**, which would have left mouse-bite stubs — including on the antenna notch, the one edge whose shape is RF-relevant. The margin is an *assembly* constraint. Bare boards need no rail, so **order "Single PCB" and the antenna notch ships with a clean routed edge.** This is a genuine win from dropping assembly. |

### ⚠ REMAIN — still live

| Item | Status |
|---|---|
| **Castellations on an internal slot wall** | **The order-stopper.** §4a. Unchanged — this is a fab process question, not an assembly one. |
| **M3 holes are profile-milled, not drilled** | §4b. Unchanged. |
| **Order-number location** | §4c. Unchanged. |
| **Physical connector-sample fit check** | **STILL BLOCKING.** §0. If anything, more important — you are hand-fitting these, with no JLC DFM pass to catch a wrong hole grid. |
| **F1 final value** | Still a placeholder (draft 750 mA, no LCSC code, `Sourcing` says do not order assembled). Order MF-MSMF035 / 050 / 075 — all three share the 1812 land — and fit the right one after a full-stack bench measurement (plan predicts 350–500 mA). Must trip before the host's fuse (A4000 keyboard port ≈ 100 mA). |
| **Via-in-pad — 64 incursions, 52 refs** | Downgraded from *reflow yield risk* to a **hand-soldering nuisance**, but not gone: an open Ø0.30 mm barrel inside an 0603 land wicks solder off the joint. Worst five, where the via is essentially dead-centre in the pad: **C2.2, C7.2, R18.2, F1.2, F2.1**. Also **C4 ×3, R20 ×3, F1/F2/F3/Q12/Q14/Q15/R23/R6 ×2** each. Tactics: tin the pad first and let the barrel fill, then place the part; add flux and a touch more solder than feels right; check C1/C4 especially — they sit under 6.3 mm cans where a starved joint cannot be inspected afterwards. |
| **Polarity-critical parts** | No longer a CPL check, now a **soldering-time** check: **D1, D2** (SS34, SMA — board-side pad 1 is the cathode on SYS5V; reversed kills the Amiga 5 V path entirely), **C1, C4** (board-side pad 1 is `+`; reversed vents two electrolytics on a 5 V rail), **U2** (USBLC6-2SC6, pin 2 = GND), **LED1/LED2**. D10–D30 are bidirectional and orientation-free. |
| **Five ambiguous ESD designators — D13, D14, D18, D26, D27** | **More important now, not less.** The SOD-323 row along the south edge has no label position within 2 mm that doesn't overlap something, so five designators read ambiguously. You are placing these by hand: **work from the schematic/board file for D13/D14/D18/D26/D27, not from the silkscreen.** |
| **Mini-DIN6 mask dams at 0.30 mm (J10, J12)** | Fabricable — comfortably above JLC's ~0.25 mm printable floor. Puts `/kbdata` next to GND on J10 and `/KBIN_5V` next to a spare pin on J12. Hand-soldering these needs a steady iron; wick any bridge rather than reflowing it. |
| **J4 USB-A overhangs the south edge by ~1.2 mm** | Was ~4 mm before the DE9 retarget moved the edge. A fillet of epoxy under the front is now belt-and-braces; still cheap insurance if the port is plugged often. |
| **OLED socket + posts** | J3 is a 1×4 **female** socket (pins x 81.74–89.36, y 40.5, order GND·VCC·SCL·SDA); H1/H2 are Ø2.2 NPTH for M2 posts. Module sits at x 71.8–99.3, y 38.5–66.3; posts = socket body + 2.54 mm (11 mm for an 8.5 mm socket), never under 8 mm — the Pico's micro-USB cable passes under the module's west edge. No post on the two west corners by design. |
| **South edge cable clash** | USB-A opening 3.68 / 3.67 mm from the DE9 hoods. Slim D-sub hoods + a normal USB plug fit; a full-size moulded hood + fat plug or a USB stick does not. Buy slim hoods or a short USB extension. |
| **"Power the keyboard connector first"** | SYS5V is fed only from the keyboard connector (D1) or USB-C aux (D2). Cabling only the joystick ports leaves SYS5V dead and drags all 14 port lines low through 10 k — the machine sees stuck directions while the board looks dead. |
| **Module test points / plain Pico** | The F.Cu keep-out at x 35.40–42.50, y 47.76–49.76 voids TP4/TP5/TP6 for a Pico W or Pico 2 W. A **plain Pico's TP4 is not covered** — put Kapton over its test points if you bodge one in. |
| **370 µF of bulk at plug-in**, **single Ø0.30 mm via on `/AMIGA_5V_FUSED`**, **single ESD clamp per shared keyboard net**, **USB pair ground reference ~49–52 %** | All measured, judged and accepted for rev6.0. Unchanged by the assembly decision. Revisit on a respin. |

---

## 7. What is in the zip, and what I verified

### Contents — 9 files, flat, nothing else

| File | Bytes | Role |
|---|---|---|
| `amigahid-pico-rev6-F_Cu.gbr` | 468 084 | `Copper,L1,Top` |
| `amigahid-pico-rev6-B_Cu.gbr` | 435 807 | `Copper,L2,Bot` |
| `amigahid-pico-rev6-F_Mask.gbr` | 14 440 | `Soldermask,Top` |
| `amigahid-pico-rev6-B_Mask.gbr` | 13 762 | `Soldermask,Bot` |
| `amigahid-pico-rev6-F_Silkscreen.gbr` | 89 547 | `Legend,Top` |
| `amigahid-pico-rev6-B_Silkscreen.gbr` | 202 542 | `Legend,Bot` (carries the credit block now) |
| `amigahid-pico-rev6-Edge_Cuts.gbr` | 2 042 | `Profile,NP` — byte-identical to the previous cut apart from the date header |
| `amigahid-pico-rev6-job.gbrjob` | 2 564 | Gerber job — declares 2 layers, 1.6 mm, `Castellated: true` |
| `amigahid-pico-rev6.drl` | 7 455 | Excellon, `MixedPlating,1,2`, absolute mm |

Deliberately **excluded**: the 17 non-fabrication layers a plain export emits (`F_Fab`, `B_Fab`,
`User_Comments`, both courtyards, `Margin`, `User_Drawings`, `User_1`–`User_4`, `User_Eco1/2`, the
adhesive layers) — an earlier export shipped 11 of these and they are exactly what gets mis-bound
in a manual CAM pass. The **drill map** (`drill-map.gbr`) is also excluded for the same reason: it
is a human-readable plot, not a fab input, and a CAM operator can mistake it for a layer. It is
kept one directory up as `../drill-map.gbr` if you want to eyeball the hole pattern.

### Drill table — 11 tools, 495 hits, **2 non-plated**

| Tool | Ø (mm) | Hits | Plating | Aperture function | What it is |
|---|---|---|---|---|---|
| T1 | 0.300 | 360 | PTH | `ViaDrill` | vias (Ø0.60 mm pad) |
| T2 | 0.500 | 3 | PTH | `ViaDrill` | power-transition vias (Ø0.90 mm pad) |
| T3 | 0.950 | 4 | PTH | `ComponentDrill` | USB-A J4 signal pins |
| T4 | 1.000 | 72 | PTH | `ComponentDrill` | 2.54 mm headers, OLED socket, module pads, DIN pins |
| T5 | 1.100 | 30 | PTH | `ComponentDrill` | mini-DIN6 signal pins (J10/J12) and DE9 pins (P1/P2) |
| **T6** | **1.300** | **2** | **PTH** | **`CastelletedDrill`** | **USB-tap castellations, internal slot wall** |
| T7 | 1.400 | 14 | PTH | `ComponentDrill` | DIN5 pins + mounting tabs (J9/J11) |
| T8 | 2.300 | 2 | PTH | `ComponentDrill` | USB-A J4 shield legs |
| T9 | 2.500 | 2 | PTH | `ComponentDrill` | mini-DIN6 centre shield post (J10/J12) |
| T10 | 3.200 | 4 | PTH | `ComponentDrill` | DE9 P1/P2 flange holes — plated, on GND, correct |
| **T11** | **2.200** | **2** | **NPTH** | `ComponentDrill` | **OLED posts H1/H2 at (97.3, 40.5) / (97.3, 64.3) — unplated, M2** |
| | | **495** | | | **2 NPTH entries** |

Every size and count reconciles against the board file's own pads and vias: 363 vias
(360 × 0.30 + 3 × 0.50) + 130 plated through-hole pads + 2 NPTH = 495. No oval/slotted pad drills.

Milled features (Edge.Cuts only, absent from the drill file): 4 × Ø3.2 mm M3 corner circles, the
3.81 × 2.00 mm USB-tap slot, and the antenna notch in the west edge (x 0–8.50, y 43.71–58.81).

### Audit result — re-verified on this cut

Checked on the exported files that went into the zip (the archive is flat, 9 entries, no directory
entries):

- **Presence** — 7 fab layers + `.gbrjob` + `.drl`, all non-empty, no stray files, no directory
  entries in the archive.
- **Structure** — every gerber terminates with `M02*`; `%TF.FileFunction%` matches each layer;
  both copper layers carry filled `G36` pour regions (F.Cu 31, B.Cu 42), so the GND pours are
  really in the plot.
- **Outline** — 26 Edge.Cuts endpoints, **every one at degree 2** (no open ends, no T-junctions);
  6 closed chains = 1 outer 100.000 × 80.000 mm profile + 4 M3 circles + 1 tap slot; nothing
  unexplained; the tap slot touches no board edge.
- **Drill** — table above; the castellated tool is correctly tagged at `X49.8 Y-50.26` / `X49.8 Y-52.26`;
  the only NonPlated entries are H1/H2.
- **Silkscreen** — the credit block is present with ink on all five rows at the expected baselines,
  and renders right-reading (not mirrored) when rasterised.
- **Apertures** — smallest silkscreen aperture 0.150 mm on both sides (at, not below, JLC's floor —
  the stock socket footprint's 0.12 mm outline was raised to 0.15 for this cut); narrowest stroked
  copper aperture 0.200 mm (meets the 0.2 mm floor the design was drawn to).
- **Deep checks** — all 363 vias tented; both castellations bisected by the slot wall with 1.14 mm
  end clearance; castellation pads have a top-side mask opening so they can be hand-soldered; no
  silk or copper outside the profile; antenna notch present (Edge.Cuts unchanged since the
  previous cut).

Two things worth knowing about how this package was produced:

1. **Zone fills are current.** Re-exporting the copper with `--check-zones` produced a
   byte-identical result, which proves the fills saved in the committed board are up to date and
   the plot is not silently using stale copper.
2. **`kicad-cli pcb export gerbers` dirties the project files.** It rewrote both
   `kicad/rev6/amigahid-pico-rev6.kicad_prl` **and** `…kicad_pro`, performing a KiCad-10 schema
   migration that bumps `net_settings.meta.version` 3 → 5. The `netclass_patterns` survived this
   time, but `CLAUDE.md`'s existing warning only names `pcbnew.BOARD.Save()`. Both files were
   restored with `git checkout --` and the tree is clean. **Anyone regenerating this package must
   do the same** — and must re-run the board gates afterwards, never on the migrated file.

---

## 8. On arrival, before any soldering

1. Inspect the two USB-tap half-holes — plated and clean, or burred? Deburr and tin if needed.
2. Check the four M3 corner holes against an actual M3 screw and your standoffs.
3. Buzz out the DE9 flange holes to GND (they should be connected — they are plated, on GND).
4. Dry-fit **every** connector before soldering anything: J9/J11 DIN5, J10/J12 mini-DIN6, P1/P2 DE9,
   J4 USB-A, J13 USB-C — and the OLED module on J3's socket with M2 screws through H1/H2. This is
   the last chance to catch a footprint error cheaply.
5. Check the bottom shifter field for via-in-pad barrels that arrived plugged or cratered —
   especially C2, C7, R18, F1, F2 (§6).
6. Then follow the build order in `../DESIGN-NOTES.md`: bottom-side SMD first, connectors, **epoxy
   fillet under J4**, module last, and buzz the module's castellated edge before powering anything.
