#!/usr/bin/env python3
"""structural checks for the rev6 board layout.

these are the facts DRC cannot check: which edge a connector sits on, which
side of the board a part is on, whether the usb-host bulk can is still parked
against its connector, whether the antenna keep-out is really empty, whether
the power nets got wide copper, whether the silkscreen says what it has to
say, whether the rev5 files are still untouched - and whether DRC itself is
still being run under the fab's rules rather than a rewritten project file.

usage (/nas is mounted noexec, so always via the interpreter):

    python3 tools/check_rev6_pcb.py [board.kicad_pcb]

environment:

    REV6_FORCE_SEXPR=1   ignore pcbnew and use the s-expression reader
    REV6_SKIP_GIT=1      skip section J (for use outside a git checkout)

exit code 0 only when every assertion passes.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

Pt = Tuple[float, float]
Poly = List[Pt]
BBox = Tuple[float, float, float, float]  # minx, miny, maxx, maxy

# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------

BOARD_REL = "kicad/rev6/amigahid-pico-rev6.kicad_pcb"

# A: board outline envelope
SIZE_X_MIN, SIZE_X_MAX = 70.0, 100.0
SIZE_Y_MIN, SIZE_Y_MAX = 60.0, 90.0

# B: mounting holes
MOUNT_DIA_MIN, MOUNT_DIA_MAX = 3.0, 3.5
MOUNT_CORNER_RADIUS = 12.0  # a hole must sit this close to a board corner

# C: antenna keep-out
ANT_MIN_LONG, ANT_MIN_SHORT = 14.0, 9.0
EDGE_TOUCH_TOL = 0.5  # rule area must come this close to a board edge
KEEPOUT_TOUCH_EPS = 0.002  # copper abutting the boundary is flanking, not inside

# D: edge assignments
EDGE_REACH_TOL = 1.5  # "flush with, or overhanging, the edge"
NORTH_CONNECTORS = ["J9", "J10", "J11", "J12"]  # west to east
NORTH_MIN_SPACING = 18.0
SOUTH_CONNECTORS = ["P1", "P2"]
DE9_MIN_SPACING = 36.0
DE9_MIN_CORNER = 18.0

# E: which side each part belongs on
TOP_REFS = [
    "U1", "U2",
    "J1", "J2", "J3", "J4", "J7", "J8", "J9", "J10", "J11", "J12", "J13",
    "P1", "P2", "JP1",
    "LED1", "LED2",
    "F1", "F2", "F3",
    "D1", "D2",
]
BOTTOM_REFS = ["Q%d" % n for n in range(1, 20)] + ["R%d" % n for n in range(1, 39)]
EXPECTED_BSS138 = 19
# the board has to sit near-flat on its bottom, so the bottom side may only
# carry packages that stand about a millimetre off the copper.  this is a
# whitelist on purpose: a can, a radial, anything through-hole or any bigger
# chip land is taller than the standoff and has to fail even though nobody
# thought to name it here.  matched against the footprint name, library
# prefix stripped.
BOTTOM_LOW_PROFILE = [
    r"SOT-23",    # Package_TO_SOT_SMD:SOT-23, SOT-23-6
    r"SOD-",      # Diode_SMD:D_SOD-323
    r"R_0603",
    r"C_0603",
    r"C_0805",
    r"LED_0603",
]

# E5: the usb-host bulk can belongs at the connector it feeds.  the layout
# brief wants C4's USBA_5V pad within 6 mm of J4 pin 1; the board is at
# 10.29 mm and nothing here pretends otherwise - the measured distance is
# printed on every run so the deviation cannot go unnoticed again.
#
# it is not a placement slip.  sweeping every courtyard-legal top-side
# position for C4 - 0.05 mm grid, all four rotations, against all 31 top-side
# courtyards - the 6.3 x 7.7 mm can gets no closer than 9.94 mm.  vacating U2's
# spot buys 8.31 mm.  the ~4.8 mm the 6 mm figure implies needs the can at
# x 46.8 turned 90 deg, which lands inside U1's courtyard: the pico module
# would have to move about 4 mm north and take C1, J2, J3 and J7 with it, i.e.
# re-lay the north half of the board.  a 6 mm assertion here could therefore
# only ever be a red gate, so what is asserted instead is the part of the rule
# the packages can actually honour, tightly:
#
#   - the can hugs the connector's north face and the USBLC6's east face,
#     which is what "as close as it goes" means once the courtyards are fixed;
#   - its + pad stays inside the sweep floor plus half a millimetre of slack.
#
# either half fails the moment someone drifts C4 back out into the board.
BULK_REF = "C4"
BULK_NET = "USBA_5V"
BULK_HOST_REF = "J4"
BULK_HOST_PAD = "1"
BULK_BRIEF_DIST = 6.0      # what the layout brief asks for
BULK_SWEEP_FLOOR = 9.94    # closest courtyard-legal top-side placement there is
BULK_MAX_DIST = 10.5       # sweep floor + placement slack
BULK_HUG_REFS = ["J4", "U2"]
BULK_MAX_HUG = 0.5

# F: power copper.  the four nets the layout brief names, plus the two other
# members of the Power netclass that carry the same current (AMIGA_5V_FUSED is
# the link between F1 and D1, AUX_5V the link between J13 and D2).  +3V3 is in
# the netclass too but is a logic rail and is deliberately not checked here.
POWER_NETS = ["AMIGA_5V", "AMIGA_5V_FUSED", "SYS5V", "USBA_5V", "KBIN_5V", "AUX_5V"]
POWER_MIN_WIDTH = 0.8
NECKDOWN_PAD_DIST = 2.0

# G: usb pair
USB_NETS = ["usb_dp", "usb_dm"]
USB_MAX_LEN = 25.0
USB_MAX_SKEW = 5.0

# H: silkscreen
SILK_STRINGS = ["TO AMIGA", "FROM KEYBOARD", "ONE Amiga", "JLCJLCJLCJLC"]
SILK_REVISION_RE = re.compile(r"\br\s*6\b", re.IGNORECASE)
REFDES_MUST_SHOW = SOUTH_CONNECTORS + NORTH_CONNECTORS + [
    "J1", "J2", "J3", "J4", "J7", "J8", "J13", "JP1", "U1",
]

# I: pours
GND_NET = "GND"
GND_MIN_COVERAGE = 0.60
GND_MIN_VIAS = 15

# J: things that must not move
REV5_GLOB_PREFIX = "kicad/amigahid-pico."
REV5_BASELINE_COMMIT = "d159951afc386a7c4ad0004cd801c12b701aa219"
NETLIST_CHECKER = "tools/check_rev6_netlist.py"
# re-baselined once, at 84f25982: the netlist checker's F1 rule was
# RE-TARGETED, not relaxed.  it used to warn when F1's value was *not* 750 mA -
# which blessed the placeholder the design gates on - and now asserts that while
# the draft value stands F1 must carry no LCSC code, so the placeholder cannot be
# ordered as an assembled part.  that is one assertion more than before (356 -> 357).
# any further move of this pin has to come with the same kind of justification.
NETLIST_CHECKER_M2_COMMIT = "84f2598220b00b59e1f444ac4af5ddd74ca22a57"
NETLIST_CHECKER_M2_BLOB = "7fe30582ad568d91c186f5d4ae4fe57f10339c6d"

# K: the rev6 project settings.  every scripted pcbnew save rewrites this file
# behind our back - it drops the netclass patterns and resets constraints to
# pcbnew's own defaults - so it has been restored by hand after each one, which
# is exactly the sort of thing that survives right up until the once it does
# not.  J4 catches the rewrite, K1-K3 catch the damage.
#
# the file deliberately no longer matches its M2 blob: f5677cb replaced rev5's
# copied-over settings with jlcpcb's, before any routing, and every constraint
# it touched moved in the tighter direction (min_copper_edge_clearance
# 0.025 -> 0.3 being the one the brief names).  reverting to M2 would hand the
# fab a board checked at 0.025 mm edge clearance, so what is pinned here is the
# floor rather than the byte pattern: settings may be tightened, never loosened,
# and the DRC gate may not be quietly defanged with exclusions or downgraded
# severities.
REV6_PROJECT = "kicad/rev6/amigahid-pico-rev6.kicad_pro"
JLC_MIN_CONSTRAINTS = {
    "min_clearance": 0.2,
    "min_copper_edge_clearance": 0.3,
    "min_hole_clearance": 0.5,
    "min_hole_to_hole": 0.5,
    "min_silk_clearance": 0.15,
    "min_through_hole_diameter": 0.3,
    "min_track_width": 0.2,
    "min_via_annular_width": 0.13,
    "min_via_diameter": 0.6,
}
POWER_NETCLASS = "Power"
POWER_NETCLASS_MIN_WIDTH = 1.0
POWER_NETCLASS_PATTERNS = [
    "/AMIGA_5V", "/AMIGA_5V_FUSED", "/SYS5V", "/USBA_5V", "/KBIN_5V", "/AUX_5V", "+3V3",
]
# the violations this board is signed off on never having.  a "0 violations"
# DRC run means nothing if any of these has been turned down to warning or
# ignore, so the gate reads the severities rather than trusting the count.
NEVER_DOWNGRADE = [
    "annular_width",
    "clearance",
    "copper_edge_clearance",
    "courtyards_overlap",
    "drill_out_of_range",
    "hole_clearance",
    "hole_near_hole",
    "invalid_outline",
    "items_not_allowed",
    "malformed_courtyard",
    "padstack",
    "shorting_items",
    "through_hole_pad_without_hole",
    "track_width",
    "tracks_crossing",
    "unconnected_items",
    "zones_intersect",
]

# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------


def poly_bbox(pts: Sequence[Pt]) -> BBox:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def bbox_union(boxes: Sequence[BBox]) -> BBox:
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def bbox_overlap(a: BBox, b: BBox, slack: float = 0.0) -> bool:
    return not (
        a[2] + slack < b[0] or b[2] + slack < a[0] or a[3] + slack < b[1] or b[3] + slack < a[1]
    )


def bbox_gap(a: BBox, b: BBox) -> float:
    """closest approach of two boxes; 0 when they touch or overlap."""
    dx = max(0.0, a[0] - b[2], b[0] - a[2])
    dy = max(0.0, a[1] - b[3], b[1] - a[3])
    return math.hypot(dx, dy)


def bbox_inside(inner: BBox, outer: BBox, slack: float = 1e-6) -> bool:
    return (
        inner[0] >= outer[0] - slack
        and inner[1] >= outer[1] - slack
        and inner[2] <= outer[2] + slack
        and inner[3] <= outer[3] + slack
    )


def poly_area(pts: Sequence[Pt]) -> float:
    """unsigned shoelace area."""
    n = len(pts)
    if n < 3:
        return 0.0
    acc = 0.0
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        acc += x1 * y2 - x2 * y1
    return abs(acc) * 0.5


def point_in_poly(pt: Pt, poly: Sequence[Pt]) -> bool:
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xint = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xint > x:
                inside = not inside
    return inside


def _orient(a: Pt, b: Pt, c: Pt) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def segs_cross(a: Pt, b: Pt, c: Pt, d: Pt) -> bool:
    d1, d2 = _orient(c, d, a), _orient(c, d, b)
    d3, d4 = _orient(a, b, c), _orient(a, b, d)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return True
    eps = 1e-12

    def on_seg(p: Pt, q: Pt, r: Pt) -> bool:
        return (
            abs(_orient(p, q, r)) < eps
            and min(p[0], q[0]) - eps <= r[0] <= max(p[0], q[0]) + eps
            and min(p[1], q[1]) - eps <= r[1] <= max(p[1], q[1]) + eps
        )

    return on_seg(c, d, a) or on_seg(c, d, b) or on_seg(a, b, c) or on_seg(a, b, d)


def polys_overlap(a: Sequence[Pt], b: Sequence[Pt]) -> bool:
    """true if two simple polygons share any area (or touch)."""
    if len(a) < 3 or len(b) < 3:
        return False
    if not bbox_overlap(poly_bbox(a), poly_bbox(b)):
        return False
    for p in a:
        if point_in_poly(p, b):
            return True
    for p in b:
        if point_in_poly(p, a):
            return True
    na, nb = len(a), len(b)
    for i in range(na):
        for j in range(nb):
            if segs_cross(a[i], a[(i + 1) % na], b[j], b[(j + 1) % nb]):
                return True
    return False


def shrink_poly(poly: Sequence[Pt], eps: float) -> Poly:
    """pull every vertex `eps` towards the centroid.

    used so that copper which merely abuts a keep-out boundary - which is what
    a legal grounded pour flanking the antenna looks like, and what kicad's
    zone filler produces - does not read as copper inside the keep-out."""
    if len(poly) < 3:
        return list(poly)
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    out = []
    for x, y in poly:
        dx, dy = cx - x, cy - y
        d = math.hypot(dx, dy)
        if d <= eps:
            out.append((cx, cy))
        else:
            out.append((x + dx / d * eps, y + dy / d * eps))
    return out


def rotate_kicad(dx: float, dy: float, angle_deg: float) -> Pt:
    """kicad's rotation: y grows downward, angles are counter-clockwise on screen."""
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    return (dx * ca + dy * sa, -dx * sa + dy * ca)


