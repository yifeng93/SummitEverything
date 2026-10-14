"""Build a relocatable, unsigned arm64 macOS internal app bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from summit_everything.integrations.first_use_defaults import (  # noqa: E402
    BUNDLE_RESOURCE_NAME,
    REPO_DEFAULTS_RELATIVE_PATH,
    FirstUseDefaults,
    read_first_use_defaults_file,
)
from summit_everything.release import fingerprint_web_dist  # noqa: E402


def run(args: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def embed_first_use_defaults(
    resources: Path, *, source: Path | None = None
) -> FirstUseDefaults | None:
    """Validate and copy the optional local non-secret defaults into Resources.

    Returns the loaded defaults, or ``None`` when the local file is absent so a
    build never depends on it. Secret-shaped keys fail closed through
    :func:`read_first_use_defaults_file`; nothing is copied in that case.
    """
    path = source if source is not None else ROOT / REPO_DEFAULTS_RELATIVE_PATH
    if not path.is_file():
        return None
    defaults = read_first_use_defaults_file(path)
    shutil.copy2(path, resources / BUNDLE_RESOURCE_NAME)
    return defaults


def packages_inventory() -> list[dict[str, str]]:
    source = (
        "import importlib.metadata as m, json; "
        "print(json.dumps(sorted(({ 'name': d.metadata['Name'], 'version': d.version } "
        "for d in m.distributions()), key=lambda x: x['name'].lower())))"
    )
    result = subprocess.check_output(
        ["uv", "run", "--group", "build", "python", "-c", source], cwd=ROOT, text=True
    )
    return json.loads(result)


def create_dmg(app: Path, dmg: Path) -> None:
    if dmg.exists():
        raise FileExistsError(f"Refusing to overwrite existing DMG: {dmg}")
    dmg.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="summit-dmg-", dir=dmg.parent) as temporary:
        staged_dmg = Path(temporary) / dmg.name
        mount = Path(temporary) / "mount"
        mount.mkdir()
        run(
            [
                "hdiutil",
                "create",
                "-volname",
                "SummitEverything Internal",
                "-srcfolder",
                str(app),
                "-format",
                "UDZO",
                str(staged_dmg),
            ]
        )
        run(["hdiutil", "verify", str(staged_dmg)])
        mounted = False
        try:
            run(
                [
                    "hdiutil",
                    "attach",
                    "-readonly",
                    "-nobrowse",
                    "-mountpoint",
                    str(mount),
                    str(staged_dmg),
                ]
            )
            mounted = True
            bundled_app = mount / app.name
            if not bundled_app.is_dir():
                raise RuntimeError("Mounted DMG does not contain the internal app")
            run(["codesign", "--verify", "--deep", "--strict", str(bundled_app)])
        finally:
            if mounted:
                run(["hdiutil", "detach", str(mount)])
        os.replace(staged_dmg, dmg)


def build(output: Path, *, allow_dirty: bool, dmg: Path | None = None) -> None:
    if sys.platform != "darwin" or os.uname().machine != "arm64":
        raise RuntimeError("This internal candidate builder requires an arm64 macOS host")
    if output.suffix != ".app" or output.exists():
        raise FileExistsError(f"App output must be a new .app path: {output}")
    if dmg is not None and dmg.exists():
        raise FileExistsError(f"Refusing to overwrite existing DMG: {dmg}")
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, text=True
    )
    if status.strip() and not allow_dirty:
        raise RuntimeError(
            "Refusing a dirty source tree; set SUMMIT_ALLOW_DIRTY=1 only for local iteration"
        )

    run(["npm", "--prefix", "web", "run", "build"])
    run(["uv", "sync", "--locked", "--group", "build"])
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    build_number = int(
        subprocess.check_output(["git", "rev-list", "--count", "HEAD"], cwd=ROOT, text=True)
    )
    if not 1 <= build_number <= 9999:
        raise RuntimeError("The source commit count cannot be represented as CFBundleVersion")
    frontend_sha = fingerprint_web_dist(str(ROOT / "web" / "dist"))
    dependency_data = {
        "python_lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
        "frontend_lock_sha256": hashlib.sha256(
            (ROOT / "web" / "package-lock.json").read_bytes()
        ).hexdigest(),
        "python_packages": packages_inventory(),
    }
    dependency_bytes = json.dumps(dependency_data, sort_keys=True, separators=(",", ":")).encode()
    dependencies_sha = hashlib.sha256(dependency_bytes).hexdigest()
    manifest = {
        "source_sha": source_sha,
        "dirty": bool(status.strip()),
        "build_id": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + frontend_sha[:12],
        "app_version": version,
        "frontend_sha256": frontend_sha,
        "dependencies_sha256": dependencies_sha,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".summit-internal-build-", dir=output.parent
    ) as temporary:
        work = Path(temporary)
        app = work / output.name
        staged_dmg = work / dmg.name if dmg is not None else None
        contents = app / "Contents"
        resources = contents / "Resources"
        (contents / "MacOS").mkdir(parents=True)
        resources.mkdir()
        run(
            [
                "uv",
                "run",
                "--group",
                "build",
                "pyinstaller",
                "--noconfirm",
                "--clean",
                "--onedir",
                "--name",
                "summit-backend",
                "--paths",
                str(ROOT / "src"),
                "--collect-all",
                "keyring",
                "--distpath",
                str(work / "dist"),
                "--workpath",
                str(work / "work"),
                "--specpath",
                str(work),
                str(ROOT / "scripts" / "packaged_server.py"),
            ]
        )
        shutil.copytree(work / "dist" / "summit-backend", resources / "backend" / "summit-backend")
        shutil.copytree(ROOT / "web" / "dist", resources / "web")
        (resources / "build-info.json").write_text(
            json.dumps(manifest, sort_keys=True), encoding="utf-8"
        )
        (resources / "dependencies.json").write_bytes(dependency_bytes)
        # Optional non-secret first-use defaults from the Git-ignored local file.
        # They are validated (secret-shaped keys fail closed) and copied before
        # signing; a missing file leaves the bundle unchanged.
        embedded_defaults = embed_first_use_defaults(resources)
        if embedded_defaults is None:
            print("No local first-use defaults file; building without injected defaults")
        else:
            field_names = ",".join(sorted(embedded_defaults.values)) or "none"
            print(
                "Embedded non-secret first-use defaults "
                f"from {embedded_defaults.source} fields={field_names}"
            )
        swift_env = dict(os.environ)
        swift_env["MACOSX_DEPLOYMENT_TARGET"] = "13.0"
        swift_command = ["swift", "build", "-c", "release", "--package-path", str(ROOT / "native")]
        # SwiftPM compiles Package.swift inside its own sandbox. A build already
        # running under a sandbox (local harnesses, some CI wrappers) cannot nest
        # that and fails with "sandbox_apply: Operation not permitted". The escape
        # hatch is explicit so default and CI behaviour stay unchanged; it only
        # affects this repository's own manifest.
        if os.environ.get("SUMMIT_SWIFT_DISABLE_SANDBOX") == "1":
            swift_command.append("--disable-sandbox")
        run(swift_command, env=swift_env)
        binary = ROOT / "native" / ".build" / "release" / "SummitEverything"
        shutil.copy2(binary, contents / "MacOS" / "SummitEverything")
        with (contents / "Info.plist").open("wb") as stream:
            plistlib.dump(
                {
                    "CFBundleExecutable": "SummitEverything",
                    "CFBundleIdentifier": "com.summiteverything.internal",
                    "CFBundleName": "SummitEverything Internal",
                    "CFBundleDisplayName": "SummitEverything Internal",
                    "CFBundlePackageType": "APPL",
                    "CFBundleVersion": f"{build_number}.0.0",
                    "CFBundleShortVersionString": version,
                    "SummitBuildID": manifest["build_id"],
                    "LSMinimumSystemVersion": "13.0",
                    "NSHighResolutionCapable": True,
                },
                stream,
            )
        run(["codesign", "--force", "--deep", "--sign", "-", str(app)])
        run(["codesign", "--verify", "--deep", "--strict", str(app)])
        if staged_dmg is not None:
            create_dmg(app, staged_dmg)
        os.replace(app, output)
        if staged_dmg is not None and dmg is not None:
            os.replace(staged_dmg, dmg)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "output", type=Path, help="new .app output path; existing paths are refused"
    )
    parser.add_argument(
        "--dmg", type=Path, help="optional new DMG output path; existing paths are refused"
    )
    args = parser.parse_args()
    build(
        args.output.expanduser().resolve(),
        allow_dirty=os.environ.get("SUMMIT_ALLOW_DIRTY") == "1",
        dmg=args.dmg.expanduser().resolve() if args.dmg else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
