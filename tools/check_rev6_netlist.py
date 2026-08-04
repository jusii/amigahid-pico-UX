#!/usr/bin/env python3
"""
amigahid-pico rev6 netlist cross-checker.

asserts the rev6 schematic's netlist against the authoritative rev6
connectivity spec, and cross-checks that spec against the pin defines in
src/config.h (single source of truth).

usage (note: /nas is noexec, always invoke through the interpreter):

    python3 tools/check_rev6_netlist.py                  # export + check
    python3 tools/check_rev6_netlist.py /tmp/rev6.net    # check an existing netlist
    python3 tools/check_rev6_netlist.py --sch path.kicad_sch
    python3 tools/check_rev6_netlist.py --no-git         # skip rev5-untouched check

exit code is 0 only when every assertion passes.

no third-party modules: stdlib only.
"""

import argparse
import os
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# repo layout
# ---------------------------------------------------------------------------

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TOOLS_DIR)

DEF_SCH = os.path.join(REPO_ROOT, "kicad", "rev6", "amigahid-pico-rev6.kicad_sch")
DEF_SYM = os.path.join(REPO_ROOT, "kicad", "rev6", "rev6-symbols.kicad_sym")
DEF_FP = os.path.join(REPO_ROOT, "kicad", "rev6", "rev6.pretty", "RPi_PicoW_SMD_TH.kicad_mod")
DEF_CONFIG = os.path.join(REPO_ROOT, "src", "config.h")
DEF_NET = "/tmp/rev6.net"
KICAD_CLI = "/usr/bin/kicad-cli"

REV5_GUARDED = [
    "kicad/amigahid-pico.kicad_sch",
    "kicad/amigahid-pico.kicad_pcb",
]
REV5_GUARDED_WIDE = [
    "kicad/amigahid-pico.kicad_pro",
    "kicad/amigahid-pico.kicad_prl",
    "kicad/amigahid-pico.net",
    "kicad/amigahid-pico-cache.lib",
    "kicad/fp-lib-table",
    "kicad/fp-info-cache",
]

# ---------------------------------------------------------------------------
# THE SPEC
# ---------------------------------------------------------------------------

# gpio -> (role, shifted?, high-side net name)
#   shifted: the gpio lands on the LOW net of a bss138 channel whose HIGH net
#            is the named net. non-shifted: the gpio is on the named net direct.
GPIO_SPEC = {
    0:  ("uart_tx",   False, "uart_tx"),
    1:  ("uart_rx",   False, "uart_rx"),
    2:  ("i2c_sda",   False, "i2c_sda"),
    3:  ("i2c_scl",   False, "i2c_scl"),
    4:  ("kbreset",   True,  "kbreset"),
    5:  ("kbdata",    True,  "kbdata"),
    6:  ("kbclock",   True,  "kbclock"),
    7:  ("cont1_hq",  True,  "cont1_hq"),
    8:  ("cont1_vq",  True,  "cont1_vq"),
    9:  ("cont1_h",   True,  "cont1_h"),
    10: ("cont1_v",   True,  "cont1_v"),
    11: ("cont1_b1",  True,  "cont1_b1"),
    12: ("cont1_b2",  True,  "cont1_b2"),
    13: ("cont1_b3",  True,  "cont1_b3"),
    14: ("kbin_clk",  True,  "kbin_clk"),
    15: ("kbin_dat",  True,  "kbin_dat"),
    16: ("led1",      False, None),          # via 1k to LED1 to GND
    17: ("led2",      False, None),          # via 1k to LED2 to GND
    18: ("cont2_b3",  True,  "cont2_b3"),
    19: ("cont2_b2",  True,  "cont2_b2"),
    20: ("cont2_b1",  True,  "cont2_b1"),
    21: ("cont2_hq",  True,  "cont2_hq"),
    22: ("cont2_vq",  True,  "cont2_vq"),
    26: ("cont2_h",   True,  "cont2_h"),
    27: ("cont2_v",   True,  "cont2_v"),
    28: ("spare",     False, None),          # -> J7.1
}

SHIFT_CHANNELS = [gp for gp, (_, s, _) in sorted(GPIO_SPEC.items()) if s]
HIGH_NETS = [GPIO_SPEC[gp][2] for gp in SHIFT_CHANNELS]

# amiga-facing high-side lines needing a ground-clamp-only TVS
ESD_LINES = HIGH_NETS[:]

# module pin numbers named explicitly by the spec
MODULE_PIN = {"3V3": 36, "VSYS": 39, "VBUS": 40}

NC = "__NC__"       # pin must be an explicit no-connect
SHIELD = "SHIELD"   # connector shell / mounting pad

CONNECTORS = {
    "J1": {  # A500-out header 1x8
        "1": "kbclock", "2": "kbdata", "3": "kbreset", "4": "amiga_5v",
        "5": NC, "6": "gnd", "7": "kb_pwrled", "8": "kb_drvled",
    },
    "J8": {  # keyboard-IN header 1x8, mirrors the A500 keyboard lead
        "1": "kbin_clk", "2": "kbin_dat", "3": "kbreset", "4": "kbin_5v",
        "5": NC, "6": "gnd", "7": "kb_pwrled", "8": "kb_drvled",
    },
    "J9": {  # DIN5-OUT
        "1": "kbclock", "2": "kbdata", "3": NC, "4": "gnd", "5": "amiga_5v",
    },
    "J10": {  # miniDIN6-OUT (PS/2)
        "1": "kbdata", "2": NC, "3": "gnd", "4": "amiga_5v", "5": "kbclock",
        "6": NC, SHIELD: "gnd",
    },
    "J11": {  # DIN5-IN
        "1": "kbin_clk", "2": "kbin_dat", "3": NC, "4": "gnd", "5": "kbin_5v",
    },
    "J12": {  # miniDIN6-IN
        "1": "kbin_dat", "2": NC, "3": "gnd", "4": "kbin_5v", "5": "kbin_clk",
        "6": NC, SHIELD: "gnd",
    },
    "P1": {  # DE9 male, controller port 1
        "1": "cont1_v", "2": "cont1_h", "3": "cont1_vq", "4": "cont1_hq",
        "5": "cont1_b3", "6": "cont1_b1", "7": NC, "8": "gnd", "9": "cont1_b2",
        SHIELD: "gnd",
    },
    "P2": {  # DE9 male, controller port 2
        "1": "cont2_v", "2": "cont2_h", "3": "cont2_vq", "4": "cont2_hq",
        "5": "cont2_b3", "6": "cont2_b1", "7": NC, "8": "gnd", "9": "cont2_b2",
        SHIELD: "gnd",
    },
    "J4": {  # USB-A host
        "1": "usba_5v", "2": "usb_dm", "3": "usb_dp", "4": "gnd", SHIELD: "gnd",
    },
    "J3": {  # OLED 1x4
        "1": "3v3", "2": "gnd", "3": "i2c_scl", "4": "i2c_sda",
    },
    "J2": {  # debug 1x6
        "1": "gnd", "2": "uart_tx", "3": "uart_rx", "4": "swdio",
        "5": "gnd", "6": "swclk",
    },
    "J7": {  # spare gpio 1x3
        "2": "3v3", "3": "gnd",   # pin 1 checked against the GP28 net separately
    },
}

