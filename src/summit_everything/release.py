"""Validated, non-secret identity data embedded in an internal app build."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import TypedDict, cast


class BuildIdentity(TypedDict):
    source_sha: str
    dirty: bool
    build_id: str
    app_version: str
    frontend_sha256: str
    dependencies_sha256: str


def load_build_identity(path: str | None) -> BuildIdentity:
    if path is None:
        return {
            "source_sha": "unmanaged",
            "dirty": True,
            "build_id": "development",
            "app_version": "0.1.0",
            "frontend_sha256": "unmanaged",
            "dependencies_sha256": "unmanaged",
        }
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Build manifest is unavailable or invalid") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "source_sha",
        "dirty",
        "build_id",
        "app_version",
        "frontend_sha256",
        "dependencies_sha256",
    }:
        raise ValueError("Build manifest fields are invalid")
    identity = payload
    if (
        not isinstance(identity["source_sha"], str)
        or not re.fullmatch(r"[0-9a-f]{40}", identity["source_sha"])
        or not isinstance(identity["dirty"], bool)
        or not isinstance(identity["build_id"], str)
        or not identity["build_id"]
        or len(identity["build_id"]) > 100
        or not isinstance(identity["app_version"], str)
        or not re.fullmatch(r"\d+\.\d+\.\d+", identity["app_version"])
        or any(
            not isinstance(identity[key], str) or not re.fullmatch(r"[0-9a-f]{64}", identity[key])
            for key in ("frontend_sha256", "dependencies_sha256")
        )
    ):
        raise ValueError("Build manifest values are invalid")
    return cast(BuildIdentity, identity)


def fingerprint_web_dist(path: str) -> str:
    root = Path(path)
    digest = hashlib.sha256()
    for item in sorted(root.rglob("*")):
        if item.is_file():
            digest.update(item.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(hashlib.sha256(item.read_bytes()).digest())
    return digest.hexdigest()


def verify_dependency_manifest(build_info_path: str, expected_sha256: str) -> None:
    dependencies = Path(build_info_path).with_name("dependencies.json")
    try:
        actual = hashlib.sha256(dependencies.read_bytes()).hexdigest()
    except OSError as exc:
        raise ValueError("Dependency manifest is unavailable") from exc
    if actual != expected_sha256:
        raise ValueError("Dependency identity does not match build manifest")
