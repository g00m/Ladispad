#!/usr/bin/env python
"""
Ladispad case STL builder.

Converts the four laser-cut acrylic case SVGs (Fusion 360 exports) into
printable STLs:

  case/  <4 per-layer STLs>  - each layer extruded to its acrylic thickness
  case/  ladispad_case_fused.stl - the four layers stacked as one solid
  case/  preview_<layer>.png  - flat face previews for verification

Layer stack (z-up, mm): bottom 3 | middle 1 8 | middle 2 8 | top 3 = 22 mm.
All layers keep the SVG planar orientation (no flips), so a printed case
assembles exactly like the laser-cut acrylic one.
"""
import os
import sys

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import case_geom as cg

HERE = os.path.dirname(os.path.abspath(__file__))       # .../Ladispad/case/3d
SVG_DIR = os.path.dirname(HERE)                          # .../Ladispad/case (has the SVGs)
OUT_DIR = HERE

LAYERS = [
    # (svg file, thickness mm, base z mm, stl name)
    ("case-bottom layer.svg",     3.0,  0.0, "ladispad_case_bottom.stl"),
    ("case-middle layer.svg",     8.0,  3.0, "ladispad_case_middle1.stl"),
    ("case-middle layer 2.svg",   8.0, 11.0, "ladispad_case_middle2.stl"),
    ("top layer edited.svg",      3.0, 19.0, "ladispad_case_top.stl"),
]


def classify(elems):
    """Split layer elements into:
       bands (lens corner bands), members (stitchable segments),
       loops (ready closed polylines), holes (circles)."""
    all_pts = []
    for e in elems:
        if e["kind"] == "circle":
            all_pts.append(e["points"])
        else:
            all_pts.append(cg.subpath_pts(e["sp"]))
    all_pts = np.vstack(all_pts)
    ref_center = (all_pts[:, 0].mean(), all_pts[:, 1].mean())

    members, loops, holes, bands = [], [], [], []
    for e in elems:
        if e["kind"] == "circle":
            holes.append(Polygon(e["points"]))
            continue
        sp = e["sp"]
        if cg.is_corner_band(sp):
            arc = cg.band_outer_arc(sp, ref_center)
            bands.append(arc)
            members.append(cg.dedupe(arc["pts"]))
            continue
        pts = cg.subpath_pts(sp)
        pts = cg.dedupe(pts)
        if len(pts) < 2:
            continue
        area = cg.signed_area(pts)
        if abs(area) < 1e-6:
            # degenerate straight edge (double line) -> segment
            if len(pts) >= 2:
                members.append(np.array([pts[0], pts[-1]]))
        elif sp["closed"]:
            loops.append(pts)
        else:
            members.append(pts)
    return members, loops, holes, bands


def build_face(elems, name):
    members, loops, holes, bands = classify(elems)
    cycles, leftovers = cg.stitch(members)
    # Fusion exports arc endpoints with fewer digits than line endpoints, which
    # leaves ~1e-6 mm near-duplicate vertices -> degenerate mesh faces. Merge them.
    JOIN_TOL = 1e-3
    polys = list(loops)
    for cyc in cycles:
        # concatenate oriented member polylines, deduping shared joints
        pts = []
        for _, poly in cyc:
            for p in poly:
                if not pts or np.hypot(*(np.asarray(p) - pts[-1])) > JOIN_TOL:
                    pts.append(tuple(p))
        if len(pts) >= 3:
            pts = np.array(pts)
            if np.hypot(*(pts[0] - pts[-1])) < JOIN_TOL:
                pts = pts[:-1]
            polys.append(pts)
    if leftovers:
        print(f"  [{name}] WARN: {len(leftovers)} un-stitched segments")
    for idx, p in enumerate(polys):
        if cg.signed_area(p) < 0:
            polys[idx] = p[::-1]
    # ensure consistent CCW orientation via shapely
    shapely_polys = []
    for p in polys:
        try:
            poly = Polygon(cg.dedupe(np.asarray(p, float), JOIN_TOL))
            if len(poly.exterior.coords) < 4:
                continue
            poly = poly.simplify(1e-4, preserve_topology=True)
        except Exception as ex:
            print(f"  [{name}] WARN: bad polygon skipped ({ex})")
            continue
        if not poly.is_valid:
            poly = make_valid(poly)
        shapely_polys.append(poly)
    if not shapely_polys:
        raise RuntimeError(f"{name}: no polygons")
    shapely_polys.sort(key=lambda q: abs(q.area), reverse=True)
    outer = shapely_polys[0]
    cutouts = shapely_polys[1:]
    for c in cutouts:
        if not outer.contains(c.representative_point()):
            print(f"  [{name}] WARN: cutout not fully inside outer")
    face = outer
    for c in cutouts:
        face = face.difference(c)
    material_holes, void_holes = [], []
    for h in holes:
        if face.contains(h.representative_point()):
            material_holes.append(h)
        else:
            void_holes.append(h)
    for h in material_holes:
        face = face.difference(h)
    if not face.is_valid:
        face = make_valid(face)
    info = {
        "face": face, "bands": len(bands), "loops": len(loops),
        "stitched": len(cycles), "members": len(members),
        "holes": len(holes), "mat_holes": len(material_holes),
        "void_holes": len(void_holes), "cutouts": len(cutouts),
    }
    return face, info


