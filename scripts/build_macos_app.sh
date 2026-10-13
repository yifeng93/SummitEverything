#!/bin/sh
set -eu

if [ "$#" -lt 1 ]; then
    echo "Usage: scripts/build_macos_app.sh OUTPUT.app [--dmg OUTPUT.dmg]" >&2
    exit 2
fi

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"
exec uv run --locked python scripts/build_macos_app.py "$@"
