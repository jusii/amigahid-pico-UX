#!/usr/bin/env python3
"""routing style checks for the rev6 board layout.

DRC proves a layout is *manufacturable*.  it says nothing about whether the
copper looks like a human drew it.  the rev6 tracks were first laid by a grid
maze router, which produced electrically-correct routing at whatever angle got
it around the next obstacle - lots of near-45 diagonals that are not 45, and
long ladders of half-millimetre jogs.  that reads as sloppy and it is not
something DRC, the netlist checker or check_rev6_pcb.py will ever complain
about.  this file turns "professional routing" into numbers:

    S1  >=99.0% of routed track length sits on a multiple of 45 deg
    S2  no staircases - runs of short segments zig-zagging their way along
    S3  no debris segments and no duplicate/overlapping copper on a net
    S4  per-net segment counts (informational, never fails)

a note on how the geometry is normalised before it is measured, because the
naive versions of S1 and S2 are both trivially gameable.

  * consecutive collinear segments are merged first.  a router can turn one
    ugly 10 mm diagonal into 21 pieces of 0.48 mm, and every piece would then
    duck under the short-segment exemption S1 grants to pad exits.  merging
    puts the run back together, so the exemption can only ever excuse copper
    that really is short.  merging only ever joins segments that are already
    collinear, share an endpoint where nothing else connects, carry no via at
    the joint and have the same width - it never changes the shape of the
    copper, only how many objects describe it.
  * S1 and S2 therefore run on merged geometry; S3 (debris, duplicates) and
    the raw half of S4 run on the untouched segment list, because a 0.02 mm
    sliver is debris whether or not something collinear sits next to it.

usage (/nas is mounted noexec, so always via the interpreter):

    python3 tools/check_rev6_style.py [board.kicad_pcb]

the board is opened read-only; nothing here ever writes the .kicad_pcb.

exit code 0 only when S1, S2 and S3 all pass.  S4 is a report.
"""

from __future__ import annotations

import collections
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------

BOARD_REL = "kicad/rev6/amigahid-pico-rev6.kicad_pcb"

NM = 1000000.0  # nanometres per millimetre (kicad's internal unit is the nm)

# S1: angle discipline
ANGLE_STEP_DEG = 45.0
ANGLE_TOL_DEG = 0.5      # how far off a multiple of 45 a segment may sit
EXEMPT_LEN_MM = 0.5      # shorter than this is a pad exit, not a routing choice
COMPLIANCE_MIN_PCT = 99.0
TOP_OFFENDER_NETS = 20
OFFENDERS_PER_NET = 3    # worst segments listed per offending net

# S2: staircases
STAIR_SEG_MAX_MM = 1.0   # a "short" segment for staircase purposes
STAIR_MIN_SEGS = 3       # this many in a row, alternating, is a staircase
STAIR_REPORT = 20

# S3: debris and duplicates
DEBRIS_MIN_MM = 0.05     # anything shorter than this is left-over garbage
OVERLAP_MIN_MM = 0.001   # collinear overlap longer than this is a real overlap
COLLINEAR_OFFSET_MM = 0.001  # perpendicular slop allowed when calling two
                             # segments collinear for the overlap test
DUPE_REPORT = 20

# S4: informational
WORST_NETS = 10

# geometry normalisation
MERGE_ANGLE_TOL_DEG = 0.05  # direction change allowed inside a merged run
SNAP_MM = 0.001             # endpoints this close are the same point

SNAP_NM = int(round(SNAP_MM * NM))


# --------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------