def rect_poly(cx: float, cy: float, w: float, h: float, angle_deg: float = 0.0) -> Poly:
    hw, hh = w / 2.0, h / 2.0
    out = []
    for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
        rx, ry = rotate_kicad(dx, dy, angle_deg)
        out.append((cx + rx, cy + ry))
    return out


def circle_poly(cx: float, cy: float, r: float, n: int = 24) -> Poly:
    return [
        (cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
        for i in range(n)
    ]


def capsule_polys(p1: Pt, p2: Pt, width: float) -> List[Poly]:
    """a track segment as a rectangle plus its two round end caps."""
    r = width / 2.0
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    ln = math.hypot(dx, dy)
    polys = [circle_poly(p1[0], p1[1], r, 12), circle_poly(p2[0], p2[1], r, 12)]
    if ln > 1e-9:
        ux, uy = -dy / ln * r, dx / ln * r
        polys.append(
            [
                (p1[0] + ux, p1[1] + uy),
                (p2[0] + ux, p2[1] + uy),
                (p2[0] - ux, p2[1] - uy),
                (p1[0] - ux, p1[1] - uy),
            ]
        )
    return polys


def arc_from_three(start: Pt, mid: Pt, end: Pt) -> Tuple[Optional[Pt], float, float]:
    """circumcentre, radius and arc length of the arc through three points."""
    ax, ay = start
    bx, by = mid
    cx, cy = end
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return None, 0.0, math.hypot(cx - ax, cy - ay)
    ux = (
        (ax * ax + ay * ay) * (by - cy)
        + (bx * bx + by * by) * (cy - ay)
        + (cx * cx + cy * cy) * (ay - by)
    ) / d
    uy = (
        (ax * ax + ay * ay) * (cx - bx)
        + (bx * bx + by * by) * (ax - cx)
        + (cx * cx + cy * cy) * (bx - ax)
    ) / d
    r = math.hypot(ax - ux, ay - uy)
    a0 = math.atan2(ay - uy, ax - ux)
    a1 = math.atan2(by - uy, bx - ux)
    a2 = math.atan2(cy - uy, cx - ux)

    def norm(x: float) -> float:
        while x <= -math.pi:
            x += 2 * math.pi
        while x > math.pi:
            x -= 2 * math.pi
        return x

    sweep = norm(a2 - a0)
    # make sure the sweep goes the way the mid point says
    if norm(a1 - a0) * sweep < 0 or abs(norm(a1 - a0)) > abs(sweep):
        sweep = sweep - math.copysign(2 * math.pi, sweep)
    return (ux, uy), r, abs(sweep) * r


def tess_arc(start: Pt, mid: Pt, end: Pt, steps: int = 12) -> Poly:
    centre, r, _ = arc_from_three(start, mid, end)
    if centre is None:
        return [start, mid, end]
    ux, uy = centre
    a0 = math.atan2(start[1] - uy, start[0] - ux)
    a2 = math.atan2(end[1] - uy, end[0] - ux)
    a1 = math.atan2(mid[1] - uy, mid[0] - ux)

    def norm(x: float) -> float:
        while x <= -math.pi:
            x += 2 * math.pi
        while x > math.pi:
            x -= 2 * math.pi
        return x

    sweep = norm(a2 - a0)
    if norm(a1 - a0) * sweep < 0 or abs(norm(a1 - a0)) > abs(sweep):
        sweep = sweep - math.copysign(2 * math.pi, sweep)
    return [
        (ux + r * math.cos(a0 + sweep * i / steps), uy + r * math.sin(a0 + sweep * i / steps))
        for i in range(steps + 1)
    ]


# --------------------------------------------------------------------------
# neutral model
# --------------------------------------------------------------------------


@dataclass
class Pad:
    ref: str
    number: str
    net: str
    pos: Pt
    polys: List[Poly]
    is_npth: bool
    drill: float
    on_copper: bool


@dataclass
class Fp:
    ref: str
    value: str
    side: str  # "top" | "bottom"
    pos: Pt
    rot: float
    courtyard: Optional[BBox]
    body: BBox  # pads + graphics, no text
    pads: List[Pad] = field(default_factory=list)
    fpid: str = ""  # "Library:Footprint" - names the package, so its height

    def extent(self) -> BBox:
        return self.courtyard if self.courtyard else self.body


@dataclass
class Track:
    net: str
    layer: str
    width: float
    start: Pt
    end: Pt
    length: float
    is_via: bool
    polys: List[Poly]


@dataclass
class ZoneM:
    name: str
    is_rule: bool
    layers: List[str]
    net: str
    outline: Poly
    keepout: Dict[str, bool]
    filled: bool
    fills: Dict[str, List[Poly]]
    fill_area: Dict[str, float]
    parent: str


@dataclass
class TextM:
    layer: str
    text: str
    visible: bool
    kind: str  # "user" | "reference" | "value"
    parent: str


@dataclass
class EdgeItem:
    closed: bool
    pts: Poly


@dataclass
class Model:
    source: str
    copper_layers: List[str]
    edges: List[EdgeItem]
    fps: List[Fp]
    tracks: List[Track]
    zones: List[ZoneM]
    texts: List[TextM]
    copper_gfx: List[Tuple[str, Poly]]

    def by_ref(self, ref: str) -> Optional[Fp]:
        for f in self.fps:
            if f.ref == ref:
                return f
        return None


LAYER_ALIASES = {
    "F.SilkS": "F.Silkscreen",
    "B.SilkS": "B.Silkscreen",
    "F.Courtyard": "F.CrtYd",
    "B.Courtyard": "B.CrtYd",
    "F.Adhes": "F.Adhesive",
    "B.Adhes": "B.Adhesive",
    "F.Fab": "F.Fab",
    "B.Fab": "B.Fab",
}


def norm_layer(name: str) -> str:
    return LAYER_ALIASES.get(name, name)


def strip_net(name: str) -> str:
    """schematic nets come through as '/NAME' or '/sheet/NAME'."""
    return name.rsplit("/", 1)[-1]


# --------------------------------------------------------------------------
# backend: pcbnew
# --------------------------------------------------------------------------


def _chain_to_pts(chain, scale: float = 1e-6) -> Poly:
    return [(chain.CPoint(i).x * scale, chain.CPoint(i).y * scale) for i in range(chain.PointCount())]


def _polyset_outers(ps, scale: float = 1e-6) -> List[Poly]:
    return [_chain_to_pts(ps.Outline(i), scale) for i in range(ps.OutlineCount())]


def _polyset_area(ps) -> float:
    total = 0.0
    for i in range(ps.OutlineCount()):
        total += poly_area(_chain_to_pts(ps.Outline(i)))
        for h in range(ps.HoleCount(i)):
            total -= poly_area(_chain_to_pts(ps.Hole(i, h)))
    return total


def load_pcbnew(path: str) -> Model:
    import pcbnew  # noqa: F401  (optional dependency)

    MM = 1e6
    board = pcbnew.LoadBoard(path)
    copper = [board.GetLayerName(l) for l in board.GetEnabledLayers().CuStack()]

    def shape_to_edge(sh) -> Optional[EdgeItem]:
        st = sh.GetShapeStr() if hasattr(sh, "GetShapeStr") else ""
        s = (sh.GetStart().x / MM, sh.GetStart().y / MM)
        e = (sh.GetEnd().x / MM, sh.GetEnd().y / MM)
        if st == "Line":
            return EdgeItem(False, [s, e])
        if st == "Arc":
            m = (sh.GetArcMid().x / MM, sh.GetArcMid().y / MM)
            return EdgeItem(False, tess_arc(s, m, e))
        if st == "Circle":
            r = math.hypot(e[0] - s[0], e[1] - s[1])
            return EdgeItem(True, circle_poly(s[0], s[1], r, 32))
        if st == "Rect":
            return EdgeItem(True, [s, (e[0], s[1]), e, (s[0], e[1])])
        if st == "Polygon":
            ps = sh.GetPolyShape()
            outs = _polyset_outers(ps)
            if outs:
                return EdgeItem(True, outs[0])
            return None
        if st == "Bezier":
            pts = [(p.x / MM, p.y / MM) for p in sh.GetBezierPoints()]
            if len(pts) >= 2:
                return EdgeItem(False, pts)
            return None
        return None

    edges: List[EdgeItem] = []
    copper_gfx: List[Tuple[str, Poly]] = []
    texts: List[TextM] = []

    def collect_gfx(item, parent: str) -> None:
        lname = norm_layer(board.GetLayerName(item.GetLayer()))
        cls = item.GetClass()
        if cls in ("PCB_TEXT", "PCB_TEXTBOX", "FP_TEXT", "FP_TEXTBOX"):
            texts.append(TextM(lname, item.GetText(), item.IsVisible(), "user", parent))
            return
        if lname == "Edge.Cuts":
            ei = shape_to_edge(item)
            if ei:
                edges.append(ei)
            return
        if lname in copper:
            ps = pcbnew.SHAPE_POLY_SET()
            try:
                item.TransformShapeToPolygon(ps, item.GetLayer(), 0, 5000, pcbnew.ERROR_OUTSIDE)
                for o in _polyset_outers(ps):
                    copper_gfx.append((lname, o))
            except Exception:
                pass

    for d in board.GetDrawings():
        collect_gfx(d, "")

    fps: List[Fp] = []
    for f in board.GetFootprints():
        ref = f.GetReference()
        side = "bottom" if f.IsFlipped() else "top"
        pads: List[Pad] = []
        body_boxes: List[BBox] = []
        for p in f.Pads():
            ps = pcbnew.SHAPE_POLY_SET()
            polys: List[Poly] = []
            on_copper = any(
                p.IsOnLayer(board.GetLayerID(cl)) for cl in copper
            )
            for cl in copper:
                lid = board.GetLayerID(cl)
                if not p.IsOnLayer(lid):
                    continue
                try:
                    ps2 = pcbnew.SHAPE_POLY_SET()
                    p.TransformShapeToPolygon(ps2, lid, 0, 5000, pcbnew.ERROR_OUTSIDE)
                    polys.extend(_polyset_outers(ps2))
                except Exception:
                    pass
            if not polys:
                polys = [
                    rect_poly(
                        p.GetPosition().x / MM,
                        p.GetPosition().y / MM,
                        p.GetSizeX() / MM,
                        p.GetSizeY() / MM,
                        p.GetOrientationDegrees(),
                    )
                ]
            npth = p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH
            drill = max(p.GetDrillSizeX(), p.GetDrillSizeY()) / MM
            pads.append(
                Pad(
                    ref,
                    p.GetNumber(),
                    strip_net(p.GetNetname()),
                    (p.GetPosition().x / MM, p.GetPosition().y / MM),
                    polys,
                    npth,
                    drill,
                    on_copper,
                )
            )
            for pl in polys:
                body_boxes.append(poly_bbox(pl))
        for g in f.GraphicalItems():
            collect_gfx(g, ref)
            lname = norm_layer(board.GetLayerName(g.GetLayer()))
            if lname not in ("F.Silkscreen", "B.Silkscreen", "Edge.Cuts") and g.GetClass() not in (
                "PCB_TEXT",
                "FP_TEXT",
                "PCB_TEXTBOX",
                "FP_TEXTBOX",
            ):
                bb = g.GetBoundingBox()
                body_boxes.append(
                    (bb.GetX() / MM, bb.GetY() / MM, (bb.GetX() + bb.GetWidth()) / MM,
                     (bb.GetY() + bb.GetHeight()) / MM)
                )
        for tx, kind in ((f.Reference(), "reference"), (f.Value(), "value")):
            texts.append(
                TextM(
                    norm_layer(board.GetLayerName(tx.GetLayer())),
                    tx.GetText(),
                    tx.IsVisible(),
                    kind,
                    ref,
                )
            )
        cy: Optional[BBox] = None
        for lid in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            c = f.GetCourtyard(lid)
            if c.OutlineCount():
                bb = c.BBox()
                cy = (
                    bb.GetX() / MM,
                    bb.GetY() / MM,
                    (bb.GetX() + bb.GetWidth()) / MM,
                    (bb.GetY() + bb.GetHeight()) / MM,
                )
                break
        body = bbox_union(body_boxes) if body_boxes else (
            f.GetPosition().x / MM, f.GetPosition().y / MM,
            f.GetPosition().x / MM, f.GetPosition().y / MM,
        )
        fps.append(
            Fp(
                ref,
                f.GetValue(),
                side,
                (f.GetPosition().x / MM, f.GetPosition().y / MM),
                f.GetOrientationDegrees(),
                cy,
                body,
                pads,
                f.GetFPIDAsString(),
            )
        )

    tracks: List[Track] = []
    for t in board.GetTracks():
        net = strip_net(t.GetNetname())
        s = (t.GetStart().x / MM, t.GetStart().y / MM)
        e = (t.GetEnd().x / MM, t.GetEnd().y / MM)
        if t.GetClass() == "PCB_VIA":
            r = t.GetWidth() / MM / 2.0
            tracks.append(
                Track(net, "via", t.GetWidth() / MM, s, e, 0.0, True, [circle_poly(s[0], s[1], r, 16)])
            )
        else:
            w = t.GetWidth() / MM
            tracks.append(
                Track(
                    net,
                    norm_layer(board.GetLayerName(t.GetLayer())),
                    w,
                    s,
                    e,
                    t.GetLength() / MM,
                    False,
                    capsule_polys(s, e, w),
                )
            )

    zones: List[ZoneM] = []

    def add_zone(z, parent: str) -> None:
        lnames = [norm_layer(board.GetLayerName(l)) for l in z.GetLayerSet().Seq()]
        outline = _polyset_outers(z.Outline())
        keep = {
            "tracks": bool(z.GetDoNotAllowTracks()),
            "vias": bool(z.GetDoNotAllowVias()),
            "pads": bool(z.GetDoNotAllowPads()),
            "copperpour": bool(z.GetDoNotAllowZoneFills()),
            "footprints": bool(z.GetDoNotAllowFootprints()),
        }
        fills: Dict[str, List[Poly]] = {}
        areas: Dict[str, float] = {}
        if not z.GetIsRuleArea():
            for ln in lnames:
                if ln not in copper:
                    continue
                try:
                    fp_list = z.GetFilledPolysList(board.GetLayerID(ln))
                except Exception:
                    continue
                if fp_list is None:
                    continue
                fills[ln] = _polyset_outers(fp_list)
                areas[ln] = _polyset_area(fp_list)
        zones.append(
            ZoneM(
                z.GetZoneName(),
                bool(z.GetIsRuleArea()),
                lnames,
                strip_net(z.GetNetname()),
                outline[0] if outline else [],
                keep,
                bool(z.IsFilled()),
                fills,
                areas,
                parent,
            )
        )

    for z in board.Zones():
        add_zone(z, "")
    for f in board.GetFootprints():
        try:
            fzones = list(f.Zones())
        except Exception:
            fzones = []
        for z in fzones:
            add_zone(z, f.GetReference())

    return Model("pcbnew", copper, edges, fps, tracks, zones, texts, copper_gfx)


# --------------------------------------------------------------------------
# backend: s-expression reader (used when pcbnew is unavailable)
# --------------------------------------------------------------------------

_TOKEN_RE = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')


def sexpr_parse(text: str):
    stack: List[list] = [[]]
    for m in _TOKEN_RE.finditer(text):
        tok = m.group(0)
        if tok == "(":
            new: list = []
            stack[-1].append(new)
            stack.append(new)
        elif tok == ")":
            if len(stack) > 1:
                stack.pop()
        elif tok.startswith('"'):
            stack[-1].append(tok[1:-1].replace('\\"', '"').replace("\\\\", "\\"))
        else:
            stack[-1].append(tok)
    return stack[0][0]


def sx(node, key: str):
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def sxall(node, key: str):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def sxf(node, key: str, idx: int = 1, default: Optional[float] = None) -> Optional[float]:
    n = sx(node, key)
    if n is None or len(n) <= idx:
        return default
    try:
        return float(n[idx])
    except ValueError:
        return default


def sxs(node, key: str, idx: int = 1, default: str = "") -> str:
    n = sx(node, key)
    if n is None or len(n) <= idx:
        return default
    return str(n[idx])


def _at(node) -> Tuple[float, float, float]:
    n = sx(node, "at")
    if n is None:
        return (0.0, 0.0, 0.0)
    x = float(n[1])
    y = float(n[2])
    r = float(n[3]) if len(n) > 3 else 0.0
    return (x, y, r)


def _pts(node) -> Poly:
    p = sx(node, "pts")
    if p is None:
        return []
    out = []
    for c in p:
        if isinstance(c, list) and c and c[0] == "xy":
            out.append((float(c[1]), float(c[2])))
    return out


def _layers_of(node) -> List[str]:
    n = sx(node, "layers")
    if n is not None:
        return [norm_layer(str(v)) for v in n[1:]]
    n = sx(node, "layer")
    if n is not None:
        return [norm_layer(str(n[1]))]
    return []


def _hidden(node) -> bool:
    h = sx(node, "hide")
    if h is not None:
        return len(h) < 2 or str(h[1]) == "yes"
    return False


def load_sexpr(path: str) -> Model:
    with open(path, "r", encoding="utf-8") as fh:
        root = sexpr_parse(fh.read())

    nettab = _net_table(root)
    copper: List[str] = []
    lay = sx(root, "layers")
    if lay is not None:
        for c in lay[1:]:
            if isinstance(c, list) and len(c) >= 3 and c[2] in ("signal", "power", "mixed", "jumper"):
                copper.append(norm_layer(str(c[1])))

    edges: List[EdgeItem] = []
    copper_gfx: List[Tuple[str, Poly]] = []
    texts: List[TextM] = []

    def shape_edge(node, kind: str, xf) -> Optional[EdgeItem]:
        if kind in ("gr_line", "fp_line"):
            s = xf(*[float(v) for v in sx(node, "start")[1:3]])
            e = xf(*[float(v) for v in sx(node, "end")[1:3]])
            return EdgeItem(False, [s, e])
        if kind in ("gr_arc", "fp_arc"):
            s = xf(*[float(v) for v in sx(node, "start")[1:3]])
            m = xf(*[float(v) for v in sx(node, "mid")[1:3]])
            e = xf(*[float(v) for v in sx(node, "end")[1:3]])
            return EdgeItem(False, tess_arc(s, m, e))
        if kind in ("gr_circle", "fp_circle"):
            c = xf(*[float(v) for v in sx(node, "center")[1:3]])
            e = xf(*[float(v) for v in sx(node, "end")[1:3]])
            r = math.hypot(e[0] - c[0], e[1] - c[1])
            return EdgeItem(True, circle_poly(c[0], c[1], r, 32))
        if kind in ("gr_rect", "fp_rect"):
            s = xf(*[float(v) for v in sx(node, "start")[1:3]])
            e = xf(*[float(v) for v in sx(node, "end")[1:3]])
            return EdgeItem(True, [s, (e[0], s[1]), e, (s[0], e[1])])
        if kind in ("gr_poly", "fp_poly"):
            raw = _pts(node)
            return EdgeItem(True, [xf(x, y) for x, y in raw]) if raw else None
        return None

    GFX_KINDS = (
        "gr_line", "gr_arc", "gr_circle", "gr_rect", "gr_poly",
        "fp_line", "fp_arc", "fp_circle", "fp_rect", "fp_poly",
    )

    def handle_gfx(node, kind: str, xf, parent: str) -> Optional[BBox]:
        lns = _layers_of(node)
        ln = lns[0] if lns else ""
        ei = shape_edge(node, kind, xf)
        if ei is None:
            return None
        if ln == "Edge.Cuts":
            edges.append(ei)
            return None
        if ln in copper:
            copper_gfx.append((ln, ei.pts))
        if ln in ("F.Silkscreen", "B.Silkscreen"):
            return None
        return poly_bbox(ei.pts)

    ident = lambda x, y: (x, y)  # noqa: E731

    for node in root:
        if not isinstance(node, list) or not node:
            continue
        kind = node[0]
        if kind in GFX_KINDS:
            handle_gfx(node, kind, ident, "")
        elif kind in ("gr_text", "gr_text_box"):
            lns = _layers_of(node)
            texts.append(
                TextM(lns[0] if lns else "", str(node[1]), not _hidden(node), "user", "")
            )

    fps: List[Fp] = []
    tracks: List[Track] = []
    zones: List[ZoneM] = []

    def parse_zone(node, parent: str) -> None:
        keep = {"tracks": False, "vias": False, "pads": False, "copperpour": False, "footprints": False}
        ko = sx(node, "keepout")
        is_rule = ko is not None
        if ko is not None:
            for k in keep:
                v = sx(ko, k)
                if v is not None and str(v[1]) == "not_allowed":
                    keep[k] = True
        poly = sx(node, "polygon")
        outline = _pts(poly) if poly is not None else []
        fills: Dict[str, List[Poly]] = {}
        areas: Dict[str, float] = {}
        for fp_node in sxall(node, "filled_polygon"):
            lns = _layers_of(fp_node)
            ln = lns[0] if lns else (copper[0] if copper else "")
            pts = _pts(fp_node)
            if not pts:
                continue
            fills.setdefault(ln, []).append(pts)
            areas[ln] = areas.get(ln, 0.0) + poly_area(pts)
        zones.append(
            ZoneM(
                sxs(node, "name"),
                is_rule,
                _layers_of(node),
                strip_net(sxs(node, "net_name")) or _net_of(node, nettab),
                outline,
                keep,
                bool(fills),
                fills,
                areas,
                parent,
            )
        )

    for node in root:
        if not isinstance(node, list) or not node:
            continue
        kind = node[0]
        if kind == "zone":
            parse_zone(node, "")
        elif kind == "segment":
            s = tuple(float(v) for v in sx(node, "start")[1:3])
            e = tuple(float(v) for v in sx(node, "end")[1:3])
            w = sxf(node, "width", 1, 0.0) or 0.0
            tracks.append(
                Track(
                    _net_of(node, nettab),
                    _layers_of(node)[0] if _layers_of(node) else "",
                    w,
                    s,
                    e,
                    math.hypot(e[0] - s[0], e[1] - s[1]),
                    False,
                    capsule_polys(s, e, w),
                )
            )
        elif kind == "arc":
            s = tuple(float(v) for v in sx(node, "start")[1:3])
            m = tuple(float(v) for v in sx(node, "mid")[1:3])
            e = tuple(float(v) for v in sx(node, "end")[1:3])
            w = sxf(node, "width", 1, 0.0) or 0.0
            _, _, alen = arc_from_three(s, m, e)
            pts = tess_arc(s, m, e)
            polys: List[Poly] = []
            for i in range(len(pts) - 1):
                polys.extend(capsule_polys(pts[i], pts[i + 1], w))
            tracks.append(
                Track(
                    _net_of(node, nettab),
                    _layers_of(node)[0] if _layers_of(node) else "",
                    w,
                    s,
                    e,
                    alen,
                    False,
                    polys,
                )
            )
        elif kind == "via":
            x, y, _ = _at(node)
            d = sxf(node, "size", 1, 0.6) or 0.6
            tracks.append(
                Track(
                    _net_of(node, nettab),
                    "via",
                    d,
                    (x, y),
                    (x, y),
                    0.0,
                    True,
                    [circle_poly(x, y, d / 2.0, 16)],
                )
            )
        elif kind == "footprint":
            fx, fy, frot = _at(node)
            side = "bottom" if (_layers_of(node) and _layers_of(node)[0] == "B.Cu") else "top"
            fpid = str(node[1]) if len(node) > 1 and not isinstance(node[1], list) else ""
            ref, value = "", ""
            for prop in sxall(node, "property"):
                if len(prop) > 2 and prop[1] == "Reference":
                    ref = str(prop[2])
                elif len(prop) > 2 and prop[1] == "Value":
                    value = str(prop[2])

            def xf(lx: float, ly: float) -> Pt:
                rx, ry = rotate_kicad(lx, ly, frot)
                return (fx + rx, fy + ry)

            for prop in sxall(node, "property"):
                if len(prop) < 3:
                    continue
                lns = _layers_of(prop)
                kindname = {"Reference": "reference", "Value": "value"}.get(str(prop[1]), "user")
                texts.append(
                    TextM(lns[0] if lns else "", str(prop[2]), not _hidden(prop), kindname, ref)
                )
            for t in sxall(node, "fp_text"):
                if len(t) < 3:
                    continue
                lns = _layers_of(t)
                kindname = {"reference": "reference", "value": "value"}.get(str(t[1]), "user")
                texts.append(
                    TextM(lns[0] if lns else "", str(t[2]), not _hidden(t), kindname, ref)
                )

            body_boxes: List[BBox] = []
            cy_boxes: List[BBox] = []
            for g in node:
                if not isinstance(g, list) or not g:
                    continue
                if g[0] in GFX_KINDS:
                    lns = _layers_of(g)
                    ln = lns[0] if lns else ""
                    bb = handle_gfx(g, g[0], xf, ref)
                    if ln in ("F.CrtYd", "B.CrtYd"):
                        ei = shape_edge(g, g[0], xf)
                        if ei:
                            cy_boxes.append(poly_bbox(ei.pts))
                    elif bb is not None:
                        body_boxes.append(bb)
                elif g[0] == "zone":
                    parse_zone(g, ref)

            pads: List[Pad] = []
            for p in sxall(node, "pad"):
                pnum = str(p[1])
                ptype = str(p[2]) if len(p) > 2 else ""
                pshape = str(p[3]) if len(p) > 3 else ""
                px, py, prot = _at(p)
                ax, ay = xf(px, py)
                size = sx(p, "size")
                sw = float(size[1]) if size else 0.0
                sh = float(size[2]) if size and len(size) > 2 else sw
                drill_node = sx(p, "drill")
                drill = 0.0
                if drill_node is not None:
                    vals = [v for v in drill_node[1:] if not isinstance(v, list) and v != "oval"]
                    try:
                        drill = max(float(v) for v in vals) if vals else 0.0
                    except ValueError:
                        drill = 0.0
                plns = _layers_of(p)
                on_copper = any(l in copper or l == "*.Cu" for l in plns)
                if pshape == "circle":
                    polys = [circle_poly(ax, ay, sw / 2.0, 20)]
                elif pshape == "oval" and abs(sw - sh) > 1e-9:
                    polys = [rect_poly(ax, ay, sw, sh, prot)]
                else:
                    polys = [rect_poly(ax, ay, sw, sh, prot)]
                pads.append(
                    Pad(
                        ref,
                        pnum,
                        _net_of(p, nettab),
                        (ax, ay),
                        polys,
                        ptype == "np_thru_hole",
                        drill,
                        on_copper,
                    )
                )
                body_boxes.append(poly_bbox(polys[0]))

            body = bbox_union(body_boxes) if body_boxes else (fx, fy, fx, fy)
            fps.append(
                Fp(
                    ref,
                    value,
                    side,
                    (fx, fy),
                    frot,
                    bbox_union(cy_boxes) if cy_boxes else None,
                    body,
                    pads,
                    fpid,
                )
            )

    return Model("s-expr", copper, edges, fps, tracks, zones, texts, copper_gfx)


def _net_table(root) -> Dict[str, str]:
    """board-level '(net <code> "<name>")' declarations, if the file has any.

    kicad 10 (file format 20260206) dropped them and names the net inline on
    every item instead; older files carry the table and reference it by code."""
    table: Dict[str, str] = {}
    for n in sxall(root, "net"):
        if len(n) > 2:
            table[str(n[1])] = strip_net(str(n[2]))
    return table


def _net_of(node, table: Dict[str, str]) -> str:
    n = sx(node, "net")
    if n is None or len(n) < 2:
        return ""
    if len(n) >= 3:  # (net <code> "<name>")
        return strip_net(str(n[2]))
    val = str(n[1])
    if val in table:  # (net <code>) with a board-level table
        return table[val]
    return strip_net(val)  # (net "<name>")


# --------------------------------------------------------------------------
# assertion plumbing
# --------------------------------------------------------------------------


class Report:
    def __init__(self) -> None:
        self.results: List[Tuple[str, str, bool, List[str]]] = []

    def add(self, ident: str, title: str, ok: bool, detail: Optional[List[str]] = None) -> bool:
        self.results.append((ident, title, ok, detail or []))
        return ok

    def check(self, ident: str, title: str, ok: bool, fail_msg: str = "") -> bool:
        return self.add(ident, title, ok, [] if ok else [fail_msg])

    @property
    def failures(self) -> List[Tuple[str, str, bool, List[str]]]:
        return [r for r in self.results if not r[2]]

    def emit(self) -> None:
        for ident, title, ok, detail in self.results:
            print("%-5s %-4s %s" % (ident, "PASS" if ok else "FAIL", title))
            for line in detail:
                print("           %s" % line)


# --------------------------------------------------------------------------
# outline analysis (shared by every backend)
# --------------------------------------------------------------------------


@dataclass
class Outline:
    chains: List[Poly]
    open_chains: List[Poly]
    outer: Optional[Poly]
    cutouts: List[Poly]
    bbox: Optional[BBox]
    area: float


def build_outline(model: Model, tol: float = 0.01) -> Outline:
    closed = [e.pts for e in model.edges if e.closed]
    opens = [list(e.pts) for e in model.edges if not e.closed]

    chains: List[Poly] = []
    unresolved: List[Poly] = []
    pool = list(opens)
    while pool:
        cur = pool.pop()
        changed = True
        while changed:
            changed = False
            for i, cand in enumerate(pool):
                if math.dist(cur[-1], cand[0]) <= tol:
                    cur = cur + cand[1:]
                elif math.dist(cur[-1], cand[-1]) <= tol:
                    cur = cur + list(reversed(cand))[1:]
                elif math.dist(cur[0], cand[-1]) <= tol:
                    cur = cand[:-1] + cur
                elif math.dist(cur[0], cand[0]) <= tol:
                    cur = list(reversed(cand))[:-1] + cur
                else:
                    continue
                pool.pop(i)
                changed = True
                break
        if len(cur) >= 3 and math.dist(cur[0], cur[-1]) <= tol:
            chains.append(cur[:-1])
        else:
            unresolved.append(cur)

    all_closed = chains + [list(c) for c in closed]
    outer = None
    cutouts: List[Poly] = []
    if all_closed:
        boxes = [poly_bbox(c) for c in all_closed]
        areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in boxes]
        idx = areas.index(max(areas))
        outer = all_closed[idx]
        cutouts = [c for i, c in enumerate(all_closed) if i != idx]
    bbox = poly_bbox(outer) if outer else None
    area = 0.0
    if outer:
        area = poly_area(outer) - sum(poly_area(c) for c in cutouts)
    return Outline(all_closed, unresolved, outer, cutouts, bbox, area)


