#!/usr/bin/env node
/**
 * Generate the macOS App icon and the DMG volume icon from the personal brand mark.
 *
 * Source of truth: `assets/branding/logo-mark.svg` (3 rings) and
 * `assets/branding/favicon.svg` (2 rings), both byte-for-byte copies of the
 * personal brand library. The symbol is never redrawn here; the brand file's
 * inner markup is reused verbatim and only recoloured through a <style> block
 * and placed on the Apple macOS icon grid (824x824 plate, rx 185.4).
 *
 * Output:
 *   native/Resources/AppIcon.icns
 *   native/Resources/VolumeIcon.icns   (byte-identical copy)
 *
 * Renderer: Playwright, resolved from this repository's `web/node_modules`.
 * Browsers are NOT a build dependency: the `.icns` files are committed and the
 * packaging build only copies them. This script is a maintainer tool.
 *
 * Usage:
 *   node assets/branding/make-appicon.mjs                       # faithful, render + self-check
 *   node assets/branding/make-appicon.mjs --profile legible     # alternative treatment
 *   node assets/branding/make-appicon.mjs --check               # verify committed .icns, no Playwright
 *   node assets/branding/make-appicon.mjs --check-only          # alias of --check
 *
 * One PNG is rendered per *distinct* pixel size and then copied to every iconset
 * name that needs that size, so a size never goes through two rendering paths.
 *
 * See assets/branding/README.md for the profile rationale and provenance.
 */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const RESOURCES_DIR = path.join(ROOT, "native", "Resources");
const APP_ICON_PATH = path.join(RESOURCES_DIR, "AppIcon.icns");
const VOLUME_ICON_PATH = path.join(RESOURCES_DIR, "VolumeIcon.icns");
const PREVIEW_ROOT = process.env.SUMMIT_APPICON_PREVIEW_DIR || "/tmp/appicon-preview";
const DEFAULT_PROFILE = "faithful";

/** The only permitted colours: the `.deep-mode` block of the brand variables.css. */
const TOKENS = {
  plate: "#1C2124", // --color-paper        (deep)
  primary: "#8FA0A4", // --color-primary     (deep)  outer / middle rings
  primaryDeep: "#B4C0C3", // --color-primary-deep (deep) innermost, heaviest ring
  ink: "#F4F3F0", // --color-ink            (deep)  summit square
};

/**
 * Size -> treatment profiles. `cover` is the symbol width as a fraction of the
 * 824pt plate; the symbol is centred. `minStroke` is a minimum *physical* pixel
 * width enforced at that icon size (0 = leave the brand's own stroke alone).
 */
const PROFILES = {
  // Default, chosen by the user on 2026-10-16. >=64px is pixel-identical to the
  // brand original; 16/32px get a 0.90px floor so the mark survives.
  faithful: {
    description: "Selected 2026-10-16. Faithful to the brand strokes; 0.90px floor at 16/32px.",
    rules: [
      ["small@<=32", { variant: "small", box: 67, cover: 0.7779, minStroke: 0.9 }],
      ["full@>=64", { variant: "full", box: 100, cover: 0.6796, minStroke: 0 }],
    ],
  },
  // Alternative A: fully faithful, no floor at all. At 16px the mark is
  // effectively invisible (measured: only 5 brand-colour pixels).
  strict: {
    description: "Fully faithful, no minimum stroke. 16px renders ~5 brand pixels (near invisible).",
    rules: [
      ["small@<=32", { variant: "small", box: 67, cover: 0.7779, minStroke: 0 }],
      ["full@>=64", { variant: "full", box: 100, cover: 0.6796, minStroke: 0 }],
    ],
  },
  // Alternative B: the earlier T2 proposal, bolder at every size. Not selected.
  legible: {
    description: "Earlier T2 proposal: bolder strokes at every size. Not selected.",
    rules: [
      ["small@<=32", { variant: "small", box: 67, cover: 0.72, minStroke: 1.25 }],
      ["small@<=64", { variant: "small", box: 67, cover: 0.66, minStroke: 1.0 }],
      ["full@<=128", { variant: "full", box: 100, cover: 0.62, minStroke: 0.85 }],
      ["full@>=256", { variant: "full", box: 100, cover: 0.58, minStroke: 0 }],
    ],
  },
};

/** iconutil requires this exact set of names, with these pixel dimensions. */
const ICONSET_ENTRIES = [
  ["icon_16x16.png", 16],
  ["icon_16x16@2x.png", 32],
  ["icon_32x32.png", 32],
  ["icon_32x32@2x.png", 64],
  ["icon_128x128.png", 128],
  ["icon_128x128@2x.png", 256],
  ["icon_256x256.png", 256],
  ["icon_256x256@2x.png", 512],
  ["icon_512x512.png", 512],
  ["icon_512x512@2x.png", 1024],
];
const ICON_SIZES = [...new Set(ICONSET_ENTRIES.map(([, size]) => size))];

