"""Unit tests for embedding the committed macOS app icon into the app bundle."""

import importlib.util
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path
from types import ModuleType

import pytest

BUILD_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_macos_app.py"
REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ICON = REPO_ROOT / "native" / "Resources" / "AppIcon.icns"
VOLUME_ICON = REPO_ROOT / "native" / "Resources" / "VolumeIcon.icns"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# name -> pixel dimensions, as iconutil requires them.
ICONSET_ENTRIES = {
    "icon_16x16.png": (16, 16),
    "icon_16x16@2x.png": (32, 32),
    "icon_32x32.png": (32, 32),
    "icon_32x32@2x.png": (64, 64),
    "icon_128x128.png": (128, 128),
    "icon_128x128@2x.png": (256, 256),
    "icon_256x256.png": (256, 256),
    "icon_256x256@2x.png": (512, 512),
    "icon_512x512.png": (512, 512),
    "icon_512x512@2x.png": (1024, 1024),
}

# Pixel size -> the iconset names that must carry that exact image.
CANONICAL_BY_SIZE = {
    16: "icon_16x16.png",
    32: "icon_32x32.png",
    64: "icon_32x32@2x.png",
    128: "icon_128x128.png",
    256: "icon_256x256.png",
    512: "icon_512x512.png",
    1024: "icon_512x512@2x.png",
}
SHARED_SIZES = {
    32: ("icon_16x16@2x.png", "icon_32x32.png"),
    256: ("icon_128x128@2x.png", "icon_256x256.png"),
    512: ("icon_256x256@2x.png", "icon_512x512.png"),
}

# icns block type -> pixel size, for the ten standard representations.
BLOCK_SIZES = {
    b"ic04": 16,
    b"ic11": 32,
    b"ic05": 32,
    b"ic12": 64,
    b"ic07": 128,
    b"ic13": 256,
    b"ic08": 256,
    b"ic14": 512,
    b"ic09": 512,
    b"ic10": 1024,
}


def make_icns(blocks: list[tuple[bytes, bytes]]) -> bytes:
    """Build an icns container from ``(type, payload)`` blocks."""
    body = b"".join(
        block_type + struct.pack(">I", len(payload) + 8) + payload for block_type, payload in blocks
    )
    return b"icns" + struct.pack(">I", len(body) + 8) + body


# A container whose only block is the 8-byte block header and an empty payload.
VALID_MINIMAL_ICNS = make_icns([(b"ic04", b"")])

# Every input below has to fail closed: correct-ish magic is never enough.
DAMAGED_ICNS_INPUTS = {
    "empty": b"",
    "three-bytes": b"icn",
    "four-bytes-magic-only": b"icns",
    "seven-bytes": b"icns\x00\x00\x00",
    "png-header": PNG_MAGIC,
    "header-only-eight-bytes": b"icns\x00\x00\x00\x08",
    "declared-length-mismatch": (
        b"icns" + struct.pack(">I", 4096) + b"ic04" + struct.pack(">I", 8)
    ),
    "block-overruns-the-file": (
        b"icns" + struct.pack(">I", 16) + b"ic04" + struct.pack(">I", 4096)
    ),
    "block-length-below-eight": (b"icns" + struct.pack(">I", 16) + b"ic04" + struct.pack(">I", 4)),
    "truncated-block-header": b"icns" + struct.pack(">I", 12) + b"ic04",
}