# config.h BOARD_HIDPICO_REV6 defines that must match the gpio map
CONFIG_PINS = {
    "I2C_PIN_SDA": 2,
    "I2C_PIN_SCL": 3,
    "KBD_AMIGA_RST": 4,
    "KBD_AMIGA_DAT": 5,
    "KBD_AMIGA_CLK": 6,
    "QM1_AMIGA_HQ": 7,
    "QM1_AMIGA_VQ": 8,
    "QM1_AMIGA_H": 9,
    "QM1_AMIGA_V": 10,
    "QM1_AMIGA_B1": 11,
    "QM1_AMIGA_B2": 12,
    "QM1_AMIGA_B3": 13,
    "KBD_REAL_CLK": 14,
    "KBD_REAL_DAT": 15,
    "LED_STATUS1": 16,
    "LED_STATUS2": 17,
}
CONFIG_FLAGS = ["HAS_SCREEN", "HAS_KEYBOARD", "HAS_PORT1", "HAS_PORT2",
                "HAS_KBD_IN", "HAS_STATUS_LEDS"]
CONFIG_FORBIDDEN = ["I2C_IRQN"]
# optional port-2 emulation defines: only checked when present
CONFIG_OPTIONAL_PINS = {
    "QM2_AMIGA_B3": 18, "QM2_AMIGA_B2": 19, "QM2_AMIGA_B1": 20,
    "QM2_AMIGA_HQ": 21, "QM2_AMIGA_VQ": 22, "QM2_AMIGA_H": 26,
    "QM2_AMIGA_V": 27,
}

# ---------------------------------------------------------------------------
# s-expression parsing
# ---------------------------------------------------------------------------


def sx_tokenize(text):
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in "()":
            yield c
            i += 1
        elif c.isspace():
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                elif text[j] == '"':
                    break
                else:
                    buf.append(text[j])
                    j += 1
            yield "".join(buf)
            i = j + 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()"':
                j += 1
            yield text[i:j]
            i = j


def sx_parse(text):
    """parse into nested python lists; atoms are plain strings."""
    stack = [[]]
    for tok in sx_tokenize(text):
        if tok == "(":
            new = []
            stack[-1].append(new)
            stack.append(new)
        elif tok == ")":
            if len(stack) == 1:
                raise ValueError("unbalanced ')' in s-expression")
            stack.pop()
        else:
            stack[-1].append(tok)
    if len(stack) != 1:
        raise ValueError("unbalanced '(' in s-expression")
    return stack[0]


def sx_head(node):
    return node[0] if isinstance(node, list) and node and isinstance(node[0], str) else None


def sx_children(node, key):
    return [c for c in node if isinstance(c, list) and sx_head(c) == key]


def sx_child(node, key):
    got = sx_children(node, key)
    return got[0] if got else None


def sx_val(node, key, default=None):
    c = sx_child(node, key)
    if c is None or len(c) < 2 or not isinstance(c[1], str):
        return default
    return c[1]


def sx_walk(node, key):
    """yield every nested list whose head is key."""
    if isinstance(node, list):
        if sx_head(node) == key:
            yield node
        for c in node:
            if isinstance(c, list):
                yield from sx_walk(c, key)


# ---------------------------------------------------------------------------
# name normalisation
# ---------------------------------------------------------------------------

NET_ALIASES = {
    "p3v3": "3v3", "vdd3v3": "3v3", "vcc3v3": "3v3", "v3v3": "3v3",
    "vss": "gnd", "gnda": "gnd", "agnd": "gnd",
    "amiga5v": "amiga_5v", "amiga_5v0": "amiga_5v",
    "kbin5v": "kbin_5v", "usba5v": "usba_5v", "usb_a_5v": "usba_5v",
    "sys_5v": "sys5v", "sys5v0": "sys5v", "p5v_sys": "sys5v",
    "usbdp": "usb_dp", "usbdm": "usb_dm",
    "usb_dplus": "usb_dp", "usb_dminus": "usb_dm",
    "usb_d_p": "usb_dp", "usb_d_n": "usb_dm", "usb_dn": "usb_dm",
}


def norm(name):
    """normalise a kicad net name: drop sheet path, punctuation, case."""
    if name is None:
        return None
    n = name.strip()
    if n.startswith("unconnected-"):
        return n
    n = n.split("/")[-1]
    n = n.lower()
    n = re.sub(r"\bd\+", "dp", n)
    n = re.sub(r"\bd-", "dm", n)
    n = re.sub(r"[^a-z0-9]+", "_", n)
    n = n.strip("_")
    return NET_ALIASES.get(n, n)


def is_nc(netname):
    return netname is not None and netname.startswith("unconnected-")


# ---------------------------------------------------------------------------
# value parsing (resistors / capacitors)
# ---------------------------------------------------------------------------

_MULT = {"": 1.0, "r": 1.0, "k": 1e3, "m": 1e6, "meg": 1e6}
_CMULT = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3, "": 1.0}


def parse_res(value):
    """return ohms, or None."""
    if not value:
        return None
    s = value.strip().lower()
    s = s.replace("Ω", "").replace("ω", "")
    s = re.sub(r"(ohms?|Ω)", "", s)
    s = s.replace(" ", "")
    s = re.sub(r"[,±]\d+%$", "", s)
    s = re.sub(r"\d+%$", "", s)
    # eia 4-digit code with r prefix, e.g. R1002 = 100 * 10^2 = 10k
    m = re.fullmatch(r"r(\d{4})", s)
    if m:
        d = m.group(1)
        return float(d[:3]) * (10 ** int(d[3]))
    # 4k7 / 10k0 style
    m = re.fullmatch(r"(\d+)(r|k|m|meg)(\d+)", s)
    if m:
        return float("%s.%s" % (m.group(1), m.group(3))) * _MULT[m.group(2)]
    # 4.7k / 10k / 100
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(r|k|m|meg)?", s)
    if m:
        return float(m.group(1)) * _MULT[m.group(2) or ""]
    return None