/** One canonical file per pixel size, used when re-checking a committed .icns. */
const CANONICAL_BY_SIZE = new Map([
  [16, "icon_16x16.png"],
  [32, "icon_32x32.png"],
  [64, "icon_32x32@2x.png"],
  [128, "icon_128x128.png"],
  [256, "icon_256x256.png"],
  [512, "icon_512x512.png"],
  [1024, "icon_512x512@2x.png"],
]);

/** icns block type -> pixel size, for the ten standard representations. */
const ICNS_BLOCK_SIZES = {
  ic04: 16,
  ic11: 32,
  ic05: 32,
  ic12: 64,
  ic07: 128,
  ic13: 256,
  ic08: 256,
  ic14: 512,
  ic09: 512,
  ic10: 1024,
};

/** Every representation block the committed `.icns` must contain. */
const EXPECTED_ICNS_BLOCKS = Object.keys(ICNS_BLOCK_SIZES);

/**
 * Pixel size -> the iconset file names that must carry that exact image.
 *
 * The renderer produces one PNG per distinct pixel size; every name returned
 * here is a byte-for-byte copy of it, so a size is rendered once and never
 * through a second compositing path.
 */
function sharedSizeGroups() {
  const groups = new Map();
  for (const [fileName, size] of ICONSET_ENTRIES) {
    const names = groups.get(size) ?? [];
    names.push(fileName);
    groups.set(size, names);
  }
  return [...groups.entries()]
    .filter(([, names]) => names.length > 1)
    .map(([size, names]) => ({ size, names }));
}

/**
 * Lower bounds for the brand-colour pixel count, ~80% of the measured values
 * (see README). Guard rails against a silently blank or over-thin render.
 */
const INK_FLOORS = {
  faithful: { 16: 17, 32: 41, 64: 34, 128: 330, 256: 1520, 512: 6390, 1024: 26130 },
  strict: { 16: 4, 32: 32, 64: 34, 128: 330, 256: 1520, 512: 6390, 1024: 26130 },
  legible: { 16: 25, 32: 55, 64: 140, 128: 260, 256: 1000, 512: 4500, 1024: 18000 },
};

/** Chebyshev (max-channel) distance used to decide "this pixel is brand colour". */
const COLOUR_TOLERANCE = 40;

/**
 * A pixel counts as brand ink only when it is opaque enough to be seen: the
 * measured counts in README §5 use `alpha > 140`. The looser `alpha > 0` reading
 * would count anti-aliased plate corners too (32px: 58 instead of 52).
 */
const INK_ALPHA_FLOOR = 140;

const PIXEL_CHECK_PY = `
import json
import sys

from PIL import Image

PLATE = (0x1C, 0x21, 0x24)
TOKENS = {
    "primary": (0x8F, 0xA0, 0xA4),
    "primaryDeep": (0xB4, 0xC0, 0xC3),
    "ink": (0xF4, 0xF3, 0xF0),
}
TOLERANCE = ${COLOUR_TOLERANCE}


def near(color, target):
    return max(abs(a - b) for a, b in zip(color, target)) <= TOLERANCE


def stats(path):
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    pixels = list(image.getdata())
    corners = [
        pixels[0],
        pixels[width - 1],
        pixels[(height - 1) * width],
        pixels[width * height - 1],
    ]
    ink = 0
    plate = False
    present = {name: False for name in TOKENS}
    for pixel in pixels:
        if pixel[3] <= ${INK_ALPHA_FLOOR}:
            continue
        rgb = pixel[:3]
        if not plate and near(rgb, PLATE):
            plate = True
        # Presence is tracked per colour independently: the two ring colours are
        # only 37 apart in Chebyshev distance, so a tolerance of ${COLOUR_TOLERANCE}
        # deliberately lets a pixel satisfy both. Each pixel still counts once.
        matched = False
        for name, target in TOKENS.items():
            if near(rgb, target):
                present[name] = True
                matched = True
        if matched:
            ink += 1
    return {
        "size": width,
        "ink": ink,
        "corners_transparent": all(corner[3] == 0 for corner in corners),
        "plate": plate,
        "tokens": present,
    }


print(json.dumps([stats(p) for p in sys.argv[1:]]))
`;