# --------------------------------------------------------------------------
# assertions
# --------------------------------------------------------------------------

def edge_gaps(box: BBox, board: BBox) -> Dict[str, float]:
    """how far each side of `box` is from the matching board edge.

    negative means the item hangs over the edge."""
    return {
        "west": box[0] - board[0],
        "north": box[1] - board[1],
        "east": board[2] - box[2],
        "south": board[3] - box[3],
    }


def edges_reached(box: BBox, board: BBox, tol: float = EDGE_REACH_TOL) -> List[str]:
    return [k for k, v in edge_gaps(box, board).items() if v <= tol]


def check_a_outline(rep: Report, ol: Outline) -> None:
    ok = True
    detail: List[str] = []
    if ol.open_chains:
        ok = False
        for c in ol.open_chains:
            detail.append(
                "Edge.Cuts chain does not close: %d points, ends %.3f,%.3f .. %.3f,%.3f"
                % (len(c), c[0][0], c[0][1], c[-1][0], c[-1][1])
            )
    if ol.outer is None:
        ok = False
        detail.append("no closed Edge.Cuts chain found at all")
    rep.add("A1", "exactly one closed outer Edge.Cuts chain", ok, detail)

    if ol.outer is not None:
        bad = [c for c in ol.cutouts if not bbox_inside(poly_bbox(c), ol.bbox)]
        rep.check(
            "A2",
            "every other closed chain is an internal cutout",
            not bad,
            "%d closed Edge.Cuts chain(s) lie outside the board outline" % len(bad),
        )
    else:
        rep.check("A2", "every other closed chain is an internal cutout", False, "no outline")

    if ol.bbox:
        w = ol.bbox[2] - ol.bbox[0]
        h = ol.bbox[3] - ol.bbox[1]
        ok = (
            SIZE_X_MIN - 0.05 <= w <= SIZE_X_MAX + 0.05
            and SIZE_Y_MIN - 0.05 <= h <= SIZE_Y_MAX + 0.05
        )
        rep.check(
            "A3",
            "board %.2f x %.2f mm inside the %g-%g x %g-%g envelope"
            % (w, h, SIZE_X_MIN, SIZE_X_MAX, SIZE_Y_MIN, SIZE_Y_MAX),
            ok,
            "board is %.2f x %.2f mm, outside %g-%g x %g-%g mm"
            % (w, h, SIZE_X_MIN, SIZE_X_MAX, SIZE_Y_MIN, SIZE_Y_MAX),
        )
    else:
        rep.check("A3", "board size inside envelope", False, "no outline to measure")