def parse_cap(value):
    """return farads, or None."""
    if not value:
        return None
    s = value.strip().lower().replace(" ", "")
    s = re.sub(r"f$", "", s)
    s = s.replace("µ", "u")
    m = re.fullmatch(r"(\d+)(p|n|u|m)(\d+)", s)
    if m:
        return float("%s.%s" % (m.group(1), m.group(3))) * _CMULT[m.group(2)]
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(p|n|u|m)?", s)
    if m:
        return float(m.group(1)) * _CMULT[m.group(2) or ""]
    return None


def near(a, b, tol=0.05):
    return a is not None and b and abs(a - b) <= tol * b


# ---------------------------------------------------------------------------
# netlist model
# ---------------------------------------------------------------------------


class Netlist(object):
    def __init__(self, path):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            tree = sx_parse(fh.read())
        root = None
        for node in tree:
            if sx_head(node) == "export":
                root = node
                break
        if root is None:
            raise ValueError("%s: not a kicad s-expression netlist" % path)

        self.path = path
        self.comps = {}          # ref -> dict
        self.net_nodes = {}      # normalised net -> [(ref, pin)]
        self.net_raw = {}        # normalised net -> raw name
        self.pin_net = {}        # (ref, pin) -> normalised net
        self.pin_func = {}       # (ref, pin) -> pinfunction
        self.comp_pins = {}      # ref -> [pin]

        comps = sx_child(root, "components")
        for comp in sx_children(comps or [], "comp"):
            ref = sx_val(comp, "ref")
            if not ref:
                continue
            libsource = sx_child(comp, "libsource")
            self.comps[ref] = {
                "ref": ref,
                "value": sx_val(comp, "value", "") or "",
                "footprint": sx_val(comp, "footprint", "") or "",
                "lib": (sx_val(libsource, "lib", "") if libsource else "") or "",
                "part": (sx_val(libsource, "part", "") if libsource else "") or "",
                "descr": (sx_val(libsource, "description", "") if libsource else "") or "",
            }

        self.aliases = {}        # normalised net -> {raw names}
        nets = sx_child(root, "nets")
        for net in sx_children(nets or [], "net"):
            raw = sx_val(net, "name", "")
            key = norm(raw)
            self.net_raw.setdefault(key, raw)
            self.aliases.setdefault(key, set()).add(raw)
            bucket = self.net_nodes.setdefault(key, [])
            for node in sx_children(net, "node"):
                ref = sx_val(node, "ref")
                pin = sx_val(node, "pin")
                fn = sx_val(node, "pinfunction", "")
                if ref is None or pin is None:
                    continue
                bucket.append((ref, pin))
                self.pin_net[(ref, pin)] = key
                self.pin_func[(ref, pin)] = fn or ""
                self.comp_pins.setdefault(ref, []).append(pin)

    # -- lookups ------------------------------------------------------------

    def has(self, ref):
        return ref in self.comps

    def net_of(self, ref, pin):
        return self.pin_net.get((ref, pin))

    def nets_of(self, ref):
        return [self.pin_net[(ref, p)] for p in self.comp_pins.get(ref, [])]

    def nodes(self, net):
        return self.net_nodes.get(net, [])

    def refs_on(self, net):
        return sorted({r for r, _ in self.nodes(net)})

    def desc(self, ref):
        c = self.comps.get(ref)
        if not c:
            return ""
        return " ".join([c["value"], c["part"], c["descr"], c["footprint"]]).lower()

    def value(self, ref):
        return self.comps.get(ref, {}).get("value", "")

    def find_pad(self, ref, want):
        """resolve a spec pin id to an actual pad name on ref."""
        pins = self.comp_pins.get(ref, [])
        if want == SHIELD:
            for p in pins:
                fn = self.pin_func.get((ref, p), "").lower()
                if re.search(r"shield|shell|mount|^mp", fn) or re.fullmatch(r"(sh|shield|mp\d*|mh\d*)", p.lower()):
                    return p
            # non-numeric pads are the usual shield/mount pads
            nonnum = [p for p in pins if not p.isdigit()]
            if len(nonnum) == 1:
                return nonnum[0]
            return None
        if want in pins:
            return want
        return None

    def pads_matching(self, ref, pattern):
        out = []
        for p in self.comp_pins.get(ref, []):
            fn = self.pin_func.get((ref, p), "")
            if re.search(pattern, fn, re.I) or re.search(pattern, p, re.I):
                out.append(p)
        return out

    def two_pin_bridge(self, ref):
        """nets touched by a 2-pin part, as a set."""
        pins = self.comp_pins.get(ref, [])
        return {self.pin_net[(ref, p)] for p in pins}

    def parts_between(self, net_a, net_b, pred):
        """2-terminal parts bridging two nets and satisfying pred(ref)."""
        out = []
        for ref in self.comps:
            pins = self.comp_pins.get(ref, [])
            if len(pins) != 2:
                continue
            if self.two_pin_bridge(ref) != {net_a, net_b}:
                continue
            if pred(ref):
                out.append(ref)
        return sorted(out)

    def polar_pads(self, ref):
        """(anode_pad, cathode_pad) for diodes/leds."""
        a = k = None
        for p in self.comp_pins.get(ref, []):
            fn = self.pin_func.get((ref, p), "").lower()
            if re.match(r"^(a|anode)(_|\d|$)", fn):
                a = p
            elif re.match(r"^(k|c|cathode)(_|\d|$)", fn):
                k = p
        pins = self.comp_pins.get(ref, [])
        if a is None and "2" in pins:
            a = "2"
        if k is None and "1" in pins:
            k = "1"
        return a, k


# ---------------------------------------------------------------------------
# symbol / footprint pad map
# ---------------------------------------------------------------------------


def pico_pad_map(sym_path):
    """name -> pad number, read from the project-local pico w symbol."""
    with open(sym_path, "r", encoding="utf-8", errors="replace") as fh:
        tree = sx_parse(fh.read())
    best = {}
    for sym in sx_walk(tree, "symbol"):
        pins = list(sx_walk(sym, "pin"))
        if len(pins) < 20:
            continue
        got = {}
        for pin in pins:
            name = sx_val(pin, "name")
            num = sx_val(pin, "number")
            if name and num:
                got[name] = num
        if len(got) > len(best):
            best = got
    return best