/**
 * Decode the committed .icns and the iconset iconutil extracted from it.
 *
 * Two facts have to be separable to judge "same pixel size, one render":
 *  1. inside the container the shared-size representations must hold identical
 *     pixels (iconutil stores 16px/32px 1x as `ARGB` RLE and the rest as PNG);
 *  2. `iconutil -c iconset` is not byte-faithful for the `ARGB` blocks — it
 *     unpremultiplies payloads that it wrote unpremultiplied. That rewrite is
 *     reported, and it must be the *only* difference left after extraction.
 */
const ICNS_AUDIT_PY = `
import hashlib
import io
import json
import struct
import sys

from PIL import Image

PNG_MAGIC = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
BLOCK_SIZES = {
    "ic04": 16, "ic11": 32, "ic05": 32, "ic12": 64, "ic07": 128,
    "ic13": 256, "ic08": 256, "ic14": 512, "ic09": 512, "ic10": 1024,
}
SHARED = {
    32: ["icon_16x16@2x.png", "icon_32x32.png"],
    256: ["icon_128x128@2x.png", "icon_256x256.png"],
    512: ["icon_256x256@2x.png", "icon_512x512.png"],
}
CANONICAL = {
    16: "icon_16x16.png", 32: "icon_32x32.png", 64: "icon_32x32@2x.png",
    128: "icon_128x128.png", 256: "icon_256x256.png", 512: "icon_512x512.png",
    1024: "icon_512x512@2x.png",
}
NAME_BLOCK = {
    "icon_16x16.png": "ic04", "icon_16x16@2x.png": "ic11", "icon_32x32.png": "ic05",
    "icon_32x32@2x.png": "ic12", "icon_128x128.png": "ic07", "icon_128x128@2x.png": "ic13",
    "icon_256x256.png": "ic08", "icon_256x256@2x.png": "ic14", "icon_512x512.png": "ic09",
    "icon_512x512@2x.png": "ic10",
}


def unpack_rle(body, count):
    out = bytearray()
    index = 0
    while len(out) < count:
        control = body[index]
        index += 1
        if control >= 0x80:
            run = control - 125
            value = body[index]
            index += 1
            out.extend(bytes([value]) * run)
        else:
            run = control + 1
            out.extend(body[index:index + run])
            index += run
    return bytes(out[:count])


def decode_argb(payload, size):
    count = size * size
    planes = []
    body = payload[4:]
    position = 0
    for _ in range(4):
        plane = bytearray()
        while len(plane) < count:
            control = body[position]
            position += 1
            if control >= 0x80:
                run = control - 125
                value = body[position]
                position += 1
                plane.extend(bytes([value]) * run)
            else:
                run = control + 1
                plane.extend(body[position:position + run])
                position += run
        planes.append(bytes(plane[:count]))
    alpha, red, green, blue = planes
    return [(red[i], green[i], blue[i], alpha[i]) for i in range(count)]


def decode(payload, size):
    if payload[:8] == PNG_MAGIC:
        return list(Image.open(io.BytesIO(payload)).convert("RGBA").getdata())
    if payload[:4] == b"ARGB":
        return decode_argb(payload, size)
    return None


def unpremultiply(pixels):
    """What iconutil -c iconset does to an ARGB payload it wrote unpremultiplied."""
    out = []
    for red, green, blue, alpha in pixels:
        if alpha == 0:
            out.append((0, 0, 0, 0) if (red, green, blue) == (0, 0, 0) else (255, 255, 255, 0))
            continue
        out.append(tuple(min(255, (channel * 255 + alpha // 2) // alpha) for channel in (red, green, blue)) + (alpha,))
    return out


def delta(first, second):
    return max(abs(a - b) for a, b in zip(first[:3], second[:3]))


def read(path):
    with open(path, "rb") as stream:
        return stream.read()


def main():
    icns_path, iconset = sys.argv[1], sys.argv[2]
    data = read(icns_path)
    blocks = []
    offset = 8
    while offset < len(data):
        block_type = data[offset:offset + 4].decode("latin-1")
        length = struct.unpack(">I", data[offset + 4:offset + 8])[0]
        payload = data[offset + 8:offset + length]
        kind = "PNG" if payload[:8] == PNG_MAGIC else ("ARGB" if payload[:4] == b"ARGB" else "other")
        blocks.append((block_type, payload, kind))
        offset += length

    report = {
        "blocks": [{"type": t, "length": len(p) + 8, "kind": k} for t, p, k in blocks],
        "shared": [],
        "pairs": [],
        "extracted": {},
    }

    by_size = {}
    for block_type, payload, _kind in blocks:
        size = BLOCK_SIZES.get(block_type)
        if size is not None:
            by_size.setdefault(size, []).append((block_type, decode(payload, size)))
    for size in sorted(by_size):
        entries = by_size[size]
        if len(entries) < 2:
            continue
        reference = entries[0][1]
        differing = 0
        worst = 0
        alpha_equal = True
        for _name, pixels in entries[1:]:
            for first, second in zip(reference, pixels):
                if first[3] != second[3]:
                    alpha_equal = False
                if first != second:
                    differing += 1
                    worst = max(worst, delta(first, second))
        report["shared"].append({
            "size": size,
            "blocks": [name for name, _pixels in entries],
            "pixel_diff": differing,
            "max_rgb_delta": worst,
            "alpha_equal": alpha_equal,
        })

    for size in sorted(set(SHARED) | set(CANONICAL)):
        name = CANONICAL[size]
        raw = read(iconset + "/" + name)
        pixels = list(Image.open(io.BytesIO(raw)).convert("RGBA").getdata())
        report["extracted"][name] = {
            "size": size,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "whitish_semitransparent": sum(
                1 for p in pixels if 0 < p[3] < 255 and p[0] > 200 and p[1] > 200 and p[2] > 200
            ),
        }

    for size, names in SHARED.items():
        raw = [read(iconset + "/" + name) for name in names]
        pixels = [list(Image.open(io.BytesIO(item)).convert("RGBA").getdata()) for item in raw]
        decoded = {
            block_type: decode(payload, size)
            for block_type, payload, _kind in blocks
            if BLOCK_SIZES.get(block_type) == size
        }
        origins = {}
        for name, values in zip(names, pixels):
            reference = decoded.get(NAME_BLOCK[name])
            if reference is None:
                origins[name] = None
            elif values == reference:
                origins[name] = NAME_BLOCK[name] + ":exact"
            elif values == unpremultiply(reference):
                origins[name] = NAME_BLOCK[name] + ":unpremultiplied"
            else:
                origins[name] = None
        report["pairs"].append({
            "size": size,
            "names": names,
            "bytes_equal": raw[0] == raw[1],
            "alpha_equal": all(a[3] == b[3] for a, b in zip(pixels[0], pixels[1])),
            "rgb_diff_pixels": sum(1 for a, b in zip(pixels[0], pixels[1]) if a != b),
            "max_rgb_delta": max([delta(a, b) for a, b in zip(pixels[0], pixels[1])] + [0]),
            "against_container": origins,
        })

    print(json.dumps(report))


main()
`;