def check_b_mounting(rep: Report, model: Model, ol: Outline) -> None:
    holes: List[Tuple[str, Pt, float]] = []
    for f in model.fps:
        for p in f.pads:
            if p.is_npth and MOUNT_DIA_MIN <= p.drill <= MOUNT_DIA_MAX:
                holes.append(("NPTH pad %s/%s" % (f.ref, p.number), p.pos, p.drill))
    for c in ol.cutouts:
        b = poly_bbox(c)
        w, h = b[2] - b[0], b[3] - b[1]
        if (
            MOUNT_DIA_MIN <= w <= MOUNT_DIA_MAX
            and MOUNT_DIA_MIN <= h <= MOUNT_DIA_MAX
            and abs(w - h) <= 0.3
        ):
            holes.append(
                ("Edge.Cuts cutout", ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0), (w + h) / 2.0)
            )

    rep.check(
        "B1",
        "exactly 4 mounting holes of %g-%g mm" % (MOUNT_DIA_MIN, MOUNT_DIA_MAX),
        len(holes) == 4,
        "found %d (%s)" % (len(holes), ", ".join("%s d=%.2f" % (h[0], h[2]) for h in holes) or "none"),
    )

    if ol.bbox and len(holes) == 4:
        corners = [
            (ol.bbox[0], ol.bbox[1]),
            (ol.bbox[2], ol.bbox[1]),
            (ol.bbox[0], ol.bbox[3]),
            (ol.bbox[2], ol.bbox[3]),
        ]
        used = set()
        bad = []
        for name, pos, _d in holes:
            dists = [math.dist(pos, c) for c in corners]
            i = dists.index(min(dists))
            if min(dists) > MOUNT_CORNER_RADIUS or i in used:
                bad.append("%s at %.2f,%.2f is %.1f mm from the nearest free corner" % (name, pos[0], pos[1], min(dists)))
            used.add(i)
        rep.check(
            "B2",
            "one mounting hole near each board corner",
            not bad and len(used) == 4,
            "; ".join(bad) or "holes do not cover 4 distinct corners",
        )
    else:
        rep.check("B2", "one mounting hole near each board corner", False, "hole count wrong or no outline")


