# CLAUDE.md — amigahid-pico

## What This Is

USB HID (and Bluetooth) keyboard/mouse adapter for Commodore Amigas built on the RP2040 (Raspberry Pi Pico). This is a local working copy of borb's upstream project (`github.com/borb/amigahid-pico`), carrying upstream PR #44 plus local work on real Amiga keyboard passthrough (`keyboard_recv` PIO, the `realkbd` build) on `port2-real-keyboard`, and the rev6 board on `board-rev6`.

This is **not** the KVM tooling — how the device is driven from other machines lives in the vault's KVM project. This repo is the firmware and hardware itself.

## Knowledge Base (Obsidian Vault)

All project knowledge lives in the Obsidian vault, accessible via the **obsidian-vault MCP server** (globally configured at user scope).

**Read these at the start of a session:**

Vault essentials:
- `CLAUDE.md` — vault structure and information placement rules
- `Machine/Coding Standards.md` — global rules for all projects (commit discipline, code quality)

This project:
- `Machine/Personal/amigahid-pico/Overview.md` — what this project is, goals, what goes in the folder

## Goals

- Track local firmware changes vs upstream (`borb/amigahid-pico` on GitHub): what this fork adds on top of upstream PR #44 (Pico W Bluetooth HID host, TankMouse wheel support, OLED debug), what upstream `main` has.
- Track the real Amiga keyboard passthrough work (`keyboard_recv` PIO module, `realkbd` firmware variant) so the physical Amiga keyboard can coexist with USB/BT input.
- Know at any time what is local-only, what came from upstream PRs, and what might be worth sending upstream.

## Tooling and approach

- **Firmware:** C on the pico-sdk (vendored at `./pico-sdk`), CMake build. Output is `.uf2` images flashed to the board over USB (BOOTSEL mass-storage mode).
- **Hardware:** RP2040 carrier board, gerbers generated for JLCPCB. rev5 KiCad sources are in `./kicad`
  (frozen); the rev6 board lives in `./kicad/rev6/` with its own footprint library `rev6.pretty`.
  Bluetooth work requires a Pico W.
- **Board checkers:** `tools/check_rev6_netlist.py` (schematic/netlist + rev5 guard),
  `tools/check_rev6_pcb.py` (board structure), `tools/check_rev6_style.py` (routing style).
- **Target:** a real Commodore Amiga — keyboard connector and controller ports.

## Writing new information

When you learn new information, write it to the correct Obsidian note via the `obsidian-vault` MCP server — not to auto-memory and not to this CLAUDE.md. Use auto-memory only for user preferences and conversation-specific context. Follow the Information Placement Rules in the vault's root `CLAUDE.md`.

For **dated, substantive activity** (commits of substance, hardware tests, board bring-up, flashing sessions), add an entry to `Machine/Personal/amigahid-pico/Changelog.md` (lazy-create on first entry). Same for `Machine/Personal/amigahid-pico/Bugs.md` when encountering or fixing issues.

## Commit discipline

Follow `Machine/Coding Standards.md`. Load-bearing rule: **never mention AI tools in commit messages** — no "Co-Authored-By", no "generated with", no Claude references. No exceptions.

## Ground rules

- **rev5 KiCad files are never modified.** `kicad/amigahid-pico.*`, `kicad/fp-*`, `kicad/*.net` and `kicad/*.lib` stay byte-identical. The rev5 gerbers and JLCPCB fab outputs in the working tree stay uncommitted. `tools/check_rev6_netlist.py` enforces the rev5 guard (section I).
- **rev6 board work IS committed**, on the `board-rev6` branch, entirely under `kicad/rev6/`. This supersedes the earlier "firmware only, never commit KiCad" rule, which applied before rev6 existed.
- Before committing any rev6 **schematic** change, both gates must pass:
  - `kicad-cli sch erc kicad/rev6/amigahid-pico-rev6.kicad_sch --exit-code-violations` (zero violations)
  - `python3 tools/check_rev6_netlist.py` (RESULT: PASS)
- Before committing any rev6 **board** change, all three gates must pass, in this order, after refilling zones:
  - `kicad-cli pcb drc kicad/rev6/amigahid-pico-rev6.kicad_pcb --schematic-parity --severity-all --refill-zones --save-board --exit-code-violations` (zero violations **and** zero unconnected items)
  - `python3 tools/check_rev6_pcb.py` (full PASS)
  - `python3 tools/check_rev6_netlist.py` (RESULT: PASS)
  - `python3 tools/check_rev6_style.py` (S1-S3 hold) — green since the copper was re-laid on
    45-degree runs, and no longer advisory: S1 (45-degree discipline) must stay at or above 99.0%,
    S2 (staircases) at zero, S3 (debris and duplicate copper) clear. Anything that puts copper on
    the board has to keep them there.
  A board commit that leaves any of these red must say so in the commit message and say why.
  Never relax a checker assertion to make it pass — re-target it to the new intended design instead, in the same commit.
- `pcbnew.BOARD.Save()` silently drops `net_settings.netclass_patterns` from
  `kicad/rev6/amigahid-pico-rev6.kicad_pro`, which loses the Power netclass and makes later DRC
  runs measure against weaker defaults. After **any** pcbnew-scripted save, run
  `git checkout -- kicad/rev6/amigahid-pico-rev6.kicad_pro` before running a gate; the file must
  stay byte-identical to HEAD.
- **Git: local commits only.** Never push, never open a PR, never touch remotes on this project without being asked in the same turn.