function fail(message) {
  process.stderr.write(`make-appicon: ${message}\n`);
  process.exit(1);
}

/**
 * Assert that every iconset name sharing a pixel size holds `cmp`-identical bytes.
 *
 * This is the assertion behind "one render per pixel size": the iconset handed
 * to `iconutil` must contain a single image per size, duplicated by name.
 */
function assertSharedSizesByteIdentical(directory, label) {
  const problems = [];
  const rows = [];
  for (const { size, names } of sharedSizeGroups()) {
    const reference = fs.readFileSync(path.join(directory, names[0]));
    for (const name of names.slice(1)) {
      const candidate = fs.readFileSync(path.join(directory, name));
      if (!reference.equals(candidate)) {
        problems.push(`${size}px: ${names[0]} and ${name} are not byte-identical`);
      }
    }
    rows.push(
      `  ${String(size).padStart(4)}px  ${names.join(" == ")}` +
        `  (${reference.length} bytes each)  cmp OK`,
    );
  }
  process.stdout.write(`${label}: one byte-identical image per pixel size\n${rows.join("\n")}\n`);
  if (problems.length > 0) {
    fail(`shared pixel sizes are not byte-identical:\n  - ${problems.join("\n  - ")}`);
  }
}

/**
 * Parse and validate an `.icns` block table (the same rules as
 * `scripts/build_macos_app.py`): the declared total length must equal the real
 * file size, every block must declare at least 8 bytes and stay inside the file,
 * and the blocks must tile the file exactly.
 */
function parseIcns(data, label) {
  if (data.length < 8) fail(`${label}: shorter than the 8-byte icns header`);
  if (data.subarray(0, 4).toString("latin1") !== "icns") fail(`${label}: bad icns magic`);
  const declared = data.readUInt32BE(4);
  if (declared !== data.length) {
    fail(`${label}: header length ${declared} != file size ${data.length}`);
  }
  const blocks = [];
  let offset = 8;
  while (offset < data.length) {
    if (offset + 8 > data.length) fail(`${label}: truncated block header at offset ${offset}`);
    const type = data.subarray(offset, offset + 4).toString("latin1");
    const length = data.readUInt32BE(offset + 4);
    if (length < 8) fail(`${label}: block ${type} declares ${length} bytes (< 8)`);
    if (offset + length > data.length) {
      fail(`${label}: block ${type} at offset ${offset} overruns the file`);
    }
    blocks.push({ type, length, offset });
    offset += length;
  }
  if (blocks.length === 0) fail(`${label}: no icon blocks`);
  return blocks;
}

