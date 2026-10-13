from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import yaml
from summit_everything.domain.content import content_sha256
from summit_everything.workspace.manifest import load_manifest

base = Path(__file__).resolve().parents[1]
workspace = base / "workspace-A"
manifest = load_manifest(workspace)
metadata = {
    "id": str(uuid4()),
    "title": "QA 无效历史场地规则",
    "role": "knowledge",
    "kind": "topic",
    "line_id": str(manifest.lines[0].id),
    "project_id": str(manifest.projects[0].id),
    "validity": "invalid",
}
body = "青岚计划曾有一条已失效的场地规则：开放时间为上午九点。\n"
metadata["approval"] = {
    "version": 1,
    "content_sha256": content_sha256(metadata, body),
    "confirmed_at": datetime.now(UTC).isoformat(),
    "confirmation_id": "qa-repair1-synthetic-invalid-fixture",
}
path = workspace / "QA-合成主线" / "QA-合成项目" / "QA-青岚失效场地规则.md"
path.write_text("---\n" + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False) + "---\n" + body, encoding="utf-8")
result = {"page_id": metadata["id"], "path": str(path.relative_to(base)), "validity": metadata["validity"], "content_sha256": metadata["approval"]["content_sha256"], "body_sha256": hashlib.sha256(body.encode()).hexdigest()}
(base / "harness" / "invalid-fixture-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