def load_build_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_build_macos_app_icon_under_test", BUILD_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _unfilter(kind: int, line: bytearray, previous: bytes, bpp: int) -> None:
    for index in range(len(line)):
        left = line[index - bpp] if index >= bpp else 0
        up = previous[index]
        up_left = previous[index - bpp] if index >= bpp else 0
        if kind == 0:
            continue
        if kind == 1:
            line[index] = (line[index] + left) & 0xFF
        elif kind == 2:
            line[index] = (line[index] + up) & 0xFF
        elif kind == 3:
            line[index] = (line[index] + (left + up) // 2) & 0xFF
        elif kind == 4:
            estimate = left + up - up_left
            distances = (abs(estimate - left), abs(estimate - up), abs(estimate - up_left))
            predictor = (left, up, up_left)[distances.index(min(distances))]
            line[index] = (line[index] + predictor) & 0xFF
        else:
            raise AssertionError(f"unsupported PNG filter {kind}")


def png_pixels(data: bytes) -> list[tuple[int, int, int, int]]:
    """Decode an 8-bit RGBA, non-interlaced PNG with the standard library only."""
    assert data[:8] == PNG_MAGIC, "not a PNG"
    header = b""
    compressed = bytearray()
    offset = 8
    while offset + 8 <= len(data):
        length = int.from_bytes(data[offset : offset + 4], "big")
        chunk = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        if chunk == b"IHDR":
            header = payload
        elif chunk == b"IDAT":
            compressed += payload
        offset += 12 + length
    assert len(header) == 13, "missing IHDR"
    width = int.from_bytes(header[0:4], "big")
    height = int.from_bytes(header[4:8], "big")
    assert (header[8], header[9], header[12]) == (8, 6, 0), "expected 8-bit RGBA, non-interlaced"

    raw = zlib.decompress(bytes(compressed))
    stride = width * 4
    pixels: list[tuple[int, int, int, int]] = []
    previous = bytes(stride)
    position = 0
    for _ in range(height):
        kind = raw[position]
        position += 1
        line = bytearray(raw[position : position + stride])
        position += stride
        _unfilter(kind, line, previous, 4)
        previous = bytes(line)
        pixels.extend(tuple(line[index : index + 4]) for index in range(0, stride, 4))
    return pixels


def icns_blocks(path: Path) -> dict[bytes, bytes]:
    """Split a committed .icns into ``type -> payload`` (duplicate types keep the first)."""
    data = path.read_bytes()
    assert data[:4] == b"icns"
    assert int.from_bytes(data[4:8], "big") == len(data)
    blocks: dict[bytes, bytes] = {}
    offset = 8
    while offset < len(data):
        block_type = data[offset : offset + 4]
        length = int.from_bytes(data[offset + 4 : offset + 8], "big")
        assert length >= 8
        assert offset + length <= len(data)
        blocks.setdefault(block_type, data[offset + 8 : offset + length])
        offset += length
    assert offset == len(data)
    return blocks


def _unpack_rle(body: bytes, count: int) -> bytes:
    out = bytearray()
    index = 0
    while len(out) < count:
        control = body[index]
        index += 1
        if control >= 0x80:
            run = control - 125
            out.extend(bytes([body[index]]) * run)
            index += 1
        else:
            run = control + 1
            out.extend(body[index : index + run])
            index += run
    return bytes(out[:count])


def argb_pixels(payload: bytes, size: int) -> list[tuple[int, int, int, int]]:
    """Decode the ``ARGB`` RLE payload iconutil writes for the 16px/32px 1x blocks."""
    assert payload[:4] == b"ARGB"
    count = size * size
    planes = []
    position = 0
    body = payload[4:]
    for _ in range(4):
        plane = bytearray()
        while len(plane) < count:
            control = body[position]
            position += 1
            if control >= 0x80:
                run = control - 125
                plane.extend(bytes([body[position]]) * run)
                position += 1
            else:
                run = control + 1
                plane.extend(body[position : position + run])
                position += run
        planes.append(bytes(plane[:count]))
    alpha, red, green, blue = planes
    return [(red[i], green[i], blue[i], alpha[i]) for i in range(count)]


def block_pixels(blocks: dict[bytes, bytes], block_type: bytes) -> list[tuple[int, int, int, int]]:
    payload = blocks[block_type]
    if payload[:8] == PNG_MAGIC:
        return png_pixels(payload)
    return argb_pixels(payload, BLOCK_SIZES[block_type])


def unpremultiply(
    pixels: list[tuple[int, int, int, int]],
) -> list[tuple[int, int, int, int]]:
    """Model what ``iconutil -c iconset`` does to the ARGB payloads it wrote raw."""
    out = []
    for red, green, blue, alpha in pixels:
        if alpha == 0:
            out.append((0, 0, 0, 0) if (red, green, blue) == (0, 0, 0) else (255, 255, 255, 0))
            continue
        scaled = tuple(
            min(255, (channel * 255 + alpha // 2) // alpha) for channel in (red, green, blue)
        )
        out.append((*scaled, alpha))
    return out


@pytest.mark.parametrize("label", sorted(DAMAGED_ICNS_INPUTS))
def test_a_damaged_icns_stops_the_build(tmp_path, label):
    """A legal-looking header is not enough: the block table has to hold up too."""
    module = load_build_module()
    source = tmp_path / f"{label}.icns"
    source.write_bytes(DAMAGED_ICNS_INPUTS[label])
    resources = tmp_path / "Resources"
    resources.mkdir()

    with pytest.raises(RuntimeError, match="Not a valid .icns file"):
        module.embed_app_icon(resources, source=source)
    assert list(resources.iterdir()) == []


def test_a_truncated_real_icns_stops_the_build(tmp_path):
    """The first 1000 bytes of the committed icon keep a valid magic and a wrong length."""
    module = load_build_module()
    source = tmp_path / "truncated.icns"
    source.write_bytes(APP_ICON.read_bytes()[:1000])
    resources = tmp_path / "Resources"
    resources.mkdir()

    with pytest.raises(RuntimeError, match="Not a valid .icns file"):
        module.embed_app_icon(resources, source=source)
    assert list(resources.iterdir()) == []


def test_a_missing_icon_stops_the_build(tmp_path):
    module = load_build_module()
    resources = tmp_path / "Resources"
    resources.mkdir()

    with pytest.raises(RuntimeError, match="Missing app icon"):
        module.embed_app_icon(resources, source=tmp_path / "absent.icns")
    assert list(resources.iterdir()) == []


def test_a_directory_instead_of_an_icon_stops_the_build(tmp_path):
    module = load_build_module()
    directory = tmp_path / "adir.icns"
    directory.mkdir()
    resources = tmp_path / "Resources"
    resources.mkdir()

    with pytest.raises(RuntimeError, match="Missing app icon"):
        module.embed_app_icon(resources, source=directory)
    assert list(resources.iterdir()) == []


def test_a_well_formed_icns_is_accepted_and_copied(tmp_path):
    module = load_build_module()
    source = tmp_path / "minimal.icns"
    source.write_bytes(VALID_MINIMAL_ICNS)
    resources = tmp_path / "Resources"
    resources.mkdir()

    assert module.embed_app_icon(resources, source=source) == "AppIcon"
    copied = resources / "AppIcon.icns"
    assert copied.read_bytes() == VALID_MINIMAL_ICNS


def test_the_default_source_is_the_committed_repository_icon(tmp_path):
    module = load_build_module()
    assert module.APP_ICON_RELATIVE_PATH == Path("native/Resources/AppIcon.icns")
    assert module.VOLUME_ICON_RELATIVE_PATH == Path("native/Resources/VolumeIcon.icns")
    assert module.ROOT == REPO_ROOT

    resources = tmp_path / "Resources"
    resources.mkdir()
    assert module.embed_app_icon(resources) == "AppIcon"
    assert (resources / "AppIcon.icns").read_bytes() == APP_ICON.read_bytes()


def test_the_committed_icons_are_valid_and_identical():
    module = load_build_module()
    for path in (APP_ICON, VOLUME_ICON):
        assert path.is_file(), f"{path} must be committed"
        # The full block table, not just the 4-byte magic.
        module.assert_valid_icns(path.read_bytes(), path=path)

    assert APP_ICON.read_bytes() == VOLUME_ICON.read_bytes()


@pytest.mark.skipif(shutil.which("iconutil") is None, reason="iconutil requires macOS")
def test_iconutil_extracts_all_ten_representations(tmp_path):
    iconset = tmp_path / "AppIcon.iconset"
    subprocess.run(
        ["iconutil", "-c", "iconset", str(APP_ICON), "-o", str(iconset)],
        check=True,
        capture_output=True,
    )

    extracted = sorted(path.name for path in iconset.iterdir())
    assert extracted == sorted(ICONSET_ENTRIES)
    assert len(extracted) == 10

    for name, (width, height) in ICONSET_ENTRIES.items():
        data = (iconset / name).read_bytes()
        assert data[:8] == PNG_MAGIC, f"{name} is not a PNG"
        assert (int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")) == (
            width,
            height,
        )


def test_shared_pixel_sizes_hold_identical_pixels_inside_the_icns():
    """One render per pixel size: the container must not carry two different images.

    The committed icon stores 16px and 32px 1x as `ARGB` RLE and the remaining
    eight representations as PNG, so this compares decoded pixels, not bytes.
    """
    blocks = icns_blocks(APP_ICON)
    pairs = [(b"ic11", b"ic05", 32), (b"ic13", b"ic08", 256), (b"ic14", b"ic09", 512)]
    for first, second, size in pairs:
        assert BLOCK_SIZES[first] == size and BLOCK_SIZES[second] == size
        assert block_pixels(blocks, first) == block_pixels(blocks, second), (
            f"{first.decode()} and {second.decode()} ({size}px) hold different images"
        )


@pytest.mark.skipif(shutil.which("iconutil") is None, reason="iconutil requires macOS")
def test_iconutil_extraction_is_not_byte_faithful_for_argb_blocks(tmp_path):
    """Documented iconutil behaviour, not a second render.

    `iconutil -c icns` stores the 16px/32px 1x blocks as `ARGB` RLE holding the
    original (unpremultiplied) pixels, but `iconutil -c iconset` unpremultiplies
    them when writing PNGs again. The 32px pair therefore differs in RGB (and
    gains a few white semi-transparent pixels) while the alpha channel stays
    identical. If Apple ever makes that round trip faithful the bytes become
    equal and this test simply stops exercising the branch.
    """
    iconset = tmp_path / "AppIcon.iconset"
    subprocess.run(
        ["iconutil", "-c", "iconset", str(APP_ICON), "-o", str(iconset)],
        check=True,
        capture_output=True,
    )

    for size, (first_name, second_name) in SHARED_SIZES.items():
        first_bytes = (iconset / first_name).read_bytes()
        second_bytes = (iconset / second_name).read_bytes()
        first = png_pixels(first_bytes)
        second = png_pixels(second_bytes)
        assert [pixel[3] for pixel in first] == [pixel[3] for pixel in second], (
            f"{size}px: alpha channels must be identical"
        )
        opaque = [
            (left, right)
            for left, right in zip(first, second, strict=True)
            if left[3] == 255 and right[3] == 255
        ]
        assert all(left == right for left, right in opaque), (
            f"{size}px: opaque pixels must be identical"
        )
        if first_bytes == second_bytes:
            continue
        assert first == unpremultiply(second) or second == unpremultiply(first), (
            f"{size}px: the extraction difference is not iconutil's ARGB unpremultiply"
        )


@pytest.mark.skipif(shutil.which("iconutil") is None, reason="iconutil requires macOS")
def test_the_iconset_input_has_one_byte_identical_image_per_size(tmp_path):
    """The iconset handed to `iconutil -c icns` is one file per pixel size, copied by name.

    Asserted on the *input* because the extraction side is rewritten by iconutil
    for the ARGB-backed 1x small blocks (see the sibling test).
    """
    iconset = tmp_path / "AppIcon.iconset"
    subprocess.run(
        ["iconutil", "-c", "iconset", str(APP_ICON), "-o", str(iconset)],
        check=True,
        capture_output=True,
    )

    rebuilt = tmp_path / "rebuilt.iconset"
    rebuilt.mkdir()
    for name, (width, _height) in ICONSET_ENTRIES.items():
        shutil.copyfile(iconset / CANONICAL_BY_SIZE[width], rebuilt / name)

    for size, (first_name, second_name) in SHARED_SIZES.items():
        assert (rebuilt / first_name).read_bytes() == (rebuilt / second_name).read_bytes(), (
            f"{size}px: the iconset input must be byte-identical"
        )