/** Resolve Playwright from the repository's own web/node_modules. */
function loadChromium() {
  const requireFromWeb = createRequire(path.join(ROOT, "web", "package.json"));
  try {
    return requireFromWeb("playwright").chromium;
  } catch (error) {
    fail(
      "Playwright is required to (re)render icons but was not found in web/node_modules. " +
        `Run \`npm --prefix web ci\` first, or use --check-only to validate the committed .icns. (${error.message})`,
    );
  }
}

/** Run an inline Python helper (Pillow is available in it) and return its stdout. */
function runPython(python, source, args) {
  const scriptPath = path.join(
    fs.mkdtempSync(path.join(os.tmpdir(), "appicon-python-")),
    "helper.py",
  );
  fs.writeFileSync(scriptPath, source, "utf8");
  return execFileSync(python.command, [...python.prefix, scriptPath, ...args], {
    encoding: "utf8",
  });
}

function readBrandMark(fileName) {
  const source = fs.readFileSync(path.join(HERE, fileName), "utf8");
  const open = source.indexOf(">");
  const close = source.lastIndexOf("</svg>");
  if (open === -1 || close === -1) {
    fail(`${fileName} does not look like an SVG document`);
  }
  return source.slice(open + 1, close);
}

const MARKS = {
  full: { inner: readBrandMark("logo-mark.svg"), box: 100, height: 84 },
  small: { inner: readBrandMark("favicon.svg"), box: 67, height: 67 },
};

/** Resolve the rule that applies to a pixel size within a profile. */
function ruleFor(profile, size) {
  const rules = PROFILES[profile].rules;
  for (const [selector, rule] of rules) {
    const match = /^(small|full)@(<=|>=)(\d+)$/.exec(selector);
    if (!match) {
      fail(`profile ${profile} has an unparsable selector: ${selector}`);
    }
    const threshold = Number(match[3]);
    if ((match[2] === "<=" && size <= threshold) || (match[2] === ">=" && size >= threshold)) {
      return rule;
    }
  }
  // Only reachable for sizes between configured buckets (e.g. 48px), which the
  // iconset never requests. Fall back to the rule for the largest sizes.
  return rules[rules.length - 1][1];
}

/**
 * Compose the 1024-unit canvas for one icon size.
 *
 * `scale` maps the brand viewBox onto the plate; the minimum-stroke rule then
 * compares a stroke's *physical* pixel width at this icon size against the
 * profile floor and scales only that stroke up.
 */
function compose(profile, size) {
  const rule = ruleFor(profile, size);
  const mark = MARKS[rule.variant];
  const plate = 824;
  const markWidth = plate * rule.cover;
  const scale = markWidth / rule.box;

  const inner = mark.inner.replace(/stroke-width="([\d.]+)"/g, (_all, raw) => {
    const units = Number.parseFloat(raw);
    const physical = units * scale * (size / 1024);
    const factor = rule.minStroke > 0 && physical < rule.minStroke ? rule.minStroke / physical : 1;
    return `stroke-width="${(units * factor).toFixed(2)}"`;
  });

  const markHeight = markWidth * (mark.height / rule.box);
  const tx = (1024 - markWidth) / 2;
  const ty = (1024 - markHeight) / 2;

  const style =
    rule.variant === "full"
      ? `g path:nth-of-type(1),g path:nth-of-type(2){stroke:${TOKENS.primary}}` +
        `g path:nth-of-type(3){stroke:${TOKENS.primaryDeep}}` +
        `g rect{fill:${TOKENS.ink}}`
      : `g path:nth-of-type(1){stroke:${TOKENS.primary}}` +
        `g path:nth-of-type(2){stroke:${TOKENS.primaryDeep}}` +
        `g rect{fill:${TOKENS.ink}}`;

  return (
    `<svg width="${size}" height="${size}" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">` +
    `<style>${style}</style>` +
    `<rect x="100" y="100" width="824" height="824" rx="185.4" fill="${TOKENS.plate}"/>` +
    `<g transform="translate(${tx.toFixed(2)},${ty.toFixed(2)}) scale(${scale.toFixed(3)})">${inner}</g>` +
    `</svg>`
  );
}