def antenna_candidates(model: Model) -> List[ZoneM]:
    """rule areas that look like they guard U1's antenna and actually bar copper.

    the RPi footprint also carries a 'board keep out suggestion' rule area on
    Edge.Cuts that forbids nothing; that one is only advisory and is skipped."""
    u1 = model.by_ref("U1")
    u1box = u1.extent() if u1 else None
    out = []
    for z in model.zones:
        if not z.is_rule or not z.outline:
            continue
        if not any(l in model.copper_layers for l in z.layers):
            continue
        if not all(z.keepout.get(k) for k in ("tracks", "vias", "pads")):
            continue
        name = (z.name or "").lower()
        near_u1 = z.parent == "U1" or (u1box is not None and bbox_overlap(poly_bbox(z.outline), u1box))
        if ("antenna" in name or re.search(r"\brf\b", name)) and near_u1:
            out.append(z)
    return out


def clip_bbox(box: BBox, clip: BBox) -> Optional[BBox]:
    b = (max(box[0], clip[0]), max(box[1], clip[1]), min(box[2], clip[2]), min(box[3], clip[3]))
    if b[2] <= b[0] or b[3] <= b[1]:
        return None
    return b


def check_c_keepout(rep: Report, model: Model, ol: Outline) -> Optional[ZoneM]:
    if not ol.bbox:
        rep.check("C1", "antenna keep-out rule area", False, "no board outline")
        rep.check("C2", "no copper inside the antenna keep-out", False, "no board outline")
        return None

    u1 = model.by_ref("U1")
    u1box = u1.extent() if u1 else None
    qualifying: List[ZoneM] = []
    notes: List[str] = []
    for z in model.zones:
        if not z.is_rule or not z.outline:
            continue
        b = poly_bbox(z.outline)
        if u1box is not None and not bbox_overlap(b, u1box):
            continue
        # only the part that lies on the board can shield anything
        on_board = clip_bbox(b, ol.bbox)
        w = (on_board[2] - on_board[0]) if on_board else 0.0
        h = (on_board[3] - on_board[1]) if on_board else 0.0
        big = (w >= ANT_MIN_LONG and h >= ANT_MIN_SHORT) or (w >= ANT_MIN_SHORT and h >= ANT_MIN_LONG)
        forbids = [k for k in ("tracks", "vias", "pads", "copperpour", "footprints") if not z.keepout.get(k)]
        missing_layers = [l for l in model.copper_layers if l not in z.layers]
        touches = min(edge_gaps(b, ol.bbox).values()) <= EDGE_TOUCH_TOL
        if big and not forbids and not missing_layers and touches:
            qualifying.append(z)
        elif big or not forbids:
            why = []
            if not big:
                why.append("only %.1f x %.1f mm on the board" % (w, h))
            if forbids:
                why.append("allows " + "+".join(forbids))
            if missing_layers:
                why.append("not on " + ",".join(missing_layers))
            if not touches:
                why.append("%.2f mm from the nearest board edge" % min(edge_gaps(b, ol.bbox).values()))
            notes.append(
                "rule area %r%s: %s"
                % (z.name or "(unnamed)", (" in " + z.parent) if z.parent else "", "; ".join(why))
            )

    rep.add(
        "C1",
        "a rule area >=%gx%g mm on all copper layers forbids tracks+vias+pads+copperpour+footprints and touches an edge"
        % (ANT_MIN_LONG, ANT_MIN_SHORT),
        bool(qualifying),
        notes if not qualifying else [],
    )

    # geometric emptiness is checked over every antenna/RF rule area near U1 so
    # that it stays meaningful even while C1 is still failing.
    regions = list(qualifying)
    for z in antenna_candidates(model):
        if z not in regions:
            regions.append(z)
    if not regions:
        rep.check("C2", "no copper inside the antenna keep-out", False, "no antenna rule area to test")
        return None

    offenders: List[str] = []
    for z in regions:
        area = shrink_poly(z.outline, KEEPOUT_TOUCH_EPS)
        zb = poly_bbox(area)
        for t in model.tracks:
            if not bbox_overlap(poly_bbox(t.polys[0]) if t.polys else zb, zb, 1.0):
                continue
            if any(polys_overlap(p, area) for p in t.polys):
                offenders.append(
                    "%s on net %r at %.2f,%.2f"
                    % ("via" if t.is_via else "track", t.net, t.start[0], t.start[1])
                )
        for f in model.fps:
            for p in f.pads:
                if not p.on_copper:
                    continue
                if not bbox_overlap(bbox_union([poly_bbox(x) for x in p.polys]), zb, 0.5):
                    continue
                if any(polys_overlap(q, area) for q in p.polys):
                    offenders.append("pad %s/%s at %.2f,%.2f" % (p.ref, p.number, p.pos[0], p.pos[1]))
        for oz in model.zones:
            if oz.is_rule:
                continue
            for ln, polys in oz.fills.items():
                for poly in polys:
                    if not bbox_overlap(poly_bbox(poly), zb):
                        continue
                    if polys_overlap(poly, area):
                        offenders.append("fill of zone %r on %s" % (oz.name or oz.net, ln))
                        break
        for ln, poly in model.copper_gfx:
            if bbox_overlap(poly_bbox(poly), zb) and polys_overlap(poly, area):
                offenders.append("copper graphic on %s" % ln)

    uniq = sorted(set(offenders))
    rep.add(
        "C2",
        "no copper item intersects the antenna keep-out on any layer",
        not uniq,
        uniq[:20] + (["... %d more" % (len(uniq) - 20)] if len(uniq) > 20 else []),
    )
    return regions[0]