@dataclass
class Seg:
    """one straight piece of track, coordinates in integer nanometres."""

    idx: int
    net: str
    layer: str
    width: int
    x1: int
    y1: int
    x2: int
    y2: int
    pieces: int = 1  # raw segments folded into this one by the merge pass

    @property
    def key(self) -> Tuple[str, str]:
        return (self.layer, self.net)

    @property
    def dx(self) -> int:
        return self.x2 - self.x1

    @property
    def dy(self) -> int:
        return self.y2 - self.y1

    @property
    def length_nm(self) -> float:
        return math.hypot(self.dx, self.dy)

    @property
    def length_mm(self) -> float:
        return self.length_nm / NM

    def angle_deg(self) -> float:
        """direction of travel, folded into [0, 180)."""
        return math.degrees(math.atan2(self.dy, self.dx)) % 180.0

    def angle_error_deg(self) -> float:
        """how far the segment sits from the nearest multiple of 45 deg."""
        if self.dx == 0 and self.dy == 0:
            return 0.0
        # exact cases first: integer nanometres make these lossless, so a
        # perfectly orthogonal or perfectly diagonal track can never be
        # failed by floating-point noise.
        if self.dx == 0 or self.dy == 0 or abs(self.dx) == abs(self.dy):
            return 0.0
        a = self.angle_deg()
        return abs(a - ANGLE_STEP_DEG * round(a / ANGLE_STEP_DEG))

    def compliant(self) -> bool:
        return self.angle_error_deg() <= ANGLE_TOL_DEG

    def exempt(self) -> bool:
        return self.length_mm < EXEMPT_LEN_MM

    def where(self) -> str:
        return "(%.3f, %.3f)->(%.3f, %.3f)" % (
            self.x1 / NM, self.y1 / NM, self.x2 / NM, self.y2 / NM
        )


@dataclass
class Board:
    segs: List[Seg] = field(default_factory=list)
    via_pts: List[Tuple[int, int]] = field(default_factory=list)
    arcs: int = 0
    arc_len_mm: float = 0.0
    source: str = ""


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------


def load_board(path: str) -> Board:
    import pcbnew  # noqa: PLC0415 - optional at import time, required here

    pcb = pcbnew.LoadBoard(path)
    out = Board(source="pcbnew %s" % pcbnew.GetBuildVersion())
    idx = 0
    for t in pcb.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetStart()
            out.via_pts.append((int(p.x), int(p.y)))
            continue
        layer = pcb.GetLayerName(t.GetLayer())
        if isinstance(t, pcbnew.PCB_ARC):
            # a deliberate curve is not an angle violation; count it so it
            # cannot silently vanish from the length totals.
            out.arcs += 1
            out.arc_len_mm += t.GetLength() / NM
            continue
        s, e = t.GetStart(), t.GetEnd()
        out.segs.append(
            Seg(
                idx=idx,
                net=t.GetNetname() or "<no net>",
                layer=layer,
                width=int(t.GetWidth()),
                x1=int(s.x), y1=int(s.y), x2=int(e.x), y2=int(e.y),
            )
        )
        idx += 1
    return out


# --------------------------------------------------------------------------
# point index: endpoints within SNAP_NM are the same node
# --------------------------------------------------------------------------