/**
 * Render one PNG per *distinct* pixel size, on a transparent background.
 *
 * `ICON_SIZES` is a set, so 32px is rendered exactly once and then copied (by
 * `makeIconset`) to both `icon_16x16@2x.png` and `icon_32x32.png`. `omitBackground`
 * plus `background:transparent` is what keeps the anti-aliased plate corners
 * free of composited white.
 */
async function renderProfile(chromium, profile, outDir) {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  try {
    for (const size of ICON_SIZES) {
      const page = await browser.newPage({
        viewport: { width: size, height: size },
        deviceScaleFactor: 1,
      });
      await page.setContent(
        `<html><body style="margin:0;background:transparent">` +
          `<div style="width:${size}px;height:${size}px">${compose(profile, size)}</div>` +
          `</body></html>`,
      );
      await page.screenshot({ path: path.join(outDir, `icon-${size}.png`), omitBackground: true });
      await page.close();
    }
  } finally {
    await browser.close();
  }
}

/** Find an interpreter that can import Pillow (system python3 first). */
function resolvePython() {
  const candidates = [
    ["python3", []],
    ["uv", ["run", "--group", "dev", "python"]],
  ];
  for (const [command, prefix] of candidates) {
    try {
      execFileSync(command, [...prefix, "-c", "import PIL"], { stdio: "ignore" });
      return { command, prefix };
    } catch {
      /* try the next candidate */
    }
  }
  fail(
    "Pillow is required for the pixel self-check but no interpreter with it was found. " +
      "System python3 normally provides it; otherwise `pip install pillow`.",
  );
}

/** Run the Pillow pixel statistics over the given PNG paths. */
function readPixelStats(python, paths) {
  return JSON.parse(runPython(python, PIXEL_CHECK_PY, paths));
}

/** Decode the committed .icns and the iconset iconutil extracted from it. */
function auditIcns(python, icnsPath, iconsetDir) {
  return JSON.parse(runPython(python, ICNS_AUDIT_PY, [icnsPath, iconsetDir]));
}

/**
 * Assert the rendered (or extracted) PNGs: transparent corners, the plate and
 * brand colours present, and enough brand-colour pixels for the profile.
 */
function assertStats(profile, stats, label) {
  const floors = INK_FLOORS[profile];
  const problems = [];
  const rows = [];

  for (const entry of stats) {
    const size = entry.size;
    const floor = floors[size];
    const marks = Object.entries(entry.tokens)
      .filter(([, present]) => present)
      .map(([name]) => name);
    rows.push(
      `  ${String(size).padStart(4)}px  brand-pixels=${String(entry.ink).padStart(6)}  ` +
        `floor=${String(floor).padStart(6)}  colours=[${marks.join(", ") || "none"}]`,
    );

    if (floor === undefined) problems.push(`${size}px is not a configured icon size`);
    if (!entry.corners_transparent) problems.push(`${size}px: a corner is not transparent`);
    if (!entry.plate) problems.push(`${size}px: the plate colour ${TOKENS.plate} is missing`);
    if (!entry.tokens.primary) problems.push(`${size}px: the primary ring colour is missing`);

    // All four colours must survive from 32px up. At 16px the innermost ring can
    // be physically impossible to form (e.g. profile `strict`), so require the
    // plate plus at least two brand colours there instead.
    if (size >= 32) {
      for (const name of ["primary", "primaryDeep", "ink"]) {
        if (!entry.tokens[name]) problems.push(`${size}px: brand colour ${name} is missing`);
      }
    } else if (marks.length < 2) {
      problems.push(`16px: expected at least 2 brand colours, found ${marks.length}`);
    }

    if (floor !== undefined && entry.ink < floor) {
      problems.push(`${size}px: brand pixels ${entry.ink} < floor ${floor}`);
    }
  }

  process.stdout.write(`${label} (profile ${profile})\n${rows.join("\n")}\n`);
  if (problems.length > 0) {
    fail(`self-check failed:\n  - ${problems.join("\n  - ")}`);
  }
  process.stdout.write("self-check OK\n");
}

function makeIconset(profileDir, iconsetPath) {
  fs.rmSync(iconsetPath, { recursive: true, force: true });
  fs.mkdirSync(iconsetPath, { recursive: true });
  // One rendered PNG per distinct pixel size, copied to every name that needs
  // it: 16 -> 1 name; 32 -> icon_16x16@2x.png + icon_32x32.png; 64 -> 1;
  // 128 -> 1; 256 -> icon_128x128@2x.png + icon_256x256.png; 512 ->
  // icon_256x256@2x.png + icon_512x512.png; 1024 -> icon_512x512@2x.png.
  for (const [fileName, size] of ICONSET_ENTRIES) {
    fs.copyFileSync(path.join(profileDir, `icon-${size}.png`), path.join(iconsetPath, fileName));
  }
  assertSharedSizesByteIdentical(iconsetPath, "iconset about to be packed");
}