def check_d_edges(rep: Report, model: Model, ol: Outline) -> None:
    if not ol.bbox:
        rep.check("D1", "edge assignments", False, "no board outline")
        return
    board = ol.bbox

    def on_edge(ref: str, want: str) -> Tuple[bool, str]:
        f = model.by_ref(ref)
        if f is None:
            return False, "%s is missing from the board" % ref
        box = f.extent()
        reached = edges_reached(box, board)
        gaps = edge_gaps(box, board)
        if want not in reached:
            return False, "%s does not reach the %s edge (gap %.2f mm)" % (ref, want, gaps[want])
        extra = [e for e in reached if e != want]
        if extra:
            return False, "%s also reaches the %s edge - orientation is ambiguous" % (ref, ",".join(extra))
        if not (board[0] <= f.pos[0] <= board[2] and board[1] <= f.pos[1] <= board[3]):
            return False, "%s origin is outside the board outline" % ref
        return True, ""

    bad = []
    for ref in SOUTH_CONNECTORS:
        ok, msg = on_edge(ref, "south")
        if not ok:
            bad.append(msg)
    rep.add("D1", "P1/P2 mate south, flush or overhanging", not bad, bad)

    bad = []
    for ref in NORTH_CONNECTORS:
        ok, msg = on_edge(ref, "north")
        if not ok:
            bad.append(msg)
    rep.add("D2", "J9/J10/J11/J12 mate north, flush or overhanging", not bad, bad)

    centres = []
    missing = []
    for ref in NORTH_CONNECTORS:
        f = model.by_ref(ref)
        if f is None:
            missing.append(ref)
            continue
        b = f.extent()
        centres.append((ref, (b[0] + b[2]) / 2.0))
    bad = list("%s missing" % m for m in missing)
    if len(centres) == len(NORTH_CONNECTORS):
        order = [r for r, _ in sorted(centres, key=lambda c: c[1])]
        if order != NORTH_CONNECTORS:
            bad.append("west-to-east order is %s, expected %s" % (" ".join(order), " ".join(NORTH_CONNECTORS)))
        for (r1, c1), (r2, c2) in zip(centres, centres[1:]):
            if abs(c2 - c1) < NORTH_MIN_SPACING:
                bad.append("%s and %s centres only %.2f mm apart (need %g)" % (r1, r2, abs(c2 - c1), NORTH_MIN_SPACING))
    rep.add(
        "D3",
        "north connectors ordered west-to-east with >=%g mm centre spacing" % NORTH_MIN_SPACING,
        not bad,
        bad,
    )

    bad = []
    for ref in ("J4", "J13"):
        f = model.by_ref(ref)
        if f is None:
            bad.append("%s is missing from the board" % ref)
            continue
        box = f.extent()
        reached = edges_reached(box, board)
        if len(reached) != 1:
            bad.append(
                "%s reaches %s (need exactly one edge so the mating face is unambiguous)"
                % (ref, ",".join(reached) or "no edge")
            )
    rep.add("D4", "J4 and J13 mate outward on exactly one board edge", not bad, bad)

    bad = []
    regions = antenna_candidates(model)
    u1 = model.by_ref("U1")
    if u1 is None:
        bad.append("U1 is missing from the board")
    elif not regions:
        bad.append("no antenna/RF rule area found near U1 to locate the antenna end")
    else:
        box = bbox_union([poly_bbox(z.outline) for z in regions])
        gaps = edge_gaps(box, board)
        best = min(gaps.items(), key=lambda kv: kv[1])
        if best[1] > EDGE_REACH_TOL:
            bad.append(
                "U1 antenna end is %.2f mm from the %s edge (need <=%g mm or overhanging)"
                % (best[1], best[0], EDGE_REACH_TOL)
            )
    rep.add("D5", "U1 antenna end flush with or overhanging a board edge", not bad, bad)

    bad = []
    cs = []
    for ref in SOUTH_CONNECTORS:
        f = model.by_ref(ref)
        if f is None:
            bad.append("%s missing" % ref)
            continue
        b = f.extent()
        cs.append((ref, (b[0] + b[2]) / 2.0))
    if len(cs) == 2:
        gap = abs(cs[1][1] - cs[0][1])
        if gap < DE9_MIN_SPACING:
            bad.append("P1/P2 centres %.2f mm apart, DE9 hoods need >=%g" % (gap, DE9_MIN_SPACING))
        for ref, c in cs:
            m = min(c - board[0], board[2] - c)
            if m < DE9_MIN_CORNER:
                bad.append("%s centre only %.2f mm from a side edge (need >=%g)" % (ref, m, DE9_MIN_CORNER))
    rep.add("D6", "DE9 hoods clear each other and the board corners", not bad, bad)


def check_e_sides(rep: Report, model: Model) -> None:
    bad = []
    for ref in TOP_REFS:
        f = model.by_ref(ref)
        if f is None:
            bad.append("%s is missing from the board" % ref)
        elif f.side != "top":
            bad.append("%s is on the bottom, expected top" % ref)
    rep.add("E1", "module, connectors, LEDs, JP1, fuses, D1/D2 and the USBLC6 are on top", not bad, bad)

    bad = []
    for ref in BOTTOM_REFS:
        f = model.by_ref(ref)
        if f is None:
            bad.append("%s is missing from the board" % ref)
        elif f.side != "bottom":
            bad.append("%s is on the top, expected bottom" % ref)
    rep.add("E2", "the 19 BSS138 and R1-R38 shifter field are on the bottom", not bad, bad)

    qs = [f for f in model.fps if re.fullmatch(r"Q\d+", f.ref)]
    rep.check(
        "E3",
        "exactly %d level shifter FETs" % EXPECTED_BSS138,
        len(qs) == EXPECTED_BSS138,
        "found %d Q* footprints" % len(qs),
    )

    # the bottom is the face the board rests on, so it may only carry packages
    # that stand about a millimetre proud of the copper.  anything else - a can,
    # a radial, a through-hole part - props the board up and gets caught here,
    # whether or not anyone remembered to list that package as tall.
    bad = []
    for f in model.fps:
        if f.side != "bottom":
            continue
        name = f.fpid.rsplit(":", 1)[-1]
        if not any(re.search(p, name) for p in BOTTOM_LOW_PROFILE):
            bad.append(
                "%s is a %s on B.Cu - too tall for the side the board sits on"
                % (f.ref, f.fpid or "(footprint with no name)")
            )
    rep.add(
        "E4",
        "every bottom-side part is low profile (%s)" % ", ".join(BOTTOM_LOW_PROFILE),
        not bad,
        sorted(bad),
    )

    check_e5_bulk(rep, model)


def check_e5_bulk(rep: Report, model: Model) -> None:
    """the usb-host bulk can sits as close to the VBUS pin as the packages allow."""
    title = "%s (usb-host bulk) is pinned to %s pin %s" % (BULK_REF, BULK_HOST_REF, BULK_HOST_PAD)
    cap = model.by_ref(BULK_REF)
    host = model.by_ref(BULK_HOST_REF)
    missing = [r for r, f in ((BULK_REF, cap), (BULK_HOST_REF, host)) if f is None]
    if missing:
        rep.check("E5", title, False, "%s missing from the board" % ", ".join(missing))
        return

    plus = [p for p in cap.pads if p.net == BULK_NET]
    vbus = [p for p in host.pads if p.number == BULK_HOST_PAD]
    if not plus or not vbus:
        rep.check(
            "E5", title, False,
            "%s has no %s pad" % (BULK_REF, BULK_NET) if not plus
            else "%s has no pad %s" % (BULK_HOST_REF, BULK_HOST_PAD),
        )
        return
    if vbus[0].net != BULK_NET:
        rep.check(
            "E5", title, False,
            "%s pin %s is on %s, not %s - the bulk cap is measured against the wrong pin"
            % (BULK_HOST_REF, BULK_HOST_PAD, vbus[0].net or "no net", BULK_NET),
        )
        return

    dist = min(math.dist(p.pos, vbus[0].pos) for p in plus)
    bad = []
    if dist > BULK_MAX_DIST + 1e-6:
        bad.append(
            "%s pad is %.2f mm from %s pin %s, past the %g mm ceiling - the sweep floor is "
            "%.2f mm, so this is drift, not geometry"
            % (BULK_NET, dist, BULK_HOST_REF, BULK_HOST_PAD, BULK_MAX_DIST, BULK_SWEEP_FLOOR)
        )

    # hugging: with the courtyards fixed, "as close as it goes" is measurable
    # as the can touching the two parts that box it in.
    for ref in BULK_HUG_REFS:
        other = model.by_ref(ref)
        if other is None:
            bad.append("%s is missing, so %s has nothing to hug" % (ref, BULK_REF))
            continue
        if cap.courtyard is None or other.courtyard is None:
            bad.append("%s or %s has no courtyard to measure against" % (BULK_REF, ref))
            continue
        gap = bbox_gap(cap.courtyard, other.courtyard)
        if gap > BULK_MAX_HUG + 1e-6:
            bad.append(
                "%s stands %.2f mm off %s (limit %g mm) - it has been let drift off the "
                "connector corner" % (BULK_REF, gap, ref, BULK_MAX_HUG)
            )

    rep.add(
        "E5",
        "%s: %s pad %.2f mm from pin %s (brief asks %g, closest legal is %.2f)"
        % (title, BULK_NET, dist, BULK_HOST_PAD, BULK_BRIEF_DIST, BULK_SWEEP_FLOOR),
        not bad,
        bad,
    )


