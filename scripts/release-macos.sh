#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
    echo "Usage: scripts/release-macos.sh OUTPUT.app OUTPUT.dmg" >&2
    echo "Builds a local unsigned internal candidate; it does not install or publish." >&2
    exit 2
fi

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"
export MACOSX_DEPLOYMENT_TARGET=13.0
uv sync --locked --group dev --group build --python-platform aarch64-apple-darwin
exec uv run --locked --group dev --group build --python-platform aarch64-apple-darwin python scripts/build_macos_app.py "$1" --dmg "$2"