function buildIcns(python, profile) {
  const previewDir = path.join(PREVIEW_ROOT, profile);
  const work = fs.mkdtempSync(path.join(os.tmpdir(), "appicon-icns-"));
  try {
    const iconset = path.join(work, "AppIcon.iconset");
    makeIconset(previewDir, iconset);
    fs.mkdirSync(RESOURCES_DIR, { recursive: true });
    execFileSync("iconutil", ["-c", "icns", iconset, "-o", APP_ICON_PATH], { stdio: "inherit" });
    fs.copyFileSync(APP_ICON_PATH, VOLUME_ICON_PATH);
  } finally {
    fs.rmSync(work, { recursive: true, force: true });
  }
  const appBytes = fs.statSync(APP_ICON_PATH).size;
  process.stdout.write(
    `wrote ${path.relative(ROOT, APP_ICON_PATH)} and ${path.relative(ROOT, VOLUME_ICON_PATH)} ` +
      `(${appBytes} bytes each)\n`,
  );
}

/**
 * Validate already-committed .icns files without Playwright or re-rendering.
 *
 * Checks, in order: the block table parses and holds the ten expected
 * representations; both committed files are byte-identical; the container's
 * shared-size representations carry identical pixels; the iconset handed to
 * `iconutil` is one byte-identical image per size; the pixel floors hold; and
 * any difference `iconutil -c iconset` introduces is accounted for.
 */
function checkOnly(python, profile) {
  for (const icns of [APP_ICON_PATH, VOLUME_ICON_PATH]) {
    if (!fs.existsSync(icns)) fail(`missing committed icon: ${path.relative(ROOT, icns)}`);
  }
  const appLabel = path.relative(ROOT, APP_ICON_PATH);
  const appBytes = fs.readFileSync(APP_ICON_PATH);
  const volumeBytes = fs.readFileSync(VOLUME_ICON_PATH);
  const blocks = parseIcns(appBytes, appLabel);
  const types = blocks.map((block) => block.type);
  const missing = EXPECTED_ICNS_BLOCKS.filter((type) => !types.includes(type));
  if (missing.length > 0) fail(`${appLabel}: missing blocks ${missing.join(", ")}`);
  const unexpected = types.filter((type) => type !== "info" && !EXPECTED_ICNS_BLOCKS.includes(type));
  if (unexpected.length > 0) fail(`${appLabel}: unexpected blocks ${unexpected.join(", ")}`);
  if (!appBytes.equals(volumeBytes)) {
    fail("AppIcon.icns and VolumeIcon.icns are not byte-identical");
  }
  process.stdout.write(
    `committed .icns: ${types.join(", ")} (${appBytes.length} bytes); ` +
      "AppIcon.icns == VolumeIcon.icns by cmp\n",
  );

  const work = fs.mkdtempSync(path.join(os.tmpdir(), "appicon-extract-"));
  try {
    const iconset = path.join(work, "AppIcon.iconset");
    execFileSync("iconutil", ["-c", "iconset", APP_ICON_PATH, "-o", iconset]);
    const extractedNames = fs.readdirSync(iconset).sort();
    const expectedNames = ICONSET_ENTRIES.map(([fileName]) => fileName).sort();
    if (extractedNames.join("\n") !== expectedNames.join("\n")) {
      fail(
        `iconutil extracted ${extractedNames.length} representations ` +
          `(${extractedNames.join(", ")}) instead of ${expectedNames.length}`,
      );
    }

    // The iconset that would be handed to iconutil, rebuilt from one canonical
    // file per pixel size, then compared with `cmp`.
    const input = path.join(work, `${profile}.iconset`);
    fs.mkdirSync(input, { recursive: true });
    const stats = [];
    // Ascending size, so assertStats reports them in a predictable order.
    for (const size of [...CANONICAL_BY_SIZE.keys()].sort((a, b) => a - b)) {
      const canonical = path.join(iconset, CANONICAL_BY_SIZE.get(size));
      if (!fs.existsSync(canonical)) fail(`AppIcon.icns has no ${CANONICAL_BY_SIZE.get(size)}`);
      fs.copyFileSync(canonical, path.join(input, CANONICAL_BY_SIZE.get(size)));
      stats.push(...readPixelStats(python, [canonical]));
    }
    for (const [fileName, size] of ICONSET_ENTRIES) {
      fs.copyFileSync(path.join(input, CANONICAL_BY_SIZE.get(size)), path.join(input, fileName));
    }
    assertSharedSizesByteIdentical(input, "iconset input (what iconutil receives)");

    assertStats(profile, stats, "committed AppIcon.icns");

    const audit = auditIcns(python, APP_ICON_PATH, iconset);
    for (const entry of audit.shared) {
      const detail = `${String(entry.size).padStart(4)}px  ${entry.blocks.join(", ")}`;
      if (entry.pixel_diff !== 0 || !entry.alpha_equal) {
        fail(
          `container ${detail}: shared-size representations differ ` +
            `(${entry.pixel_diff} px, max Δrgb ${entry.max_rgb_delta})`,
        );
      }
      process.stdout.write(`  container ${detail}: identical pixels inside the .icns\n`);
    }

    const whites = Object.entries(audit.extracted)
      .filter(([, info]) => info.whitish_semitransparent > 0)
      .map(([name, info]) => `${name}=${info.whitish_semitransparent}`);
    process.stdout.write(
      "  whitish semi-transparent pixels in the extracted reps: " +
        `${whites.length > 0 ? whites.join(", ") : "none"}\n`,
    );

    const diverging = audit.pairs.filter((pair) => !pair.bytes_equal);
    if (diverging.length === 0) {
      process.stdout.write("  extracted iconset pairs are byte-identical by cmp\n");
    } else {
      process.stdout.write(
        "  NOTE: `iconutil -c iconset` rewrites these shared-size pairs, so their bytes\n" +
          "  differ even though the iconset handed to iconutil was byte-identical and the\n" +
          "  .icns itself stores identical pixels. iconutil writes the 16px/32px 1x blocks as\n" +
          "  `ARGB` RLE (unpremultiplied) and unpremultiplies them again when extracting.\n",
      );
      for (const pair of diverging) {
        const origins = Object.entries(pair.against_container)
          .map(([name, origin]) => `${name}=${origin ?? "UNEXPLAINED"}`)
          .join(", ");
        process.stdout.write(
          `    ${String(pair.size).padStart(4)}px  ${pair.names.join(" vs ")}: ` +
            `${pair.rgb_diff_pixels} px differ, max Δrgb ${pair.max_rgb_delta}, ` +
            `alpha identical=${pair.alpha_equal} [${origins}]\n`,
        );
        const unexplained = Object.values(pair.against_container).some(
          (origin) => origin === null,
        );
        if (!pair.alpha_equal || unexplained) {
          fail(
            `${pair.size}px extraction divergence is not explained by iconutil's ARGB ` +
              `handling: ${JSON.stringify(pair.against_container)}`,
          );
        }
      }
    }
  } finally {
    fs.rmSync(work, { recursive: true, force: true });
  }
}

