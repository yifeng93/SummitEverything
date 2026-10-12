from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from summit_everything.domain.models import IntakeJob, IntakeItem
from summit_everything.intake.sources import IntakeService
from summit_everything.workspace.manifest import load_manifest
from summit_everything.workspace.transactions import atomic_write

base = Path(__file__).resolve().parent
root = base / "workspace"
manifest = load_manifest(root)
item = IntakeService().add_text(root, "Synthetic failed provider attempt for browser QA only.", filename="unknown-fixture.txt", operation_id=f"unknown-source-{uuid4()}")
job_id = uuid4()
line = manifest.lines[0]
project = manifest.projects[0]
job = IntakeJob(job_id=job_id, item_ids=[item.item_id], line_id=line.id, project_id=project.id, request_hash=hashlib.sha256(b"unknown-fixture").hexdigest(), state="unknown", draft_ids=[], error="provider outcome unknown", created_at=datetime.now(UTC), attempt_id=str(uuid4()), revision=2)
item = item.model_copy(update={"state": "unknown", "latest_job_id": job_id, "revision": item.revision + 1})
meta = root / ".summit-everything" / "intake"
atomic_write(meta / "jobs" / f"{job_id}.json", job.model_dump_json(indent=2).encode())
atomic_write(meta / "items" / f"{item.item_id}.json", item.model_dump_json(indent=2).encode())
print(json.dumps({"item_id": str(item.item_id), "job_id": str(job_id), "item_state": item.state, "job_state": job.state}))