def footprint_pads(fp_path):
    try:
        with open(fp_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return None
    return {m for m in re.findall(r'\(pad\s+"([^"]*)"', text) if m}


def gp_pad(padmap, gp):
    pat = re.compile(r"^GPIO%d(_.*)?$" % gp, re.I)
    for name, num in padmap.items():
        if pat.match(name):
            return num
    return None


def named_pad(padmap, name):
    for k, v in padmap.items():
        if k.strip().lower() == name.lower():
            return v
    return None


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


class Report(object):
    def __init__(self):
        self.results = []   # (section, id, ok, message)
        self.notes = []
        self.warns = []
        self.section = "general"

    def sec(self, name):
        self.section = name

    def chk(self, ident, ok, message):
        self.results.append((self.section, ident, bool(ok), message))
        return bool(ok)

    def note(self, msg):
        self.notes.append(msg)

    def warn(self, msg):
        self.warns.append(msg)

    @property
    def failures(self):
        return [r for r in self.results if not r[2]]

    def emit(self):
        order = []
        for sec, _, _, _ in self.results:
            if sec not in order:
                order.append(sec)
        print("")
        for sec in order:
            rows = [r for r in self.results if r[0] == sec]
            bad = [r for r in rows if not r[2]]
            state = "FAIL" if bad else "PASS"
            print("[%s] %s  (%d/%d checks passed)" % (state, sec, len(rows) - len(bad), len(rows)))
            for _, ident, _, msg in bad:
                print("        FAIL %-34s %s" % (ident, msg))
        if self.warns:
            print("")
            print("warnings (not fatal):")
            for w in self.warns:
                print("    ! %s" % w)
        if self.notes:
            print("")
            print("notes:")
            for n in self.notes:
                print("    - %s" % n)
        total = len(self.results)
        bad = len(self.failures)
        print("")
        print("summary: %d assertions, %d passed, %d FAILED" % (total, total - bad, bad))
        print("RESULT: %s" % ("PASS" if bad == 0 else "FAIL"))


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------


def parse_config_block(path):
    """extract the BOARD_HIDPICO_REV6 preprocessor block from config.h."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"\s*#\s*(el)?if\s+defined\s*\(\s*BOARD_HIDPICO_REV6\s*\)", line):
            start = i + 1
            break
    if start is None:
        return None
    depth = 0
    block = []
    for line in lines[start:]:
        s = line.strip()
        if re.match(r"#\s*if", s):
            depth += 1
        elif re.match(r"#\s*endif", s):
            if depth == 0:
                break
            depth -= 1
        elif depth == 0 and re.match(r"#\s*(elif|else)\b", s):
            break
        block.append(line)
    return block


def check_netlist_sanity(rep, nl):
    """distinct nets that normalise to one name would hide a real disconnection."""
    rep.sec("0. netlist sanity")
    clashes = ["%s <- %s" % (k, sorted(v)) for k, v in sorted(nl.aliases.items()) if len(v) > 1]
    rep.chk("0.no_name_collisions", not clashes,
            "distinct nets collapse to the same normalised name (rename one): "
            + "; ".join(clashes[:6]))


def check_config(rep, config_path):
    rep.sec("A. src/config.h BOARD_HIDPICO_REV6 block")
    block = parse_config_block(config_path)
    if block is None:
        rep.chk("A.block", False, "no BOARD_HIDPICO_REV6 block found in %s" % config_path)
        return
    rep.chk("A.block", True, "")

    defines = {}
    flags = set()
    for line in block:
        m = re.match(r"\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(-?\d+)", line)
        if m:
            defines[m.group(1)] = int(m.group(2))
            flags.add(m.group(1))
            continue
        m = re.match(r"\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s*(//.*)?$", line)
        if m:
            flags.add(m.group(1))
            continue
        m = re.match(r"\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(\S+)", line)
        if m:
            flags.add(m.group(1))

    for name, want in sorted(CONFIG_PINS.items()):
        got = defines.get(name)
        rep.chk("A.%s" % name, got == want,
                "expected %s == %d, got %s" % (name, want, got if got is not None else "undefined"))

    for name in CONFIG_FLAGS:
        rep.chk("A.%s" % name, name in flags, "%s is not defined in the REV6 block" % name)

    for name in CONFIG_FORBIDDEN:
        rep.chk("A.no_%s" % name, name not in flags,
                "%s must not be defined for REV6 (vestigial)" % name)

    rep.chk("A.port2_role_guard",
            bool(re.search(r"#\s*error", "".join(block))) and "PORT2_ROLE_KEYBOARD" in "".join(block),
            "REV6 block must #error when PORT2_ROLE_KEYBOARD is requested")

    present = [n for n in CONFIG_OPTIONAL_PINS if n in defines]
    if present:
        for name in sorted(present):
            want = CONFIG_OPTIONAL_PINS[name]
            rep.chk("A.%s" % name, defines[name] == want,
                    "expected %s == %d, got %s" % (name, want, defines[name]))
    else:
        rep.note("config.h has no QM2_* port-2 defines (no port-2 emulation yet); "
                 "spec pins 18/19/20/21/22/26/27 checked against the schematic only")


def check_padmap(rep, padmap, fppads):
    rep.sec("B. pico w symbol / footprint pad map")
    if not padmap:
        rep.chk("B.symbol", False, "could not read any pin map from the rev6 symbol library")
        return {}
    rep.chk("B.symbol", True, "")

    resolved = {}
    for gp in sorted(GPIO_SPEC):
        pad = gp_pad(padmap, gp)
        ok = rep.chk("B.GP%d" % gp, pad is not None,
                     "symbol has no pin named GPIO%d" % gp)
        if ok:
            resolved["GP%d" % gp] = pad

    for name, want in sorted(MODULE_PIN.items()):
        pad = named_pad(padmap, name)
        rep.chk("B.%s" % name, pad == str(want),
                "symbol pin %s should be module pad %d, got %s" % (name, want, pad))
        if pad:
            resolved[name] = pad

    for name in ("SWCLK", "SWDIO", "TP2", "TP3"):
        pad = named_pad(padmap, name)
        ok = rep.chk("B.%s" % name, pad is not None,
                     "symbol has no %s pin (extend the U1 symbol so the netlist captures it)" % name)
        if ok:
            resolved[name] = pad

    if fppads is None:
        rep.warn("footprint %s not readable; pad existence not cross-checked" % DEF_FP)
    else:
        missing = sorted({p for p in resolved.values() if p not in fppads})
        rep.chk("B.footprint_pads", not missing,
                "footprint lacks pad(s) %s used by the symbol" % ", ".join(missing))
    return resolved


def check_u1(rep, nl, pads):
    rep.sec("C. U1 (pico w) pad -> net")
    if not nl.has("U1"):
        rep.chk("C.U1", False, "no component U1 in the netlist")
        return {}
    rep.chk("C.U1", True, "")
    rep.chk("C.U1_is_picow", "pico" in nl.desc("U1") and "w" in nl.desc("U1"),
            "U1 should be the pico w module (value/footprint: %r)" % nl.comps["U1"]["footprint"])

    # the netlist's own pinfunctions must agree with the symbol library
    mismatches = []
    for key, pad in pads.items():
        fn = nl.pin_func.get(("U1", pad), "")
        base = re.sub(r"_%s$" % re.escape(pad), "", fn)
        want = key.replace("GP", "GPIO") if key.startswith("GP") else key
        if base and not re.match(r"^%s(_.*)?$" % re.escape(want), base, re.I):
            mismatches.append("pad %s is %r, expected %s" % (pad, base, want))
    rep.chk("C.symbol_matches_sch", not mismatches,
            "U1 in the schematic does not use the rev6 pico w symbol: " + "; ".join(mismatches[:6]))

    low_nets = {}
    for gp in sorted(GPIO_SPEC):
        role, shifted, high = GPIO_SPEC[gp]
        pad = pads.get("GP%d" % gp)
        if pad is None:
            rep.chk("C.GP%d" % gp, False, "no pad known for GP%d" % gp)
            continue
        net = nl.net_of("U1", pad)
        if net is None or is_nc(net):
            rep.chk("C.GP%d" % gp, False,
                    "GP%d (pad %s, %s) is unconnected" % (gp, pad, role))
            continue
        if shifted:
            low_nets[gp] = net
            rep.chk("C.GP%d" % gp, True, "")
        elif role in ("uart_tx", "uart_rx", "i2c_sda", "i2c_scl"):
            rep.chk("C.GP%d" % gp, net == high,
                    "GP%d should be on net %s, found %s" % (gp, high, nl.net_raw.get(net, net)))
        else:
            low_nets[gp] = net
            rep.chk("C.GP%d" % gp, True, "")

    # explicit module rails
    vsys = pads.get("VSYS")
    if vsys:
        rep.chk("C.VSYS", nl.net_of("U1", vsys) == "sys5v",
                "VSYS (pad %s) must be on SYS5V, found %s"
                % (vsys, nl.net_raw.get(nl.net_of("U1", vsys), nl.net_of("U1", vsys))))
    v3v3 = pads.get("3V3")
    if v3v3:
        rep.chk("C.3V3", nl.net_of("U1", v3v3) == "3v3",
                "pad %s (3V3) must be on +3V3, found %s"
                % (v3v3, nl.net_raw.get(nl.net_of("U1", v3v3), nl.net_of("U1", v3v3))))
    vbus = pads.get("VBUS")
    if vbus:
        net = nl.net_of("U1", vbus)
        alone = net is not None and len(nl.nodes(net)) == 1
        rep.chk("C.VBUS_nc", net is None or (is_nc(net) and alone),
                "VBUS (pad %s) must have no net, found %s"
                % (vbus, nl.net_raw.get(net, net)))

    for name, jpin in (("SWDIO", "4"), ("SWCLK", "6")):
        pad = pads.get(name)
        if pad is None:
            continue
        net = nl.net_of("U1", pad)
        jn = nl.net_of("J2", jpin)
        rep.chk("C.%s" % name, net is not None and not is_nc(net) and net == jn,
                "%s (pad %s) must share a net with J2.%s (%s vs %s)"
                % (name, pad, jpin, nl.net_raw.get(net, net), nl.net_raw.get(jn, jn)))

    for name, want in (("TP2", "usb_dm"), ("TP3", "usb_dp")):
        pad = pads.get(name)
        if pad is None:
            continue
        net = nl.net_of("U1", pad)
        rep.chk("C.%s" % name, net == want,
                "%s (pad %s) must be on %s, found %s" % (name, pad, want, nl.net_raw.get(net, net)))

    gnd_pads = [p for p, n in ((p, nl.pin_func.get(("U1", p), "")) for p in nl.comp_pins.get("U1", []))
                if re.match(r"^A?GND", n, re.I)]
    bad = [p for p in gnd_pads if nl.net_of("U1", p) != "gnd"]
    rep.chk("C.GND_pads", not bad, "U1 ground pads not on GND: %s" % ", ".join(bad))

    return low_nets


def is_bss138(nl, ref):
    return "bss138" in nl.desc(ref)


def is_res(nl, ref, ohms):
    return ref.upper().startswith("R") and near(parse_res(nl.value(ref)), ohms)


def check_shifters(rep, nl, low_nets):
    rep.sec("D. bss138 level-shift channels (19)")
    bss = sorted(r for r in nl.comps if is_bss138(nl, r))
    rep.chk("D.count", len(bss) == 19, "expected 19 BSS138, found %d (%s)"
            % (len(bss), ", ".join(bss) if bss else "none"))

    used = set()
    for gp in SHIFT_CHANNELS:
        role, _, high = GPIO_SPEC[gp]
        low = low_nets.get(gp)
        if low is None:
            rep.chk("D.%s" % role, False, "no low-side net for GP%d (%s)" % (gp, role))
            continue

        cands = []
        for ref in bss:
            spads = nl.pads_matching(ref, r"^S")
            if any(nl.net_of(ref, p) == low for p in spads):
                cands.append(ref)
        if len(cands) != 1:
            rep.chk("D.%s.fet" % role, False,
                    "expected exactly 1 BSS138 with source on the GP%d net (%s), found %d %s"
                    % (gp, nl.net_raw.get(low, low), len(cands), cands))
            continue
        q = cands[0]
        used.add(q)
        rep.chk("D.%s.fet" % role, True, "")

        gpads = nl.pads_matching(q, r"^G")
        rep.chk("D.%s.gate" % role,
                bool(gpads) and all(nl.net_of(q, p) == "3v3" for p in gpads),
                "%s gate must be on +3V3" % q)

        dpads = nl.pads_matching(q, r"^D")
        dnets = {nl.net_of(q, p) for p in dpads}
        rep.chk("D.%s.drain" % role, dnets == {high},
                "%s drain must be on %s, found %s"
                % (q, high, ", ".join(nl.net_raw.get(n, str(n)) for n in dnets) or "nothing"))

        lo_pu = nl.parts_between(low, "3v3", lambda r: is_res(nl, r, 10e3))
        rep.chk("D.%s.pullup_lo" % role, len(lo_pu) == 1,
                "expected one 10k from the GP%d net to +3V3, found %s" % (gp, lo_pu or "none"))

        hi_pu = nl.parts_between(high, "sys5v", lambda r: is_res(nl, r, 10e3))
        rep.chk("D.%s.pullup_hi" % role, len(hi_pu) == 1,
                "expected one 10k from %s to SYS5V, found %s" % (high, hi_pu or "none"))

    stray = sorted(set(bss) - used)
    rep.chk("D.no_stray_fets", not stray,
            "BSS138 not bound to a spec channel: %s" % ", ".join(stray))


def check_connectors(rep, nl, low_nets):
    rep.sec("E. connector pinouts")
    for ref in sorted(CONNECTORS, key=lambda r: (r[0], int(re.sub(r"\D", "", r) or 0))):
        table = CONNECTORS[ref]
        if not nl.has(ref):
            rep.chk("E.%s" % ref, False, "connector %s is missing from the schematic" % ref)
            continue
        rep.chk("E.%s" % ref, True, "")
        for want_pin, want_net in sorted(table.items()):
            pad = nl.find_pad(ref, want_pin)
            ident = "E.%s.%s" % (ref, want_pin)
            if pad is None:
                rep.chk(ident, False, "%s has no pad %s" % (ref, want_pin))
                continue
            got = nl.net_of(ref, pad)
            if want_net is NC:
                alone = got is not None and len(nl.nodes(got)) == 1
                rep.chk(ident, got is None or (is_nc(got) and alone),
                        "%s.%s must be a no-connect, found %s" % (ref, pad, nl.net_raw.get(got, got)))
            else:
                rep.chk(ident, got == want_net,
                        "%s.%s must be on %s, found %s"
                        % (ref, pad, want_net, nl.net_raw.get(got, got)))

    # J7 pin 1 carries the GP28 net (auto-named, so compare by identity)
    if nl.has("J7"):
        gp28 = low_nets.get(28)
        j7 = nl.net_of("J7", "1")
        rep.chk("E.J7.1", gp28 is not None and j7 == gp28,
                "J7.1 must share the GP28 net (GP28=%s, J7.1=%s)"
                % (nl.net_raw.get(gp28, gp28), nl.net_raw.get(j7, j7)))

    # the reset wire-or: J1.3 and J8.3 are the same net
    if nl.has("J1") and nl.has("J8"):
        rep.chk("E.reset_wire_or",
                nl.net_of("J1", "3") == nl.net_of("J8", "3") == "kbreset",
                "J1.3 and J8.3 must both be the kbreset net")

    # keyboard led pass-through: J1.7/J8.7 and J1.8/J8.8 are copper-only pairs
    if nl.has("J1") and nl.has("J8"):
        rep.chk("E.led_passthrough",
                nl.net_of("J1", "7") == nl.net_of("J8", "7") == "kb_pwrled"
                and nl.net_of("J1", "8") == nl.net_of("J8", "8") == "kb_drvled",
                "J1/J8 pins 7 and 8 must pair up on kb_pwrled / kb_drvled")


def check_power(rep, nl, low_nets):
    rep.sec("F. power tree")

    def two_pin_nets(ref):
        return nl.two_pin_bridge(ref) if nl.has(ref) else set()

    # F1: AMIGA_5V -> D1 anode; D1 cathode = SYS5V
    if not nl.has("F1"):
        rep.chk("F.F1", False, "F1 (amiga 5v polyfuse) missing")
        mid1 = None
    else:
        nets = two_pin_nets("F1")
        rep.chk("F.F1", "amiga_5v" in nets and len(nets) == 2,
                "F1 must bridge AMIGA_5V and the D1 anode node, found %s" % sorted(nets))
        mid1 = next(iter(nets - {"amiga_5v"}), None) if "amiga_5v" in nets else None
        if "polyfuse" not in nl.desc("F1") and "fuse" not in nl.desc("F1"):
            rep.warn("F1 value %r does not look like a polyfuse" % nl.value("F1"))
        if not re.search(r"750\s*ma|0\.?75\s*a", nl.value("F1"), re.I):
            rep.warn("F1 value %r does not state the 750 mA hold current" % nl.value("F1"))

    if not nl.has("D1"):
        rep.chk("F.D1", False, "D1 (SS34 schottky from the amiga rail) missing")
    else:
        a, k = nl.polar_pads("D1")
        rep.chk("F.D1", a is not None and k is not None, "cannot identify D1 anode/cathode pads")
        if a and k:
            rep.chk("F.D1.anode", mid1 is not None and nl.net_of("D1", a) == mid1,
                    "D1 anode must be on the F1 output node (%s), found %s"
                    % (nl.net_raw.get(mid1, mid1), nl.net_raw.get(nl.net_of("D1", a), nl.net_of("D1", a))))
            rep.chk("F.D1.cathode", nl.net_of("D1", k) == "sys5v",
                    "D1 cathode must be SYS5V, found %s"
                    % nl.net_raw.get(nl.net_of("D1", k), nl.net_of("D1", k)))
        rep.chk("F.D1.part", "ss34" in nl.desc("D1") or "schottky" in nl.desc("D1"),
                "D1 should be an SS34 schottky, value is %r" % nl.value("D1"))

    # D2: usb-c VBUS -> SYS5V
    if not nl.has("D2"):
        rep.chk("F.D2", False, "D2 (schottky from the usb-c aux input) missing")
    else:
        a, k = nl.polar_pads("D2")
        rep.chk("F.D2", a is not None and k is not None, "cannot identify D2 anode/cathode pads")
        if a and k:
            anet = nl.net_of("D2", a)
            rep.chk("F.D2.cathode", nl.net_of("D2", k) == "sys5v",
                    "D2 cathode must be SYS5V, found %s"
                    % nl.net_raw.get(nl.net_of("D2", k), nl.net_of("D2", k)))
            if nl.has("J13"):
                vbus_pads = nl.pads_matching("J13", r"vbus")
                vnets = {nl.net_of("J13", p) for p in vbus_pads}
                rep.chk("F.D2.anode", bool(vbus_pads) and vnets == {anet},
                        "D2 anode must be the J13 VBUS node; J13 VBUS pads on %s, D2 anode on %s"
                        % (sorted(nl.net_raw.get(n, str(n)) for n in vnets), nl.net_raw.get(anet, anet)))

    # F2 / F3 branches
    for fref, dest, rating in (("F2", "usba_5v", "500"), ("F3", "kbin_5v", "200")):
        if not nl.has(fref):
            rep.chk("F.%s" % fref, False, "%s polyfuse (SYS5V -> %s) missing" % (fref, dest.upper()))
            continue
        nets = two_pin_nets(fref)
        rep.chk("F.%s" % fref, nets == {"sys5v", dest},
                "%s must bridge SYS5V and %s, found %s" % (fref, dest.upper(), sorted(nets)))
        if not re.search(rating, nl.value(fref)):
            rep.warn("%s value %r does not state the %s mA hold current" % (fref, nl.value(fref), rating))

    # usb-c CC pulldowns
    if nl.has("J13"):
        for cc in ("cc1", "cc2"):
            pads = nl.pads_matching("J13", r"^%s" % cc)
            if not pads:
                rep.chk("F.J13.%s" % cc, False, "J13 has no %s pad" % cc.upper())
                continue
            ccnet = nl.net_of("J13", pads[0])
            rs = nl.parts_between(ccnet, "gnd", lambda r: is_res(nl, r, 5.1e3))
            rep.chk("F.J13.%s" % cc, len(rs) == 1,
                    "expected one 5.1k from %s to GND, found %s" % (cc.upper(), rs or "none"))
        gpads = nl.pads_matching("J13", r"gnd|shield|shell")
        bad = [p for p in gpads if nl.net_of("J13", p) != "gnd"]
        rep.chk("F.J13.gnd", bool(gpads) and not bad,
                "J13 ground/shell pads must be on GND (offending: %s)" % ", ".join(bad))
    else:
        rep.chk("F.J13", False, "J13 (usb-c power-only receptacle) missing")

    # bulk / decoupling
    def cap_between(net, farads, at_least=False):
        out = []
        for ref in nl.comps:
            if not ref.upper().startswith("C"):
                continue
            if nl.two_pin_bridge(ref) != {net, "gnd"}:
                continue
            val = parse_cap(nl.value(ref))
            if val is None:
                continue
            if (val >= farads * 0.95) if at_least else near(val, farads):
                out.append(ref)
        return sorted(out)

    rep.chk("F.bulk_sys5v", bool(cap_between("sys5v", 220e-6)),
            "no 220uF bulk cap between SYS5V and GND")
    rep.chk("F.decouple_10u", bool(cap_between("sys5v", 10e-6)),
            "no 10uF decoupling cap between SYS5V and GND")
    rep.chk("F.decouple_100n", bool(cap_between("sys5v", 100e-9)),
            "no 100nF decoupling cap between SYS5V and GND")
    rep.chk("F.bulk_usba", bool(cap_between("usba_5v", 150e-6, at_least=True)),
            "no >=150uF bulk cap between USBA_5V and GND (usb host requirement)")

    # rails: membership and sources
    rep.chk("F.sys5v_exists", "sys5v" in nl.net_nodes, "no SYS5V net in the design")
    rep.chk("F.amiga5v_exists", "amiga_5v" in nl.net_nodes, "no AMIGA_5V net in the design")
    rep.chk("F.kbin5v_exists", "kbin_5v" in nl.net_nodes, "no KBIN_5V net in the design")
    rep.chk("F.usba5v_exists", "usba_5v" in nl.net_nodes, "no USBA_5V net in the design")

    # +3V3 is sourced only by U1 pin 36
    supply_refs = {"F1", "F2", "F3", "D1", "D2", "J13", "J4"}
    on3v3 = set(nl.refs_on("3v3"))
    rep.chk("F.3v3_sole_source", not (on3v3 & supply_refs),
            "+3V3 must come only from U1 pin 36; also touched by %s"
            % ", ".join(sorted(on3v3 & supply_refs)))
    rep.chk("F.3v3_has_u1", "U1" in on3v3, "+3V3 does not reach U1")
    rep.chk("F.3v3_no_5v_bridge", not nl.parts_between("3v3", "sys5v", lambda r: True),
            "direct part bridging +3V3 and SYS5V")

    # i2c pull-ups
    for line in ("i2c_sda", "i2c_scl"):
        rs = nl.parts_between(line, "3v3", lambda r: is_res(nl, r, 4.7e3))
        rep.chk("F.pullup_%s" % line, len(rs) == 1,
                "expected one 4.7k from %s to +3V3, found %s" % (line, rs or "none"))

    # usb esd
    usblc = sorted(r for r in nl.comps if "usblc6" in nl.desc(r))
    if len(usblc) != 1:
        rep.chk("F.usblc6", False, "expected exactly one USBLC6-2SC6, found %s" % (usblc or "none"))
    else:
        u = usblc[0]
        nets = {nl.net_of(u, p) for p in nl.comp_pins.get(u, [])}
        for want in ("usb_dp", "usb_dm", "usba_5v", "gnd"):
            rep.chk("F.usblc6.%s" % want, want in nets,
                    "%s (USBLC6) is not connected to %s" % (u, want))

    # led chains: GP16/GP17 -> 1k -> LEDn -> GND (active high)
    for gp, led in ((16, "LED1"), (17, "LED2")):
        ident = "F.%s" % led
        if not nl.has(led):
            rep.chk(ident, False, "%s missing" % led)
            continue
        a, k = nl.polar_pads(led)
        if a is None or k is None:
            rep.chk(ident, False, "cannot identify %s anode/cathode" % led)
            continue
        gp_net = low_nets.get(gp)
        anet, knet = nl.net_of(led, a), nl.net_of(led, k)
        rep.chk(ident, True, "")
        # the 1k may sit on either side of the led; anode side must reach the
        # gpio and the cathode side must reach GND
        if knet == "gnd":
            rs = nl.parts_between(gp_net, anet, lambda r: is_res(nl, r, 1e3)) if gp_net else []
            rep.chk("%s.chain" % ident, len(rs) == 1,
                    "expected one 1k from the GP%d net (%s) to the %s anode, found %s"
                    % (gp, nl.net_raw.get(gp_net, gp_net), led, rs or "none"))
        elif anet == gp_net:
            rs = nl.parts_between(knet, "gnd", lambda r: is_res(nl, r, 1e3))
            rep.chk("%s.chain" % ident, len(rs) == 1,
                    "expected one 1k from the %s cathode to GND, found %s" % (led, rs or "none"))
        else:
            rep.chk("%s.chain" % ident, False,
                    "%s is not in a GP%d -> 1k -> LED -> GND chain (anode on %s, cathode on %s)"
                    % (led, gp, nl.net_raw.get(anet, anet), nl.net_raw.get(knet, knet)))

    # JP1 solder jumper: kb_pwrled <-> SYS5V
    if not nl.has("JP1"):
        rep.chk("F.JP1", False, "JP1 (kb_pwrled to SYS5V solder jumper) missing")
    else:
        nets = {nl.net_of("JP1", p) for p in nl.comp_pins.get("JP1", [])}
        rep.chk("F.JP1", nets == {"kb_pwrled", "sys5v"},
                "JP1 must bridge kb_pwrled and SYS5V, found %s"
                % sorted(nl.net_raw.get(n, str(n)) for n in nets))
        if "jumper" not in nl.desc("JP1"):
            rep.warn("JP1 %r does not look like a solder jumper" % nl.value("JP1"))

    # rail fan-out: exactly 19 gates and 19+19 pull-ups
    gates = [r for r in nl.comps if is_bss138(nl, r)
             and all(nl.net_of(r, p) == "3v3" for p in nl.pads_matching(r, r"^G"))
             and nl.pads_matching(r, r"^G")]
    rep.chk("F.gates_on_3v3", len(gates) == 19,
            "expected 19 BSS138 gates on +3V3, found %d" % len(gates))
    lo = [r for r in nl.comps if is_res(nl, r, 10e3) and "3v3" in nl.two_pin_bridge(r)]
    hi = [r for r in nl.comps if is_res(nl, r, 10e3) and "sys5v" in nl.two_pin_bridge(r)]
    rep.chk("F.pullups_3v3", len(lo) == 19,
            "expected 19 low-side 10k pull-ups to +3V3, found %d" % len(lo))
    rep.chk("F.pullups_sys5v", len(hi) == 19,
            "expected 19 high-side 10k pull-ups to SYS5V, found %d" % len(hi))


ESD_PATTERN = r"pesd|tvs|esd|smf\d|cdsot|pgb1|sp05|d5v0|esda|semtech|clamp"


def check_esd(rep, nl):
    rep.sec("G. esd clamps on amiga-facing lines")
    clamps = sorted(r for r in nl.comps
                    if re.search(ESD_PATTERN, nl.desc(r)) and "usblc6" not in nl.desc(r))
    rep.chk("G.count", len(clamps) >= 19,
            "expected >=19 ground-clamp TVS parts, found %d (%s)"
            % (len(clamps), ", ".join(clamps) if clamps else "none"))
    for line in ESD_LINES:
        found = []
        for ref in clamps:
            nets = {nl.net_of(ref, p) for p in nl.comp_pins.get(ref, [])}
            if line in nets and "gnd" in nets:
                found.append(ref)
        rep.chk("G.%s" % line, bool(found),
                "no TVS clamp between %s and GND" % line)
    # rail-steering arrays would phantom-power sys5v; forbid clamps touching 5v rails
    steering = [r for r in clamps
                if {"sys5v", "amiga_5v", "usba_5v", "kbin_5v", "3v3"}
                & {nl.net_of(r, p) for p in nl.comp_pins.get(r, [])}]
    rep.chk("G.no_rail_steering", not steering,
            "ground-clamp-only TVS required; these touch a supply rail: %s" % ", ".join(steering))


def check_nc_flags(rep, nl, sch_path):
    rep.sec("H. explicit no-connect flags")
    sch_dir = os.path.dirname(os.path.abspath(sch_path))
    total = 0
    files = []
    for name in sorted(os.listdir(sch_dir)):
        if name.endswith(".kicad_sch"):
            path = os.path.join(sch_dir, name)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            n = len(re.findall(r"\(no_connect\b", text))
            total += n
            files.append("%s:%d" % (name, n))
    # spec no-connects: J1.5 J8.5 J9.3 J10.2 J10.6 J11.3 J12.2 J12.6 P1.7 P2.7 VBUS
    rep.chk("H.count", total >= 11,
            "expected >=11 no-connect flags across %s, found %d (%s)"
            % (sch_dir, total, ", ".join(files) or "no sheets"))
    # every pin the netlist reports as unconnected needs one of those flags
    floating = sorted(n for n in nl.net_nodes if is_nc(n))
    rep.chk("H.every_nc_flagged", total >= len(floating),
            "%d unconnected pins but only %d no-connect flags: %s"
            % (len(floating), total, ", ".join(floating[:8])))


def check_rev5_untouched(rep, repo, enabled):
    rep.sec("I. rev5 files untouched")
    if not enabled:
        rep.note("rev5 git check skipped (--no-git)")
        return
    try:
        out = subprocess.run(
            ["git", "-C", repo, "diff", "--stat", "HEAD", "--"] + REV5_GUARDED,
            capture_output=True, text=True, check=False)
    except OSError as exc:
        rep.chk("I.git", False, "cannot run git: %s" % exc)
        return
    rep.chk("I.rev5_sch_pcb", out.returncode == 0 and not out.stdout.strip(),
            "rev5 schematic/pcb modified:\n%s" % out.stdout.strip())
    wide = subprocess.run(
        ["git", "-C", repo, "diff", "--stat", "HEAD", "--"] + REV5_GUARDED_WIDE,
        capture_output=True, text=True, check=False)
    if wide.stdout.strip():
        rep.warn("other rev5 files differ from HEAD:\n      %s"
                 % wide.stdout.strip().replace("\n", "\n      "))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def export_netlist(sch, out):
    cmd = [KICAD_CLI, "sch", "export", "netlist", "--output", out,
           "--format", "kicadsexpr", sch]
    print("running: %s" % " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True, cwd="/tmp", check=False)
    if res.returncode != 0:
        sys.stderr.write(res.stdout + res.stderr)
    return res.returncode == 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="cross-check the rev6 netlist against the rev6 spec")
    ap.add_argument("netlist", nargs="?", help="existing netlist to check (default: export from the schematic)")
    ap.add_argument("--sch", default=DEF_SCH, help="rev6 schematic (default: %s)" % DEF_SCH)
    ap.add_argument("--sym", default=DEF_SYM, help="rev6 symbol library holding the pico w symbol")
    ap.add_argument("--fp", default=DEF_FP, help="pico w footprint")
    ap.add_argument("--config", default=DEF_CONFIG, help="src/config.h")
    ap.add_argument("--repo", default=REPO_ROOT, help="repository root")
    ap.add_argument("--out", default=DEF_NET, help="netlist export path (default: %s)" % DEF_NET)
    ap.add_argument("--no-git", action="store_true", help="skip the rev5-untouched git check")
    args = ap.parse_args(argv)

    print("=== amigahid-pico rev6 netlist checker ===")
    print("schematic : %s" % args.sch)
    print("config.h  : %s" % args.config)

    netlist_path = args.netlist
    if netlist_path is None:
        if not os.path.exists(args.sch):
            print("\nFATAL: schematic not found: %s" % args.sch)
            return 2
        if not export_netlist(args.sch, args.out):
            print("\nFATAL: kicad-cli netlist export failed")
            return 2
        netlist_path = args.out
    print("netlist   : %s" % netlist_path)

    rep = Report()

    try:
        nl = Netlist(netlist_path)
    except (OSError, ValueError) as exc:
        print("\nFATAL: cannot read netlist %s: %s" % (netlist_path, exc))
        return 2
    print("parsed    : %d components, %d nets" % (len(nl.comps), len(nl.net_nodes)))

    try:
        padmap = pico_pad_map(args.sym)
    except (OSError, ValueError) as exc:
        padmap = {}
        rep.warn("cannot read symbol library %s: %s" % (args.sym, exc))
    fppads = footprint_pads(args.fp)

    check_netlist_sanity(rep, nl)
    check_config(rep, args.config)
    pads = check_padmap(rep, padmap, fppads)
    low_nets = check_u1(rep, nl, pads)
    check_shifters(rep, nl, low_nets)
    check_connectors(rep, nl, low_nets)
    check_power(rep, nl, low_nets)
    check_esd(rep, nl)
    check_nc_flags(rep, nl, args.sch)
    check_rev5_untouched(rep, args.repo, not args.no_git)

    rep.emit()
    return 0 if not rep.failures else 1


if __name__ == "__main__":
    sys.exit(main())