async function main() {
  const argv = process.argv.slice(2);
  if (argv.includes("--help") || argv.includes("-h")) {
    process.stdout.write(
      "usage: node assets/branding/make-appicon.mjs " +
        "[--profile strict|faithful|legible] [--check] [--check-only]\n",
    );
    return 0;
  }
  let profile = DEFAULT_PROFILE;
  const profileIndex = argv.indexOf("--profile");
  if (profileIndex !== -1) {
    profile = argv[profileIndex + 1];
  }
  if (!Object.hasOwn(PROFILES, profile)) {
    fail(`unknown profile ${profile}; expected one of ${Object.keys(PROFILES).join(", ")}`);
  }

  const python = resolvePython();

  // `--check` and `--check-only` are the same offline verification: they parse
  // the committed .icns, re-extract it with iconutil, assert the shared pixel
  // sizes are one byte-identical image, and re-run the pixel floors. No render.
  if (argv.includes("--check") || argv.includes("--check-only")) {
    checkOnly(python, profile);
    return 0;
  }

  const chromium = loadChromium();
  // Render every profile's previews for side-by-side review; only the selected
  // profile is packaged into the committed .icns.
  for (const name of Object.keys(PROFILES)) {
    const dir = path.join(PREVIEW_ROOT, name);
    await renderProfile(chromium, name, dir);
    process.stdout.write(`previews: ${dir}/icon-<size>.png\n`);
  }

  assertStats(
    profile,
    readPixelStats(
      python,
      ICON_SIZES.map((size) => path.join(PREVIEW_ROOT, profile, `icon-${size}.png`)),
    ),
    "rendered previews",
  );
  buildIcns(python, profile);
  return 0;
}

main().then(
  (code) => process.exit(code ?? 0),
  (error) => {
    process.stderr.write(`make-appicon: ${error?.stack || error}\n`);
    process.exit(1);
  },
);
