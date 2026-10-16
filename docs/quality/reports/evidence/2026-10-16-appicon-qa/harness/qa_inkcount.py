#!/usr/bin/env python3
"""Independent QA ink-pixel counter for the committed .icns iconset.

Definition (per QA brief C3): ink pixel = alpha > 140 AND Chebyshev distance
to one of #8FA0A4 / #B4C0C3 / #F4F3F0 <= 40.
Also reports the README's self-check definition (alpha > 0) for contrast.
Never imports the implementer's generator.
"""
import os
import sys

from PIL import Image

TOKENS = [(0x8F, 0xA0, 0xA4), (0xB4, 0xC0, 0xC3), (0xF4, 0xF3, 0xF0)]
ICONSET = sys.argv[1] if len(sys.argv) > 1 else ".local/qa/appicon/iconset/AppIcon.iconset"

FILES = [
    ("16", "icon_16x16.png"),
    ("16@2x=32", "icon_16x16@2x.png"),
    ("32", "icon_32x32.png"),
    ("32@2x=64", "icon_32x32@2x.png"),
    ("128", "icon_128x128.png"),
    ("128@2x=256", "icon_128x128@2x.png"),
    ("256", "icon_256x256.png"),
    ("256@2x=512", "icon_256x256@2x.png"),
    ("512", "icon_512x512.png"),
    ("512@2x=1024", "icon_512x512@2x.png"),
]


def cheb(c, t):
    return max(abs(c[0] - t[0]), abs(c[1] - t[1]), abs(c[2] - t[2]))


def analyse(path):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = im.load()
    ink_140 = 0
    ink_0 = 0
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    plate = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            c = (r, g, b)
            m = min(cheb(c, t) for t in TOKENS)
            if m <= 40:
                ink_0 += 1
                if a > 140:
                    ink_140 += 1
            if a > 140 and cheb(c, (0x1C, 0x21, 0x24)) <= 8:
                plate += 1
    return dict(size=(w, h), ink_gt140=ink_140, ink_gt0=ink_0,
                corners=[tuple(c) for c in corners], plate=plate)


if __name__ == "__main__":
    print(f"{'rep':<12}{'px':<10}{'ink(a>140)':<12}{'ink(a>0)':<10}"
          f"{'corners alpha':<18}{'plate#1C2124'}")
    for label, fn in FILES:
        p = os.path.join(ICONSET, fn)
        r = analyse(p)
        ca = [c[3] for c in r["corners"]]
        print(f"{label:<12}{str(r['size']):<10}{r['ink_gt140']:<12}{r['ink_gt0']:<10}"
              f"{str(ca):<18}{r['plate']}")