def to_mesh(face, z0, z1):
    import trimesh
    if face.geom_type == "MultiPolygon":
        meshes = [trimesh.creation.extrude_polygon(Polygon(p.exterior, p.interiors), z1 - z0)
                  for p in face.geoms]
        m = trimesh.util.concatenate(meshes)
    else:
        m = trimesh.creation.extrude_polygon(Polygon(face.exterior, list(face.interiors)), z1 - z0)
    m.apply_translation([0, 0, z0])
    if not m.is_watertight:
        m.fix_normals()
        if not m.is_watertight:
            m.fill_holes()
    return m


def preview(face, path, name):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from shapely.ops import unary_union
    polys = list(face.geoms) if face.geom_type == "MultiPolygon" else [face]
    fig, ax = plt.subplots(figsize=(6.6, 6.0))
    for p in polys:
        xs, ys = p.exterior.xy
        ax.plot(xs, ys, "k-", lw=0.7)
        ax.fill(xs, ys, color="tab:blue", alpha=0.35)
        for ring in p.interiors:
            xs, ys = ring.xy
            ax.plot(xs, ys, "k-", lw=0.7)
            ax.fill(xs, ys, color="white", alpha=0.9)
    bb = np.vstack([np.array(p.exterior.coords) for p in polys])
    ax.set_xlim(bb[:, 0].min() - 3, bb[:, 0].max() + 3)
    ax.set_ylim(bb[:, 1].min() - 3, bb[:, 1].max() + 3)
    ax.set_aspect("equal")
    ax.set_title(f"{name}  ({abs(face.area):.0f} mm2)")
    ax.grid(alpha=0.3)
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)


def main():
    import trimesh
    meshes = []
    ok = True
    for fname, thick, z0, stl in LAYERS:
        path = os.path.join(SVG_DIR, fname)
        print(f"== {fname}")
        elems = cg.load_layer(path)
        face, info = build_face(elems, fname)
        a = face.area
        print(f"   face A={a:.1f} mm2  (bands={info['bands']} loops={info['loops']} "
              f"stitched={info['stitched']} cutouts={info['cutouts']} "
              f"holes={info['holes']} [material={info['mat_holes']}, void={info['void_holes']}])")
        m = to_mesh(face, z0, z0 + thick)
        print(f"   mesh watertight={m.is_watertight} V={m.volume:.1f} mm3  (expect~{a * thick:.0f})")
        if not m.is_watertight:
            ok = False
            print(f"   FAIL: not watertight")
        out = os.path.join(OUT_DIR, stl)
        m.export(out)
        print(f"   wrote {stl}")
        pv = os.path.join(OUT_DIR, "preview_" + stl.replace("ladispad_case_", "").replace(".stl", ".png"))
        preview(face, pv, fname)
        meshes.append(m)
    # fused single body
    try:
        fused = trimesh.boolean.union(meshes, engine="manifold")
        name = "ladispad_case_fused.stl"
        print(f"== fused: watertight={fused.is_watertight} V={fused.volume:.1f} mm3 "
              f"(parts sum={sum(x.volume for x in meshes):.1f})  H={fused.bounds[1][1]:.2f}mm")
        if fused.is_watertight:
            fused.export(os.path.join(OUT_DIR, name))
            print(f"   wrote {name}")
        else:
            trimesh.util.concatenate(meshes).export(os.path.join(OUT_DIR, name))
            print(f"   wrote {name} (concatenated, not unioned)")
    except Exception as ex:
        trimesh.util.concatenate(meshes).export(os.path.join(OUT_DIR, "ladispad_case_fused.stl"))
        print(f"   union failed ({ex}); wrote concatenated fused file")
    print("DONE", "OK" if ok else "WITH FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
