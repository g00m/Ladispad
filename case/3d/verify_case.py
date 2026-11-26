#!/usr/bin/env python
"""
Verify the generated Ladispad case STLs against the source SVG geometry.

Checks, per layer:
  - mesh is watertight, volume == face area x thickness
  - bounding box matches the SVG canvas footprint
  - a cross-section at mid-thickness matches the source 2D face
    (symmetric-difference area ~ 0)
And for the stack:
  - the 4 corner screw holes line up through all four layers
  - the fused STL is one connected solid spanning z = 0..22 mm
"""
import os
import sys

import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import case_geom as cg
from build_case import LAYERS, build_face, SVG_DIR, OUT_DIR

SCREW_XY = [(5.60, 92.28), (102.16, 92.00), (5.49, 5.70), (101.99, 5.70)]


def slice_polys(mesh, z):
    """Cross-section of a mesh at height z -> shapely (multi)polygon with holes."""
    section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if section is None:
        return Polygon()
    path2d, to_3d = section.to_planar()
    polys = list(path2d.polygons_full)
    if not polys:
        return Polygon()
    # to_planar() re-centres the 2D frame; shift back to original XY
    return affinity.translate(unary_union(polys), to_3d[0][3], to_3d[1][3])


def main():
    ok = True
    faces = {}
    print("=== per-layer checks")
    for fname, thick, z0, stl in LAYERS:
        face, info = build_face(cg.load_layer(os.path.join(SVG_DIR, fname)), fname)
        faces[stl] = (face, thick, z0)
        mesh = trimesh.load(os.path.join(OUT_DIR, stl), force="mesh")
        b = mesh.bounds
        sl = slice_polys(mesh, z0 + thick / 2.0)
        diff = sl.symmetric_difference(face).area
        checks = [
            ("watertight", mesh.is_watertight),
            ("volume==area*thick", abs(mesh.volume - face.area * thick) < 1.0),
            ("z-range", abs(b[0][2] - z0) < 1e-6 and abs(b[1][2] - (z0 + thick)) < 1e-6),
            ("footprint", abs(b[0][0] - 1.05) < 0.05 and abs(b[1][0] - 106.50) < 0.05
                          and abs(b[0][1] - 1.05) < 0.05 and abs(b[1][1] - 96.34) < 0.05),
            ("section matches svg (<1mm2)", diff < 1.0),
        ]
        for label, good in checks:
            if not good:
                ok = False
            print(f"  {stl:32s} {label:28s} {'PASS' if good else 'FAIL'}")
        print(f"      A={face.area:.1f}mm2 V={mesh.volume:.1f}mm3 z=[{b[0][2]:.2f},{b[1][2]:.2f}] "
              f"section_diff={diff:.4f}mm2")

    print("\n=== screw-hole alignment through the stack")
    for (x, y) in SCREW_XY:
        holes = []
        for fname, thick, z0, stl in LAYERS:
            mesh = trimesh.load(os.path.join(OUT_DIR, stl), force="mesh")
            sl = slice_polys(mesh, z0 + thick / 2.0)
            holes.append(not sl.contains(__import__("shapely").geometry.Point(x, y)))
        good = all(holes)
        ok &= good
        print(f"  ({x:6.2f},{y:6.2f}) open in all layers: {holes}  {'PASS' if good else 'FAIL'}")

    print("\n=== fused stack")
    fused = trimesh.load(os.path.join(OUT_DIR, "ladispad_case_fused.stl"), force="mesh")
    b = fused.bounds
    parts = fused.split(only_watertight=False)
    checks = [
        ("watertight", fused.is_watertight),
        ("single connected solid", len(parts) == 1),
        ("height 22mm", abs((b[1][2] - b[0][2]) - 22.0) < 1e-6),
        ("volume == sum of layers",
         abs(fused.volume - sum(m.volume for m in
             [trimesh.load(os.path.join(OUT_DIR, s), force="mesh") for _, _, _, s in LAYERS])) < 1.0),
    ]
    for label, good in checks:
        if not good:
            ok = False
        print(f"  {label:28s} {'PASS' if good else 'FAIL'}")
    print(f"      bbox x[{b[0][0]:.2f},{b[1][0]:.2f}] y[{b[0][1]:.2f},{b[1][1]:.2f}] z[{b[0][2]:.2f},{b[1][2]:.2f}] V={fused.volume:.1f}mm3")

    print("\n=== fused cross-sections vs source layers")
    for fname, thick, z0, stl in LAYERS:
        sl = slice_polys(fused, z0 + thick / 2.0)
        diff = sl.symmetric_difference(faces[stl][0]).area
        good = diff < 1.0
        ok &= good
        print(f"  z={z0 + thick/2:5.1f} ({stl:28s}) diff={diff:8.4f}mm2  {'PASS' if good else 'FAIL'}")

    print("\nRESULT:", "ALL CHECKS PASSED" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
