from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from summit_everything.domain.models import IntakeItem
from summit_everything.intake.review import IntakeReviewService
from summit_everything.intake.sources import IntakeService
from summit_everything.integrations.llm import FakeLLM
from summit_everything.workspace.manifest import create_line, create_project
from summit_everything.workspace.transactions import atomic_write

root = Path(__file__).resolve().parents[1] / "workspace-ui"
line = create_line(root, "Synthetic QA line", "qa-line")
project = create_project(root, line.id, "Synthetic QA project", "qa-project")
intake = IntakeService()
review = IntakeReviewService(FakeLLM())
reviewing = intake.add_text(root, "Deidentified text retained for manual review.", filename="review.txt", operation_id="browser-review-source")
job = review.create_job(root, [reviewing.item_id], operation_id="browser-review-job", line_id=line.id, project_id=project.id)
unknown = intake.add_text(root, "Deidentified unknown source.", filename="unknown.txt", operation_id="browser-unknown-source")
unknown = unknown.model_copy(update={"state": "unknown", "attempt_id": str(uuid4()), "finished_at": None})
unknown_path = root / ".summit-everything" / "intake" / "items" / f"{unknown.item_id}.json"
atomic_write(unknown_path, unknown.model_dump_json(indent=2).encode())
print(json.dumps({"workspace": str(root), "project_id": str(project.id), "review_job_state": job.state, "review_draft_count": len(review.list_drafts(root, pending_only=True)), "unknown_item_id": str(unknown.item_id), "provider_calls": review.provider.calls}, ensure_ascii=False))
