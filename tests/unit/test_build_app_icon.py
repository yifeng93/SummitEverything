"""Unit tests for embedding the committed macOS app icon into the app bundle."""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

BUILD_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_macos_app.py"
REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ICON = REPO_ROOT / "native" / "Resources" / "AppIcon.icns"
VOLUME_ICON = REPO_ROOT / "native" / "Resources" / "VolumeIcon.icns"

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

MINIMAL_ICNS = b"icns" + b"\x00\x00\x00\x08"


def load_build_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_build_macos_app_icon_under_test", BUILD_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def test_a_missing_icon_stops_the_build(tmp_path):
    module = load_build_module()
    resources = tmp_path / "Resources"
    resources.mkdir()

    with pytest.raises(RuntimeError, match="Missing app icon"):
        module.embed_app_icon(resources, source=tmp_path / "absent.icns")
    assert list(resources.iterdir()) == []


def test_a_file_that_is_not_an_icns_stops_the_build(tmp_path):
    module = load_build_module()
    source = tmp_path / "fake.icns"
    source.write_bytes(b"not-an-icns")
    resources = tmp_path / "Resources"
    resources.mkdir()

    with pytest.raises(RuntimeError, match="Not a valid .icns file"):
        module.embed_app_icon(resources, source=source)
    assert list(resources.iterdir()) == []


def test_a_truncated_icns_header_stops_the_build(tmp_path):
    module = load_build_module()
    # Correct magic but shorter than the 8-byte minimum.
    source = tmp_path / "short.icns"
    source.write_bytes(b"icns")
    resources = tmp_path / "Resources"
    resources.mkdir()

    with pytest.raises(RuntimeError, match="Not a valid .icns file"):
        module.embed_app_icon(resources, source=source)
    assert list(resources.iterdir()) == []


def test_a_minimal_icns_is_accepted_and_copied(tmp_path):
    module = load_build_module()
    source = tmp_path / "minimal.icns"
    source.write_bytes(MINIMAL_ICNS)
    resources = tmp_path / "Resources"
    resources.mkdir()

    assert module.embed_app_icon(resources, source=source) == "AppIcon"
    copied = resources / "AppIcon.icns"
    assert copied.read_bytes() == MINIMAL_ICNS


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
    for path in (APP_ICON, VOLUME_ICON):
        assert path.is_file(), f"{path} must be committed"
        data = path.read_bytes()
        assert len(data) >= 8
        assert data[:4] == b"icns"

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

    for name, dimensions in ICONSET_ENTRIES.items():
        assert png_dimensions(iconset / name) == dimensions
