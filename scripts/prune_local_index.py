"""Prune old local LanceDB generations after the app has exited."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from summit_everything.retrieval.store import IndexStore  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-db", type=Path, required=True, help="Profile index.sqlite3 path")
    parser.add_argument(
        "--app-stopped",
        action="store_true",
        help="Confirm that SummitEverything has exited and no queries are in flight",
    )
    args = parser.parse_args()
    if not args.app_stopped:
        parser.error(
            "stop SummitEverything, then pass --app-stopped to confirm the maintenance window"
        )
    result = IndexStore(args.index_db).prune_old_generations(retain_previous=1)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
