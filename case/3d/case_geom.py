#!/usr/bin/env python
"""Ladispad case geometry: Fusion-360 SVG -> segment-level mm geometry."""
import math
import re
import xml.etree.ElementTree as ET

import numpy as np

SVG_NS = "{http://www.w3.org/2000/svg}"
TOKEN = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])|([-+]?(?:\d*\.?\d+|\d+\.?)(?:e[-+]?\d+)?)")
ARC_SAMPLES = 64


def tokenize(d):
    out, cur, cmd = [], [], None
    for m in TOKEN.finditer(d):
        if m.group(1):
            if cmd is not None:
                out.append((cmd, cur))
            cmd, cur = m.group(1), []
        elif m.group(2):
            if cmd is None:
                raise ValueError("number before command: %r" % d[:40])
            cur.append(float(m.group(2)))
    if cmd is not None:
        out.append((cmd, cur))
    return out


def parse_transform(t):
    M = np.eye(3)
    if not t:
        return M
    for op in re.findall(r"(matrix|translate|scale|rotate)\(([^)]*)\)", t):
        fn, a = op[0], [float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:e[-+]?\d+)?", op[1])]
        if fn == "matrix" and len(a) == 6:
            m = np.array([a[0], a[1], 0, a[2], a[3], 0, a[4], a[5], 1]).reshape(3, 3)
        elif fn == "translate":
            m = np.array([1, 0, a[0], 0, 1, a[1] or 0, 0, 0, 1]).reshape(3, 3)
        elif fn == "scale":
            sx, sy = a[0], a[1] if len(a) > 1 else a[0]
            m = np.array([sx, 0, 0, 0, sy, 0, 0, 0, 1]).reshape(3, 3)
        elif fn == "rotate" and len(a) == 1:
            r = math.radians(a[0])
            m = np.array([math.cos(r), -math.sin(r), 0, math.sin(r), math.cos(r), 0, 0, 0, 1]).reshape(3, 3)
        else:
            continue
        M = M @ m
    return M


def _arc_pts(x1, y1, rx, ry, psi, large, sweep, x2, y2, n):
    if rx == 0 or ry == 0:
        return [(x2, y2)], (x2, y2)
    rx, ry = abs(rx), abs(ry)
    ps = math.radians(psi)
    cp, sp = math.cos(ps), math.sin(ps)
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1:
        s = math.sqrt(lam)
        rx, ry = s * rx, s * ry
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    co = math.sqrt(max(num / den, 0.0))
    if large == sweep:
        co = -co
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx, cy = cp * cxp - sp * cyp + (x1 + x2) / 2, sp * cxp + cp * cyp + (y1 + y2) / 2

    def ang(ax, ay, bx, by):
        return math.atan2(ax * by - ay * bx, ax * bx + ay * by)

    th1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dth = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dth > 0:
        dth -= 2 * math.pi
    elif sweep and dth < 0:
        dth += 2 * math.pi
    pts = []
    for i in range(1, n + 1):
        t = th1 + dth * i / n
        pts.append((cp * rx * math.cos(t) - sp * ry * math.sin(t) + cx,
                    sp * rx * math.cos(t) + cp * ry * math.sin(t) + cy))
    return pts, (cx, cy)


def _cubic(p0, p1, p2, p3, n=24):
    t = np.linspace(0, 1, n)[1:]
    return [( (1-ti)**3*p0[0] + 3*(1-ti)**2*ti*p1[0] + 3*(1-ti)*ti*ti*p2[0] + ti**3*p3[0],
             (1-ti)**3*p0[1] + 3*(1-ti)**2*ti*p1[1] + 3*(1-ti)*ti*ti*p2[1] + ti**3*p3[1]) for ti in t]


def _quad(p0, p1, p2, n=16):
    t = np.linspace(0, 1, n)[1:]
    return [( (1-ti)**2*p0[0] + 2*(1-ti)*ti*p1[0] + ti*ti*p2[0],
             (1-ti)**2*p0[1] + 2*(1-ti)*ti*p1[1] + ti*ti*p2[1]) for ti in t]


