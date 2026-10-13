#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
    echo "Usage: scripts/release-macos.sh OUTPUT.app OUTPUT.dmg" >&2
    echo "Builds a local unsigned internal candidate; it does not install or publish." >&2
    exit 2
fi

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"
exec uv run --locked python scripts/build_macos_app.py "$1" --dmg "$2"