class PointIndex:
    def __init__(self, snap: int = SNAP_NM) -> None:
        self.snap = snap
        self.cells: Dict[Tuple[int, int], List[int]] = {}
        self.pts: List[Tuple[int, int]] = []

    def _cell(self, x: int, y: int) -> Tuple[int, int]:
        return (x // self.snap, y // self.snap)

    def find(self, x: int, y: int) -> Optional[int]:
        cx, cy = self._cell(x, y)
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                for pid in self.cells.get((cx + ox, cy + oy), ()):
                    px, py = self.pts[pid]
                    if abs(px - x) <= self.snap and abs(py - y) <= self.snap:
                        return pid
        return None

    def add(self, x: int, y: int) -> int:
        pid = self.find(x, y)
        if pid is not None:
            return pid
        pid = len(self.pts)
        self.pts.append((x, y))
        self.cells.setdefault(self._cell(x, y), []).append(pid)
        return pid


# --------------------------------------------------------------------------
# chain building and collinear merging
# --------------------------------------------------------------------------


Oriented = Tuple[int, int, int]  # (seg index, from pid, to pid)


def build_chains(segs: Sequence[Seg], via_pts: Sequence[Tuple[int, int]]):
    """group segments into ordered polylines, per (layer, net).

    a chain runs through nodes where exactly two segments of the same net and
    layer meet and no via lands.  anything else - a tee, a via, a dead end -
    ends the chain, because that is a real feature of the routing rather than
    an artefact of how many objects the router emitted.
    """
    index = PointIndex()
    ends: List[Tuple[int, int]] = []
    for s in segs:
        ends.append((index.add(s.x1, s.y1), index.add(s.x2, s.y2)))

    via_pids = set()
    for (vx, vy) in via_pts:
        pid = index.find(vx, vy)
        if pid is not None:
            via_pids.add(pid)

    groups: Dict[Tuple[str, str], List[int]] = collections.defaultdict(list)
    for s in segs:
        groups[s.key].append(s.idx)

    chains: List[List[Oriented]] = []
    for _key, members in sorted(groups.items()):
        adj: Dict[int, List[int]] = collections.defaultdict(list)
        for i in members:
            a, b = ends[i]
            adj[a].append(i)
            if b != a:
                adj[b].append(i)

        def through(pid: int) -> bool:
            return len(adj[pid]) == 2 and pid not in via_pids

        def other_seg(pid: int, seg: int) -> int:
            pair = adj[pid]
            return pair[0] if pair[1] == seg else pair[1]

        def other_end(seg: int, pid: int) -> int:
            a, b = ends[seg]
            return b if a == pid else a

        used = set()
        for start in members:
            if start in used:
                continue
            used.add(start)
            a, b = ends[start]
            chain: List[Oriented] = [(start, a, b)]

            # extend forward off the far end
            cur_seg, cur_pt = start, b
            while through(cur_pt):
                nxt = other_seg(cur_pt, cur_seg)
                if nxt in used:
                    break  # closed loop
                used.add(nxt)
                nxt_end = other_end(nxt, cur_pt)
                chain.append((nxt, cur_pt, nxt_end))
                cur_seg, cur_pt = nxt, nxt_end

            # and backward off the near end
            cur_seg, cur_pt = start, a
            while through(cur_pt):
                prv = other_seg(cur_pt, cur_seg)
                if prv in used:
                    break
                used.add(prv)
                prv_start = other_end(prv, cur_pt)
                chain.insert(0, (prv, prv_start, cur_pt))
                cur_seg, cur_pt = prv, prv_start

            chains.append(chain)
    return chains, index, ends


def _angle_between(dx1: float, dy1: float, dx2: float, dy2: float) -> float:
    """unsigned angle between two direction vectors, in degrees."""
    n1 = math.hypot(dx1, dy1)
    n2 = math.hypot(dx2, dy2)
    if n1 == 0 or n2 == 0:
        return 0.0
    dot = (dx1 * dx2 + dy1 * dy2) / (n1 * n2)
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


def merge_chain(segs: Sequence[Seg], chain: Sequence[Oriented],
                index: PointIndex) -> List[Seg]:
    """fold consecutive collinear same-width pieces of one chain together.

    the running comparison is against the accumulated segment, not against the
    previous piece, so a long chain of 0.04 deg steps cannot drift its way
    around a corner one hair at a time.
    """
    out: List[Seg] = []
    for (i, a, b) in chain:
        s = segs[i]
        ax, ay = index.pts[a]
        bx, by = index.pts[b]
        if out:
            prev = out[-1]
            same_width = prev.width == s.width
            straight = _angle_between(prev.dx, prev.dy, bx - ax, by - ay) <= MERGE_ANGLE_TOL_DEG
            if same_width and straight:
                out[-1] = Seg(
                    idx=prev.idx, net=prev.net, layer=prev.layer, width=prev.width,
                    x1=prev.x1, y1=prev.y1, x2=bx, y2=by,
                    pieces=prev.pieces + 1,
                )
                continue
        out.append(
            Seg(idx=s.idx, net=s.net, layer=s.layer, width=s.width,
                x1=ax, y1=ay, x2=bx, y2=by, pieces=1)
        )
    return out


# --------------------------------------------------------------------------
# assertion plumbing (same shape as check_rev6_pcb.py)
# --------------------------------------------------------------------------


class Report:
    def __init__(self) -> None:
        self.results: List[Tuple[str, str, bool, List[str]]] = []

    def add(self, ident: str, title: str, ok: bool,
            detail: Optional[List[str]] = None) -> bool:
        self.results.append((ident, title, ok, detail or []))
        return ok

    @property
    def failures(self) -> List[Tuple[str, str, bool, List[str]]]:
        return [r for r in self.results if not r[2]]

    def emit(self) -> None:
        for ident, title, ok, detail in self.results:
            print("%-4s %-4s %s" % (ident, "PASS" if ok else "FAIL", title))
            for line in detail:
                print("          %s" % line)


# --------------------------------------------------------------------------
# S1: angle discipline
# --------------------------------------------------------------------------


def check_s1(rep: Report, merged: Sequence[Seg]) -> None:
    total = sum(s.length_mm for s in merged)
    exempt_len = 0.0
    good_len = 0.0
    bad_len = 0.0
    bad: List[Seg] = []
    for s in merged:
        L = s.length_mm
        if s.exempt():
            exempt_len += L
        elif s.compliant():
            good_len += L
        else:
            bad_len += L
            bad.append(s)

    # the headline number reads the rule literally: exempt copper does not
    # count against the layout.  the strict number (exempt copper excluded
    # from the numerator) is printed beside it so the exemption can never
    # quietly become the place where the ugly length hides.
    pct = 100.0 * (good_len + exempt_len) / total if total else 100.0
    strict_base = good_len + bad_len
    strict = 100.0 * good_len / strict_base if strict_base else 100.0
    ok = pct >= COMPLIANCE_MIN_PCT

    detail = [
        "routed length %.3f mm over %d merged segments" % (total, len(merged)),
        "on-angle %.3f mm | exempt (<%.2f mm) %.3f mm (%.2f%% of total) | "
        "off-angle %.3f mm across %d segments"
        % (good_len, EXEMPT_LEN_MM, exempt_len, (100.0 * exempt_len / total) if total else 0.0,
           bad_len, len(bad)),
        "compliance %.3f%% (need >= %.1f%%), strict %.3f%%, tolerance %.1f deg"
        % (pct, COMPLIANCE_MIN_PCT, strict, ANGLE_TOL_DEG),
    ]

    if bad:
        per_net: Dict[str, List[Seg]] = collections.defaultdict(list)
        for s in bad:
            per_net[s.net].append(s)
        ranked = sorted(
            per_net.items(),
            key=lambda kv: sum(x.length_mm for x in kv[1]),
            reverse=True,
        )
        shown = min(TOP_OFFENDER_NETS, len(ranked))
        detail.append("top %d offending nets by off-angle length:" % shown)
        for net, items in ranked[:TOP_OFFENDER_NETS]:
            nlen = sum(x.length_mm for x in items)
            detail.append(
                "  %-22s %8.3f mm  %3d seg  (%.2f%% of all off-angle)"
                % (net, nlen, len(items), 100.0 * nlen / bad_len if bad_len else 0.0)
            )
            for s in sorted(items, key=lambda x: x.length_mm, reverse=True)[:OFFENDERS_PER_NET]:
                detail.append(
                    "      %-5s %7.3f mm  %6.2f deg (err %.2f)  %s"
                    % (s.layer, s.length_mm, s.angle_deg(), s.angle_error_deg(), s.where())
                )
        if len(ranked) > TOP_OFFENDER_NETS:
            detail.append("  ... and %d more nets" % (len(ranked) - TOP_OFFENDER_NETS))

    rep.add("S1", "track length on 45 deg multiples >= %.1f%%" % COMPLIANCE_MIN_PCT,
            ok, detail)


# --------------------------------------------------------------------------
# S2: staircases
# --------------------------------------------------------------------------


@dataclass
class Stair:
    net: str
    layer: str
    count: int
    length_mm: float
    start: Tuple[float, float]
    end: Tuple[float, float]


def _turn_sign(a: Seg, b: Seg) -> int:
    cross = a.dx * b.dy - a.dy * b.dx
    if cross > 0:
        return 1
    if cross < 0:
        return -1
    return 0


def find_staircases(chains_merged: Sequence[Sequence[Seg]]) -> List[Stair]:
    found: List[Stair] = []
    for chain in chains_merged:
        n = len(chain)
        if n < STAIR_MIN_SEGS:
            continue
        lens = [s.length_mm for s in chain]
        turns = [_turn_sign(chain[i], chain[i + 1]) for i in range(n - 1)]

        k = 0
        while k < n:
            if lens[k] >= STAIR_SEG_MAX_MM:
                k += 1
                continue
            j = k
            while (j + 1 < n
                   and lens[j + 1] < STAIR_SEG_MAX_MM
                   and turns[j] != 0
                   and (j == k or turns[j] == -turns[j - 1])):
                j += 1
            if j - k + 1 >= STAIR_MIN_SEGS:
                run = chain[k:j + 1]
                found.append(
                    Stair(
                        net=run[0].net,
                        layer=run[0].layer,
                        count=len(run),
                        length_mm=sum(x.length_mm for x in run),
                        start=(run[0].x1 / NM, run[0].y1 / NM),
                        end=(run[-1].x2 / NM, run[-1].y2 / NM),
                    )
                )
            k = j + 1
    return found


def check_s2(rep: Report, chains_merged: Sequence[Sequence[Seg]]) -> None:
    stairs = find_staircases(chains_merged)
    detail = [
        "a staircase is >= %d consecutive segments, each < %.1f mm, with "
        "alternating turn directions" % (STAIR_MIN_SEGS, STAIR_SEG_MAX_MM),
        "found %d" % len(stairs),
    ]
    if stairs:
        worst = sorted(stairs, key=lambda s: (s.count, s.length_mm), reverse=True)
        for s in worst[:STAIR_REPORT]:
            detail.append(
                "  %-22s %-5s %2d seg %7.3f mm  (%.3f, %.3f)->(%.3f, %.3f)"
                % (s.net, s.layer, s.count, s.length_mm,
                   s.start[0], s.start[1], s.end[0], s.end[1])
            )
        if len(stairs) > STAIR_REPORT:
            detail.append("  ... and %d more" % (len(stairs) - STAIR_REPORT))
    rep.add("S2", "no staircase runs", not stairs, detail)


# --------------------------------------------------------------------------
# S3: debris and duplicate/overlapping copper
# --------------------------------------------------------------------------


def _overlap_len_mm(a: Seg, b: Seg) -> float:
    """length the two segments share while lying on the same line, in mm.

    returns 0.0 when they are not collinear, or only touch end to end.
    """
    la, lb = a.length_nm, b.length_nm
    if la == 0 or lb == 0:
        return 0.0
    # parallel?  direction is unsigned here: antiparallel copper overlaps
    # exactly as much as parallel copper does.
    ang = _angle_between(a.dx, a.dy, b.dx, b.dy)
    if min(ang, 180.0 - ang) > 0.5:
        return 0.0
    # same infinite line?  perpendicular distance of b's ends from a's line.
    ux, uy = a.dx / la, a.dy / la
    tol = COLLINEAR_OFFSET_MM * NM
    for (px, py) in ((b.x1, b.y1), (b.x2, b.y2)):
        perp = abs((px - a.x1) * uy - (py - a.y1) * ux)
        if perp > tol:
            return 0.0
    # 1-d overlap along a's direction
    t0 = 0.0
    t1 = la
    s0 = (b.x1 - a.x1) * ux + (b.y1 - a.y1) * uy
    s1 = (b.x2 - a.x1) * ux + (b.y2 - a.y1) * uy
    if s0 > s1:
        s0, s1 = s1, s0
    lo = max(t0, s0)
    hi = min(t1, s1)
    return max(0.0, (hi - lo) / NM)


def check_s3(rep: Report, segs: Sequence[Seg]) -> None:
    debris = [s for s in segs if s.length_mm < DEBRIS_MIN_MM]

    groups: Dict[Tuple[str, str], List[Seg]] = collections.defaultdict(list)
    for s in segs:
        groups[s.key].append(s)

    dupes: List[Tuple[Seg, Seg, float, bool]] = []
    for _key, members in sorted(groups.items()):
        n = len(members)
        for i in range(n):
            a = members[i]
            for j in range(i + 1, n):
                b = members[j]
                same = ((a.x1, a.y1, a.x2, a.y2) == (b.x1, b.y1, b.x2, b.y2)
                        or (a.x1, a.y1, a.x2, a.y2) == (b.x2, b.y2, b.x1, b.y1))
                ov = _overlap_len_mm(a, b)
                if same or ov > OVERLAP_MIN_MM:
                    dupes.append((a, b, ov, same))

    detail = [
        "%d segments checked; shortest %.4f mm"
        % (len(segs), min((s.length_mm for s in segs), default=0.0)),
        "debris (< %.2f mm): %d" % (DEBRIS_MIN_MM, len(debris)),
        "duplicate / overlapping same-net pairs: %d" % len(dupes),
    ]
    for s in sorted(debris, key=lambda x: x.length_mm)[:DUPE_REPORT]:
        detail.append("  debris %-22s %-5s %.4f mm  %s"
                      % (s.net, s.layer, s.length_mm, s.where()))
    if len(debris) > DUPE_REPORT:
        detail.append("  ... and %d more debris segments" % (len(debris) - DUPE_REPORT))
    for (a, b, ov, same) in sorted(dupes, key=lambda t: t[2], reverse=True)[:DUPE_REPORT]:
        detail.append("  %s %-22s %-5s %.3f mm shared  %s | %s"
                      % ("dup " if same else "over", a.net, a.layer, ov,
                         a.where(), b.where()))
    if len(dupes) > DUPE_REPORT:
        detail.append("  ... and %d more pairs" % (len(dupes) - DUPE_REPORT))

    rep.add("S3", "no debris segments, no duplicate or overlapping copper",
            not debris and not dupes, detail)


# --------------------------------------------------------------------------
# S4: per-net segment counts (informational)
# --------------------------------------------------------------------------


def check_s4(rep: Report, segs: Sequence[Seg], merged: Sequence[Seg]) -> None:
    raw: Dict[str, int] = collections.Counter(s.net for s in segs)
    mrg: Dict[str, int] = collections.Counter(s.net for s in merged)
    lens: Dict[str, float] = collections.defaultdict(float)
    for s in segs:
        lens[s.net] += s.length_mm

    ranked = sorted(raw.items(), key=lambda kv: kv[1], reverse=True)
    detail = [
        "%d nets carry copper; %d raw segments merge to %d"
        % (len(raw), len(segs), len(merged)),
        "%-22s %5s %7s %10s %9s" % ("net", "raw", "merged", "length mm", "mm/seg"),
    ]
    for net, count in ranked[:WORST_NETS]:
        m = mrg.get(net, 0)
        detail.append(
            "  %-22s %4d %6d %10.3f %9.3f"
            % (net, count, m, lens[net], lens[net] / m if m else 0.0)
        )
    rep.add("S4", "per-net segment counts (informational)", True, detail)


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

    try:
        board = load_board(board_path)
    except ImportError:
        print("pcbnew python module not available - this checker needs it",
              file=sys.stderr)
        return 2

    chains, index, _ends = build_chains(board.segs, board.via_pts)
    chains_merged = [merge_chain(board.segs, c, index) for c in chains]
    merged = [s for c in chains_merged for s in c]

    print("board  : %s" % board_path)
    print("backend: %s" % board.source)
    print("content: %d track segments, %d vias, %d arcs (%.3f mm), "
          "%d chains, %d merged segments"
          % (len(board.segs), len(board.via_pts), board.arcs, board.arc_len_mm,
             len(chains), len(merged)))
    print()

    rep = Report()
    check_s1(rep, merged)
    check_s2(rep, chains_merged)
    check_s3(rep, board.segs)
    check_s4(rep, board.segs, merged)

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