def parse_subpaths(d, M):
    """Path data -> list of subpaths. seg = dict(kind, pts(N,2 incl start), p0, p1, arc_center)."""
    out, segs = [], []
    cx = cy = 0.0
    ctrl = None

    def apply_pts(raw):
        v = np.atleast_2d(np.array(raw, float))
        vh = np.hstack([v, np.ones((v.shape[0], 1))])
        return (vh @ M.T)[:, :2]

    def seg(p0, pts, kind, center=None):
        raw = [p0] + [tuple(p) for p in pts]
        arr = apply_pts(raw)
        ctr = apply_pts([center])[:, :2][0] if center is not None else None
        segs.append({"kind": kind, "pts": arr, "p0": arr[0], "p1": arr[-1], "arc_center": ctr})

    for cmd, args in tokenize(d):
        if not args:
            # zero-arg command (Z): the while loop below would never run for it
            if cmd in "Zz":
                out.append({"closed": True, "segs": segs})
                segs = []
            continue
        i = 0
        while i < len(args):
            c = cmd
            step = 2 if c in "ML" else 1 if c in "HV" else 4 if c in "CSQ" else 2 if c == "T" else 7 if c == "A" else 0
            if c in "Zz":
                out.append({"closed": True, "segs": segs})
                segs = []
                i += 1
                continue
            if i + step > len(args):
                break
            a = args[i:i + step]
            i += step
            if c in "Mm":
                if segs:
                    out.append({"closed": False, "segs": segs})
                    segs = []
                cx, cy = (a[0], a[1]) if c == "M" else (cx + a[0], cy + a[1])
                seg((cx, cy), [], "point")
                continue
            if c in "LlHhVv":
                if c == "L":
                    nx, ny = a[0], a[1]
                elif c == "l":
                    nx, ny = cx + a[0], cy + a[1]
                elif c == "H":
                    nx, ny = a[0], cy
                elif c == "h":
                    nx, ny = cx + a[0], cy
                elif c == "V":
                    nx, ny = cx, a[0]
                else:
                    nx, ny = cx, cy + a[0]
                seg((cx, cy), [(nx, ny)], "line")
                cx, cy = nx, ny
            elif c in "CcSs":
                if c in "Cc":
                    x1, y1, x2, y2, ex, ey = (a if c == "C" else [cx + a[0], cy + a[1], cx + a[2], cy + a[3], cx + a[4], cy + a[5]])
                else:
                    c1 = (cx, cy) if ctrl is None else (2*cx - ctrl[0], 2*cy - ctrl[1])
                    x2, y2, ex, ey = (a if c == "S" else [cx + a[0], cy + a[1], cx + a[2], cy + a[3]])
                    seg((cx, cy), _cubic((cx, cy), c1, (x2, y2), (ex, ey)), "curve")
                    ctrl = (x2, y2); cx, cy = ex, ey; continue
                seg((cx, cy), _cubic((cx, cy), (x1, y1), (x2, y2), (ex, ey)), "curve")
                ctrl = (x2, y2); cx, cy = ex, ey
            elif c in "QqTt":
                if c in "Qq":
                    x1, y1, ex, ey = (a if c == "Q" else [cx + a[0], cy + a[1], cx + a[2], cy + a[3]])
                else:
                    c1 = (cx, cy) if ctrl is None else (2*cx - ctrl[0], 2*cy - ctrl[1])
                    ex, ey = (a if c == "T" else [cx + a[0], cy + a[1]])
                    seg((cx, cy), _quad((cx, cy), c1, (ex, ey)), "curve")
                    ctrl = c1; cx, cy = ex, ey; continue
                seg((cx, cy), _quad((cx, cy), (x1, y1), (ex, ey)), "curve")
                ctrl = (x1, y1); cx, cy = ex, ey
            elif c in "Aa":
                if c == "A":
                    rx, ry, psi, la, sw, ex, ey = a
                else:
                    rx, ry, psi, la, sw, ex, ey = a[0], a[1], a[2], a[3], a[4], cx + a[5], cy + a[6]
                s, ctr = _arc_pts(cx, cy, rx, ry, psi, int(la), int(sw), ex, ey, ARC_SAMPLES)
                seg((cx, cy), s, "arc", ctr)
                cx, cy = ex, ey
    if segs:
        out.append({"closed": False, "segs": segs})
    return [s for s in out if s["segs"]]