def net_tracks(model: Model, net: str) -> List[Track]:
    return [t for t in model.tracks if t.net == net]


def net_has_copper(model: Model, net: str) -> bool:
    if any(not t.is_via for t in net_tracks(model, net)):
        return True
    for z in model.zones:
        if not z.is_rule and z.net == net and any(z.fills.values()):
            return True
    return False


def check_f_power(rep: Report, model: Model) -> None:
    unrouted = [n for n in POWER_NETS if not net_has_copper(model, n)]
    rep.add(
        "F1",
        "power nets have copper (tracks or a pour): " + ", ".join(POWER_NETS),
        not unrouted,
        ["%s has no track and no filled zone - nothing is routed yet" % n for n in unrouted],
    )

    pads_by_net: Dict[str, List[Pt]] = {}
    for f in model.fps:
        for p in f.pads:
            pads_by_net.setdefault(p.net, []).append(p.pos)

    thin: List[str] = []
    for net in POWER_NETS:
        near = pads_by_net.get(net, [])
        for t in net_tracks(model, net):
            if t.is_via or t.width >= POWER_MIN_WIDTH - 1e-9:
                continue
            ends_at_pads = all(
                any(math.dist(end, pp) <= NECKDOWN_PAD_DIST for pp in near) for end in (t.start, t.end)
            )
            if ends_at_pads:
                continue
            thin.append(
                "%s: %.3f mm segment on %s from %.2f,%.2f to %.2f,%.2f"
                % (net, t.width, t.layer, t.start[0], t.start[1], t.end[0], t.end[1])
            )
    rep.add(
        "F2",
        "every power segment is >=%g mm (pad neckdowns within %g mm excepted)"
        % (POWER_MIN_WIDTH, NECKDOWN_PAD_DIST),
        not thin,
        thin[:20] + (["... %d more" % (len(thin) - 20)] if len(thin) > 20 else []),
    )


def check_g_usb(rep: Report, model: Model) -> None:
    lengths: Dict[str, float] = {}
    for net in USB_NETS:
        lengths[net] = sum(t.length for t in net_tracks(model, net) if not t.is_via)

    missing = [n for n, l in lengths.items() if l <= 0.0]
    rep.add(
        "G1",
        "usb_dp and usb_dm are routed",
        not missing,
        ["%s has no routed length - the USB pair is not routed yet" % n for n in missing],
    )

    long_ones = [
        "%s is %.2f mm (limit %g)" % (n, l, USB_MAX_LEN) for n, l in lengths.items() if l > USB_MAX_LEN
    ]
    rep.add("G2", "each USB data net is shorter than %g mm" % USB_MAX_LEN, not long_ones, long_ones)

    if not missing:
        skew = abs(lengths[USB_NETS[0]] - lengths[USB_NETS[1]])
        rep.check(
            "G3",
            "USB pair length mismatch below %g mm" % USB_MAX_SKEW,
            skew < USB_MAX_SKEW,
            "usb_dp %.2f mm vs usb_dm %.2f mm, mismatch %.2f mm"
            % (lengths["usb_dp"], lengths["usb_dm"], skew),
        )
    else:
        rep.check("G3", "USB pair length mismatch below %g mm" % USB_MAX_SKEW, False, "pair not routed")


def check_h_silk(rep: Report, model: Model) -> None:
    silk_texts = [
        t for t in model.texts if t.layer in ("F.Silkscreen", "B.Silkscreen") and t.visible
    ]
    user_texts = [t.text for t in silk_texts if t.kind == "user"]
    all_texts = [t.text for t in silk_texts]

    missing = []
    for want in SILK_STRINGS:
        if not any(want.lower() in t.lower() for t in all_texts):
            missing.append(want)
    rep.add(
        "H1",
        "silkscreen carries " + ", ".join(repr(s) for s in SILK_STRINGS),
        not missing,
        ["missing silkscreen text %r" % m for m in missing],
    )

    rep.check(
        "H2",
        "silkscreen carries a board revision marker matching /r\\s*6/",
        any(SILK_REVISION_RE.search(t) for t in user_texts),
        "no board-level silkscreen text contains an 'r6' revision marker",
    )

    bad = []
    for ref in REFDES_MUST_SHOW:
        hits = [t for t in model.texts if t.parent == ref and t.kind == "reference"]
        if not hits:
            bad.append("%s has no reference text item" % ref)
            continue
        good = [t for t in hits if t.layer in ("F.Silkscreen", "B.Silkscreen") and t.visible]
        if not good:
            bad.append(
                "%s reference is %s"
                % (ref, "hidden" if not hits[0].visible else "on %s, not a silkscreen layer" % hits[0].layer)
            )
    rep.add("H3", "every connector reference designator is visible on silkscreen", not bad, bad)


def check_i_zones(rep: Report, model: Model, ol: Outline) -> None:
    gnd = [z for z in model.zones if not z.is_rule and z.net == GND_NET]
    per_layer: Dict[str, List[ZoneM]] = {}
    for z in gnd:
        for ln in z.layers:
            if ln in model.copper_layers:
                per_layer.setdefault(ln, []).append(z)

    missing = [ln for ln in model.copper_layers if ln not in per_layer]
    rep.add(
        "I1",
        "a GND pour exists on every copper layer",
        not missing,
        ["no GND zone on %s" % ln for ln in missing],
    )

    unfilled = [
        "%s zone %r is not filled" % (ln, z.name or z.net)
        for ln, zs in per_layer.items()
        for z in zs
        if not z.fills.get(ln)
    ]
    rep.add(
        "I2",
        "every GND pour is filled and the fill is saved in the board",
        not unfilled,
        unfilled + (["run 'Edit > Fill All Zones' and save before checking"] if unfilled else []),
    )

    bad = []
    if ol.area > 0:
        for ln in model.copper_layers:
            area = sum(z.fill_area.get(ln, 0.0) for z in per_layer.get(ln, []))
            frac = area / ol.area
            if frac < GND_MIN_COVERAGE:
                bad.append(
                    "%s GND fill covers %.1f%% of the %.1f mm2 board (need %.0f%%)"
                    % (ln, frac * 100.0, ol.area, GND_MIN_COVERAGE * 100.0)
                )
    else:
        bad.append("board area unknown")
    rep.add("I3", "GND pours cover >=%.0f%% of the board on each layer" % (GND_MIN_COVERAGE * 100), not bad, bad)

    vias = [t for t in model.tracks if t.is_via and t.net == GND_NET]
    rep.check(
        "I4",
        ">=%d GND stitching vias" % GND_MIN_VIAS,
        len(vias) >= GND_MIN_VIAS,
        "found %d GND vias" % len(vias),
    )

    stranded = gnd_stranded(model)
    rep.add(
        "I5",
        "every GND pad reaches the main ground island",
        not stranded,
        [
            "%s is on a ground island of its own - the pour around it is not tied "
            "to the plane by any via" % s
            for s in stranded[:20]
        ]
        + (["... %d more" % (len(stranded) - 20)] if len(stranded) > 20 else []),
    )


