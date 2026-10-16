#!/usr/bin/env python3
"""Independent QA compositor for the >=64px fidelity claim (C5).

Reads ONLY assets/branding/logo-mark.svg (parsed for its path `d` and stroke
widths) and re-emits an equivalent SVG with the documented dark-token palette.
It deliberately does not import or read the implementer's generator.

Parameters per the QA brief / assets/branding/README.md:
  canvas 1024x1024 transparent
  plate  <rect x=100 y=100 width=824 height=824 rx=185.4 fill=#1C2124>
  cover  0.6796  -> symbol width = 824*0.6796, centred
  palette  outer/middle #8FA0A4, inner #B4C0C3, vertex square #F4F3F0
"""
import os
import re
import sys

import xml.etree.ElementTree as ET

SRC = "assets/branding/logo-mark.svg"
OUTDIR = ".local/qa/appicon/indep-render"
PLATE = 824.0
ORIGIN = 100.0
COVER = 0.6796
PALETTE = ["#8FA0A4", "#8FA0A4", "#B4C0C3"]  # outer, middle, inner (by document order)


def parse_source():
    tree = ET.parse(SRC)
    root = tree.getroot()
    vb = root.get("viewBox").split()
    vw, vh = float(vb[2]), float(vb[3])
    ns = "{http://www.w3.org/2000/svg}"
    paths = []
    for p in root.iter(ns + "path"):
        paths.append(("path", p.get("d"), float(p.get("stroke-width"))))
    for r in root.iter(ns + "rect"):
        paths.append(("rect", (float(r.get("x")), float(r.get("y")),
                               float(r.get("width")), float(r.get("height"))), None))
    return vw, vh, paths


def build_svg(size):
    vw, vh, items = parse_source()
    sym_w = PLATE * COVER
    scale = sym_w / vw
    x0 = ORIGIN + (PLATE - sym_w) / 2.0
    y0 = ORIGIN + (PLATE - vh * scale) / 2.0
    body = []
    pi = 0
    for kind, data, sw in items:
        if kind == "path":
            body.append(
                f'<path d="{data}" fill="none" stroke="{PALETTE[pi]}" '
                f'stroke-width="{sw}" stroke-linejoin="miter"/>')
            pi += 1
        else:
            x, y, w, h = data
            body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                        f'fill="#F4F3F0"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 1024 1024">'
            f'<rect x="{ORIGIN}" y="{ORIGIN}" width="{PLATE}" height="{PLATE}" '
            f'rx="185.4" fill="#1C2124"/>'
            f'<g transform="translate({x0:.6f},{y0:.6f}) scale({scale:.9f})">'
            + "".join(body) + '</g></svg>')


JS = """
const { chromium } = require('playwright-core');
(async () => {
  const fs = require('fs');
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: NNN, height: NNN }, deviceScaleFactor: 1 });
  await pg.goto('file://' + process.argv[2]);
  await pg.screenshot({ path: process.argv[3], omitBackground: true });
  await b.close();
})();
"""

if __name__ == "__main__":
    os.makedirs(OUTDIR, exist_ok=True)
    for size in (256, 1024):
        svg = build_svg(size)
        p = os.path.join(OUTDIR, f"indep-{size}.svg")
        with open(p, "w") as fh:
            fh.write(svg)
        with open(os.path.join(OUTDIR, "shot.js"), "w") as fh:
            fh.write(JS.replace("NNN", str(size)))
        print("wrote", p)