def load_layer(f):
    root = ET.parse(f).getroot()
    elems = []
    for g in [root] + list(root.iter()):
        if g.tag not in (SVG_NS + "g", SVG_NS + "svg"):
            continue
        M = parse_transform(g.get("transform"))
        for c in g:
            if c.tag == SVG_NS + "path" and c.get("d"):
                for sp in parse_subpaths(c.get("d"), M):
                    elems.append({"kind": "path", "sp": sp, "id": c.get("id", "")})
            elif c.tag == SVG_NS + "circle":
                try:
                    cx, cy, r = float(c.get("cx")), float(c.get("cy")), float(c.get("r"))
                except (TypeError, ValueError):
                    continue
                a = np.linspace(0, 2 * math.pi, 64)
                v = np.column_stack([cx + r*np.cos(a), cy + r*np.sin(a), np.ones(64)])
                elems.append({"kind": "circle", "points": (v @ M.T)[:, :2], "center": (cx, cy), "r": r})
    return elems


def subpath_pts(sp):
    pts = []
    for s in sp["segs"]:
        v = s["pts"]
        if not pts or math.hypot(pts[-1][0] - v[0][0], pts[-1][1] - v[0][1]) > 1e-9:
            pts.append(tuple(v[0]))
        pts.extend(map(tuple, v[1:]))
    if pts:
        return np.array(pts)
    return np.empty((0, 2))


def dedupe(pts, tol=1e-6):
    out = [tuple(pts[0])]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append(tuple(p))
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= tol:
        out.pop()
    return np.array(out)


def signed_area(pts):
    if len(pts) < 3:
        return 0.0
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def is_corner_band(sp):
    """Lens band: closed subpath of 2 arcs (+ zero-length lines/points)."""
    if not sp["closed"]:
        return False
    kinds = [s["kind"] for s in sp["segs"]]
    arcs = [s for s in sp["segs"] if s["kind"] == "arc"]
    if len(arcs) != 2:
        return False
    for s in sp["segs"]:
        if s["kind"] == "curve":
            return False
        if s["kind"] == "line" and np.hypot(*(s["p1"] - s["p0"])) > 1e-2:
            return False
    return True


def band_outer_arc(sp, ref_center):
    """Of the two lens arcs, keep the one bulging away from ref_center."""
    arcs = [s for s in sp["segs"] if s["kind"] == "arc"]
    best = max(arcs, key=lambda s: np.hypot(*(s["pts"][len(s["pts"]) // 2] - np.array(ref_center))))
    return best


def stitch(members, tol=0.05):
    """Chain members (polylines; endpoints = first/last points) into cycles by endpoint matching.
    Returns (cycles, leftovers); each cycle = list of (member_index, oriented_polyline)."""
    n = len(members)
    used = [False] * n
    cycles, leftovers = [], []

    def close(p, q):
        return np.hypot(*(np.asarray(p, float) - np.asarray(q, float))) < tol

    def orient(j, enter):
        p = members[j]
        if close(p[0], enter):
            return p
        if close(p[-1], enter):
            return p[::-1]
        return None

    for start in range(n):
        if used[start]:
            continue
        chain = [(start, members[start])]
        used[start] = True
        ok = True
        while True:
            end_pt = chain[-1][1][-1]
            found = None
            for j in range(n):
                if used[j]:
                    continue
                o = orient(j, end_pt)
                if o is not None:
                    found = j
                    break
            if found is None:
                ok = close(chain[-1][1][-1], chain[0][1][0])
                break
            j = found
            used[j] = True
            chain.append((j, orient(j, end_pt)))
            if len(chain) > n:
                ok = False
                break
        if ok and close(chain[-1][1][-1], chain[0][1][0]):
            cycles.append(chain)
        else:
            leftovers.extend(poly for _, poly in chain)
    return cycles, leftovers
