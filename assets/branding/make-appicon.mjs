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
 *   node assets/branding/make-appicon.mjs --check-only          # verify committed .icns, no Playwright
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
        if pixel[3] == 0:
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

function fail(message) {
  process.stderr.write(`make-appicon: ${message}\n`);
  process.exit(1);
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

/** Render one PNG per icon size, transparent background, for a profile. */
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
  const scriptPath = path.join(
    fs.mkdtempSync(path.join(os.tmpdir(), "appicon-pixels-")),
    "pixel_check.py",
  );
  fs.writeFileSync(scriptPath, PIXEL_CHECK_PY, "utf8");
  const raw = execFileSync(python.command, [...python.prefix, scriptPath, ...paths], {
    encoding: "utf8",
  });
  return JSON.parse(raw);
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
  for (const [fileName, size] of ICONSET_ENTRIES) {
    fs.copyFileSync(path.join(profileDir, `icon-${size}.png`), path.join(iconsetPath, fileName));
  }
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

/** Validate already-committed .icns files without Playwright or re-rendering. */
function checkOnly(python) {
  for (const icns of [APP_ICON_PATH, VOLUME_ICON_PATH]) {
    if (!fs.existsSync(icns)) fail(`missing committed icon: ${path.relative(ROOT, icns)}`);
  }
  const extracted = fs.mkdtempSync(path.join(os.tmpdir(), "appicon-extract-"));
  try {
    const iconset = path.join(extracted, "AppIcon.iconset");
    execFileSync("iconutil", ["-c", "iconset", APP_ICON_PATH, "-o", iconset], { stdio: "inherit" });
    const stats = [];
    // Ascending size, so assertStats reports them in a predictable order.
    for (const size of [...CANONICAL_BY_SIZE.keys()].sort((a, b) => a - b)) {
      const candidate = path.join(iconset, CANONICAL_BY_SIZE.get(size));
      if (!fs.existsSync(candidate)) fail(`AppIcon.icns has no ${CANONICAL_BY_SIZE.get(size)}`);
      stats.push(...readPixelStats(python, [candidate]));
    }
    assertStats(DEFAULT_PROFILE, stats, "committed AppIcon.icns");
  } finally {
    fs.rmSync(extracted, { recursive: true, force: true });
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

  if (argv.includes("--check-only")) {
    checkOnly(python);
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