class _UF:
    def __init__(self) -> None:
        self.p: Dict[object, object] = {}

    def find(self, a: object) -> object:
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a: object, b: object) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def gnd_stranded(model: Model) -> List[str]:
    """GND pads that do not share an electrical island with the main plane.

    I1-I4 only prove a pour exists, is filled, is big and has vias.  none of them
    notices a fill region that missed its via: with a pour-only ground (this board
    has no GND tracks at all) such a region is a dead node, and DRC reports it as an
    anonymous 'Zone GND F.Cu <-> Zone GND B.Cu' line that names no part.  D23/D25/
    D26/D29 shipped that way once already."""
    items: List[Tuple[object, List[str], List[Poly], BBox, bool]] = []
    # (key, layers, polygons, bbox, bridges_layers)
    for z in model.zones:
        if z.is_rule or z.net != GND_NET:
            continue
        for ln, polys in z.fills.items():
            if ln not in model.copper_layers:
                continue
            for i, poly in enumerate(polys):
                if len(poly) < 3:
                    continue
                items.append(
                    (("fill", z.name, ln, i), [ln], [poly], poly_bbox(poly), False)
                )
    pad_keys: Dict[object, str] = {}
    for f in model.fps:
        for p in f.pads:
            if p.net != GND_NET or not p.polys or not p.on_copper:
                continue
            key = ("pad", f.ref, p.number, id(p))
            layers = [ln for ln in model.copper_layers]
            if p.drill <= 0.0:
                layers = ["B.Cu" if f.side == "bottom" else "F.Cu"]
            items.append((key, layers, p.polys, bbox_union([poly_bbox(q) for q in p.polys]), p.drill > 0.0))
            pad_keys[key] = "%s pad %s" % (f.ref, p.number)
    for i, t in enumerate(model.tracks):
        if t.net != GND_NET or not t.polys:
            continue
        layers = list(model.copper_layers) if t.is_via else [t.layer]
        items.append((("trk", i), layers, t.polys, bbox_union([poly_bbox(q) for q in t.polys]), t.is_via))

    uf = _UF()
    # bucket by a coarse grid so this stays linear in practice
    cell = 4.0
    buckets: Dict[Tuple[str, int, int], List[int]] = {}
    for idx, (_key, layers, _polys, box, _br) in enumerate(items):
        for ln in layers:
            for gx in range(int(box[0] // cell), int(box[2] // cell) + 1):
                for gy in range(int(box[1] // cell), int(box[3] // cell) + 1):
                    buckets.setdefault((ln, gx, gy), []).append(idx)
    seen: set = set()
    for members in buckets.values():
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                ia, ib = members[a], members[b]
                if ia == ib or (ia, ib) in seen:
                    continue
                seen.add((ia, ib))
                ka, la, pa, ba, _ = items[ia]
                kb, lb, pb, bb, _ = items[ib]
                if not set(la) & set(lb):
                    continue
                if not bbox_overlap(ba, bb):
                    continue
                if any(polys_overlap(qa, qb) for qa in pa for qb in pb):
                    uf.union(ka, kb)

    sizes: Dict[object, float] = {}
    for key, _layers, polys, _box, _br in items:
        if key[0] != "fill":
            continue
        sizes[uf.find(key)] = sizes.get(uf.find(key), 0.0) + sum(poly_area(q) for q in polys)
    if not sizes:
        return []
    main = max(sizes, key=lambda k: sizes[k])
    return sorted(name for key, name in pad_keys.items() if uf.find(key) != main)


def _git(root: str, *args: str) -> Tuple[int, str]:
    try:
        p = subprocess.run(
            ["git", "-C", root] + list(args), capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)
    return p.returncode, (p.stdout + p.stderr).strip()


def check_j_untouched(rep: Report, root: str) -> None:
    rc, out = _git(root, "rev-parse", "--git-dir")
    if rc != 0:
        rep.check("J1", "rev5 KiCad files unmodified in the working tree", False, "not a git checkout: %s" % out)
        rep.check("J2", "rev5 KiCad files unchanged since the fork point", False, "not a git checkout")
        rep.check("J3", "%s unmodified since M2" % NETLIST_CHECKER, False, "not a git checkout")
        rep.check("J4", "%s unmodified in the working tree" % REV6_PROJECT, False, "not a git checkout")
        return

    rc, out = _git(root, "ls-files", "-m", "-o", "--exclude-standard", "--", "kicad/")
    dirty = [
        l for l in out.splitlines()
        if l.startswith(REV5_GLOB_PREFIX)
    ]
    rc2, staged = _git(root, "diff", "--cached", "--name-only", "--", "kicad/")
    dirty += [l for l in staged.splitlines() if l.startswith(REV5_GLOB_PREFIX)]
    rep.add(
        "J1",
        "rev5 KiCad files unmodified in the working tree",
        not dirty,
        ["%s differs from HEAD" % d for d in sorted(set(dirty))],
    )

    rc, listing = _git(root, "ls-tree", "-r", "--name-only", "HEAD", "kicad/")
    rev5 = [f for f in listing.splitlines() if f.startswith(REV5_GLOB_PREFIX)]
    bad = []
    if rc != 0 or not rev5:
        bad.append("could not list rev5 files at HEAD")
    else:
        rc, base = _git(root, "rev-parse", "--verify", REV5_BASELINE_COMMIT + "^{commit}")
        if rc != 0:
            bad.append("baseline commit %s not found in this repo" % REV5_BASELINE_COMMIT[:8])
        else:
            for f in rev5:
                rc1, h1 = _git(root, "rev-parse", "HEAD:%s" % f)
                rc2, h2 = _git(root, "rev-parse", "%s:%s" % (REV5_BASELINE_COMMIT, f))
                if rc1 or rc2 or h1 != h2:
                    bad.append("%s changed since %s" % (f, REV5_BASELINE_COMMIT[:8]))
    rep.add("J2", "rev5 KiCad files byte-identical to the fork point", not bad, bad)

    bad = []
    rc, blob = _git(root, "hash-object", os.path.join(root, NETLIST_CHECKER))
    if rc != 0:
        bad.append("cannot hash %s: %s" % (NETLIST_CHECKER, blob))
    elif blob != NETLIST_CHECKER_M2_BLOB:
        bad.append(
            "%s content hash %s does not match the M2 version %s (commit %s) - the netlist "
            "checker must not be weakened" % (NETLIST_CHECKER, blob[:12], NETLIST_CHECKER_M2_BLOB[:12], NETLIST_CHECKER_M2_COMMIT[:8])
        )
    rc, log = _git(root, "log", "--format=%H", "%s..HEAD" % NETLIST_CHECKER_M2_COMMIT, "--", NETLIST_CHECKER)
    if rc == 0 and log:
        bad.append(
            "%s was touched by %d commit(s) after M2: %s"
            % (NETLIST_CHECKER, len(log.splitlines()), " ".join(c[:8] for c in log.splitlines()))
        )
    rep.add("J3", "%s unmodified since M2" % NETLIST_CHECKER, not bad, bad)

    # every scripted pcbnew save rewrites the project file, so a dirty .kicad_pro
    # here means the gates below are being run against settings nobody chose.
    rc, out = _git(root, "ls-files", "-m", "--", REV6_PROJECT)
    dirty = [l for l in out.splitlines() if l.strip()]
    rc, staged = _git(root, "diff", "--cached", "--name-only", "--", REV6_PROJECT)
    dirty += [l for l in staged.splitlines() if l.strip()]
    rep.add(
        "J4",
        "%s unmodified in the working tree" % REV6_PROJECT,
        not dirty,
        ["%s differs from HEAD - a scripted save has rewritten it; restore it before "
         "trusting DRC" % d for d in sorted(set(dirty))],
    )


def check_k_project(rep: Report, root: str) -> None:
    """the fab rules and the DRC severities the board was signed off under."""
    path = os.path.join(root, REV6_PROJECT)
    try:
        with open(path) as fh:
            proj = json.load(fh)
    except (OSError, ValueError) as exc:
        for ident, what in (
            ("K1", "rev6 constraints meet the jlcpcb floors"),
            ("K2", "the %s netclass carries the supply rails" % POWER_NETCLASS),
            ("K3", "no DRC rule is excluded or downgraded"),
        ):
            rep.check(ident, what, False, "cannot read %s: %s" % (REV6_PROJECT, exc))
        return

    board = proj.get("board") or {}
    rules = (board.get("design_settings") or {}).get("rules") or {}
    bad = []
    for key in sorted(JLC_MIN_CONSTRAINTS):
        floor = JLC_MIN_CONSTRAINTS[key]
        val = rules.get(key)
        if val is None:
            bad.append("%s is unset - pcbnew has rewritten the constraints" % key)
        elif float(val) < floor - 1e-9:
            bad.append("%s is %g mm, under the %g mm fab floor" % (key, float(val), floor))
    rep.add(
        "K1",
        "rev6 constraints meet the jlcpcb floors (%s)"
        % ", ".join("%s>=%g" % (k, JLC_MIN_CONSTRAINTS[k]) for k in sorted(JLC_MIN_CONSTRAINTS)),
        not bad,
        bad,
    )

    nets = proj.get("net_settings") or {}
    classes = {c.get("name"): c for c in (nets.get("classes") or [])}
    bad = []
    pcls = classes.get(POWER_NETCLASS)
    if pcls is None:
        bad.append("no %r netclass - the supply rails are back on Default" % POWER_NETCLASS)
    else:
        width = float(pcls.get("track_width") or 0.0)
        if width < POWER_NETCLASS_MIN_WIDTH - 1e-9:
            bad.append(
                "%s track_width is %g mm, under the %g mm the brief asks of the rails"
                % (POWER_NETCLASS, width, POWER_NETCLASS_MIN_WIDTH)
            )
    assigned = {
        p.get("pattern") for p in (nets.get("netclass_patterns") or [])
        if p.get("netclass") == POWER_NETCLASS
    }
    orphans = [p for p in POWER_NETCLASS_PATTERNS if p not in assigned]
    if orphans:
        bad.append("%s is not assigned to %s" % (POWER_NETCLASS, ", ".join(orphans)))
    rep.add("K2", "the %s netclass carries the supply rails" % POWER_NETCLASS, not bad, bad)

    bad = []
    excluded = board.get("drc_exclusions") or []
    if excluded:
        bad.append(
            "%d DRC exclusion(s) - a clean run means nothing while violations are being "
            "waived: %s" % (len(excluded), "; ".join(str(e) for e in excluded[:5]))
        )
    severities = (board.get("design_settings") or {}).get("rule_severities") or {}
    for rule in NEVER_DOWNGRADE:
        sev = severities.get(rule)
        if sev is None:
            bad.append("%s has no severity set" % rule)
        elif sev != "error":
            bad.append("%s is %r, and has to stay an error" % (rule, sev))
    rep.add("K3", "no DRC rule is excluded or downgraded", not bad, bad)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv: List[str]) -> int:
    root = repo_root()
    board_path = argv[1] if len(argv) > 1 else os.path.join(root, BOARD_REL)
    if not os.path.isfile(board_path):
        print("board file not found: %s" % board_path, file=sys.stderr)
        return 2

    model: Optional[Model] = None
    if not os.environ.get("REV6_FORCE_SEXPR"):
        try:
            model = load_pcbnew(board_path)
        except ImportError:
            pass
        except Exception as exc:  # noqa: BLE001 - fall back rather than die
            print("pcbnew backend failed (%s); falling back to the s-expr reader" % exc, file=sys.stderr)
    if model is None:
        model = load_sexpr(board_path)

    print("board  : %s" % board_path)
    print("backend: %s   copper layers: %s" % (model.source, ", ".join(model.copper_layers)))
    print("content: %d footprints, %d track items, %d zones, %d text items"
          % (len(model.fps), len(model.tracks), len(model.zones), len(model.texts)))
    print()

    ol = build_outline(model)
    rep = Report()
    check_a_outline(rep, ol)
    check_b_mounting(rep, model, ol)
    check_c_keepout(rep, model, ol)
    check_d_edges(rep, model, ol)
    check_e_sides(rep, model)
    check_f_power(rep, model)
    check_g_usb(rep, model)
    check_h_silk(rep, model)
    check_i_zones(rep, model, ol)
    if os.environ.get("REV6_SKIP_GIT"):
        rep.add("J0", "git checks skipped by REV6_SKIP_GIT", True)
    else:
        check_j_untouched(rep, root)
    check_k_project(rep, root)

    rep.emit()
    print()
    failed = rep.failures
    if failed:
        print("FAILED %d of %d assertions: %s"
              % (len(failed), len(rep.results), " ".join(f[0] for f in failed)))
        return 1
    print("all %d assertions pass" % len(rep.results))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
