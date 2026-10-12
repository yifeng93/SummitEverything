"""Reproducible synthetic M3.2 file-count sample; no remote providers or real data."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from summit_everything.domain.models import IntakeItem
from summit_everything.intake import review, sources
from summit_everything.intake.review import IntakeReviewService
from summit_everything.intake.sources import IntakeService
from summit_everything.integrations.llm import FakeLLM
from summit_everything.workspace import archives, state, transactions, writer
from summit_everything.workspace.archives import archive_completed_transactions, archived_records
from summit_everything.workspace.manifest import create_line, create_project, create_workspace
from summit_everything.workspace.transactions import (
    atomic_write,
    digest,
    workspace_lock,
    write_intent,
)

FLOW_COUNT = 120
MONTHS = ((2026, 6), (2026, 7), (2026, 8), (2026, 9))


class FrozenDateTime(datetime):
    fixed: datetime = datetime(2026, 6, 15, 12, tzinfo=UTC)

    @classmethod
    def now(cls, tz=None):  # type: ignore[no-untyped-def]
        return cls.fixed.astimezone(tz) if tz else cls.fixed.replace(tzinfo=None)


def _count(root: Path, pattern: str) -> int:
    return len(list(root.glob(pattern))) if root.exists() else 0


def main() -> None:
    modules = (review, sources, state, archives, transactions, writer)
    originals = {module: module.datetime for module in modules}
    try:
        with TemporaryDirectory(prefix="summit-m3-package3-bulk-") as directory:
            root = Path(directory) / "workspace"
            create_workspace(root, "合成 M3.2 计数库", root.parent / "profile", "bulk-create")
            line = create_line(root, "合成主线", "bulk-line")
            project = create_project(root, line.id, "合成项目", "bulk-project")
            provider = FakeLLM()
            intake = IntakeService()
            service = IntakeReviewService(provider)
            operation_ids: list[str] = []
            sha_operation_ids: list[str] = []

            for index in range(FLOW_COUNT):
                year, month = MONTHS[index % len(MONTHS)]
                FrozenDateTime.fixed = datetime(year, month, 15, 12, tzinfo=UTC)
                for module in modules:
                    module.datetime = FrozenDateTime
                operation_id = f"bulk-source-{index:03d}"
                operation_ids.append(operation_id)
                item = intake.add_text(
                    root,
                    f"Synthetic source {index}",
                    filename=f"source-{index:03d}.txt",
                    operation_id=operation_id,
                )
                job = service.create_job(
                    root,
                    [item.item_id],
                    operation_id=f"bulk-job-{index:03d}",
                    line_id=line.id,
                    project_id=project.id,
                )
                draft = service.get_draft(root, job.draft_ids[0])
                service.confirm_draft(
                    root,
                    draft.draft_id,
                    expected_version=draft.version,
                    confirmation_id=f"bulk-confirm-{index:03d}",
                    operation_id=f"bulk-write-{index:03d}",
                    conflict_resolutions={},
                )
                target = root / ".summit-everything" / "bulk-write-intent-target.json"
                expected = digest(target.read_bytes() if target.exists() else None)
                sha_operation_id = f"bulk-write-intent-{index:03d}"
                sha_operation_ids.append(sha_operation_id)
                with workspace_lock(root):
                    write_intent(
                        root,
                        sha_operation_id,
                        target,
                        expected,
                        json.dumps({"synthetic_write": index}).encode(),
                    )
                if (index + 1) % (FLOW_COUNT // len(MONTHS)) == 0:
                    print(f"completed={index + 1}")

            # Add synthetic completed Feishu receipts for each month so that
            # the family participates in this filesystem-only compression check.
            tx_root = root / ".summit-everything" / "transactions"
            for ordinal, (year, month) in enumerate(MONTHS):
                finished = datetime(year, month, 20, tzinfo=UTC).isoformat()
                key = hashlib.sha256(f"bulk-feishu-{ordinal}".encode()).hexdigest()
                atomic_write(
                    tx_root / f"feishu-import-{key}.json",
                    json.dumps(
                        {
                            "request_hash": hashlib.sha256(key.encode()).hexdigest(),
                            "state": "completed",
                            "result": {"state": "succeeded", "synthetic": True},
                            "finished_at": finished,
                        },
                        sort_keys=True,
                    ).encode(),
                )

            # Preserve one legacy undated terminal item and one unknown job/item
            # as visible active exceptions; their dates are not fabricated.
            unknown_id, unknown_job_id = uuid4(), uuid4()
            intake_root = root / ".summit-everything" / "intake"
            unknown_item = IntakeItem(
                item_id=unknown_id,
                source_id=uuid4(),
                title="synthetic unknown",
                filename="unknown.txt",
                original_relative_path="原件/unknown.txt",
                created_at=datetime(2026, 9, 15, tzinfo=UTC),
                state="unknown",
                latest_job_id=unknown_job_id,
            )
            atomic_write(
                intake_root / "items" / f"{unknown_id}.json",
                unknown_item.model_dump_json().encode(),
            )
            unknown_job = {
                "job_id": str(unknown_job_id),
                "item_ids": [str(unknown_id)],
                "request_hash": "u" * 64,
                "state": "unknown",
                "created_at": "2026-09-15T00:00:00+00:00",
                "attempt_id": str(uuid4()),
                "revision": 2,
                "draft_ids": [],
            }
            atomic_write(
                intake_root / "jobs" / f"{unknown_job_id}.json", json.dumps(unknown_job).encode()
            )
            legacy_id = uuid4()
            legacy = IntakeItem(
                item_id=legacy_id,
                source_id=uuid4(),
                title="synthetic legacy undated",
                filename="legacy.txt",
                original_relative_path="原件/legacy.txt",
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
                state="completed",
                latest_job_id=uuid4(),
                attempt_no=0,
            )
            atomic_write(
                intake_root / "items" / f"{legacy_id}.json", legacy.model_dump_json().encode()
            )

            FrozenDateTime.fixed = datetime(2026, 10, 1, tzinfo=UTC)
            for module in modules:
                module.datetime = FrozenDateTime
            with workspace_lock(root):
                archive_completed_transactions(root, now=FrozenDateTime.fixed, locked=True)
            state.archive_intake(root, now=FrozenDateTime.fixed)

            archived_items = archived_records(root, "intake-items")
            archived_jobs = archived_records(root, "intake-jobs")
            archived_tx = archived_records(root, "transactions")
            active_items = [
                IntakeItem.model_validate_json(path.read_bytes())
                for path in (intake_root / "items").glob("*.json")
            ]
            active_jobs = [
                json.loads(path.read_bytes()) for path in (intake_root / "jobs").glob("*.json")
            ]
            replay_item = intake.add_text(
                root,
                "Synthetic source 0",
                filename="source-000.txt",
                operation_id=operation_ids[0],
            )
            replay_job = service.create_job(
                root,
                [replay_item.item_id],
                operation_id="bulk-job-000",
                line_id=line.id,
                project_id=project.id,
            )
            if provider.calls != FLOW_COUNT:
                raise RuntimeError("Archive replay unexpectedly called the provider")

            month_summaries = sorted(
                str(path.relative_to(root / ".summit-everything" / "archives"))
                for path in (root / ".summit-everything" / "archives").rglob("summary.json")
            )
            sources_count = _count(root / "原件", "*/*.txt")
            drafts = list((root / ".summit-everything" / "drafts").glob("*.json"))
            flow_month_strings = {f"{year:04d}-{month:02d}" for year, month in MONTHS}
            sha_records = [
                name for name in archived_tx if len(name) == 69 and name.endswith(".json")
            ]
            summary = {
                "flows_completed": FLOW_COUNT,
                "months": [f"{year:04d}-{month:02d}" for year, month in MONTHS],
                "setup_only_summary_months": sorted(
                    {
                        path.parent.name
                        for path in (root / ".summit-everything" / "archives").rglob("summary.json")
                        if path.parent.name not in flow_month_strings
                    }
                ),
                "provider_calls_including_replay": provider.calls,
                "replay_item_state": replay_item.state,
                "replay_job_state": replay_job.state,
                "active_item_records_total": len(active_items),
                "newflow_active_items_including_unknown": sum(
                    item.item_id != legacy_id for item in active_items
                ),
                "unknown_active_items": sum(item.state == "unknown" for item in active_items),
                "completed_sample_items_still_active": sum(
                    item.item_id not in {legacy_id, unknown_id} for item in active_items
                ),
                "legacy_undated_active_items": sum(
                    item.item_id == legacy_id for item in active_items
                ),
                "active_item_category_note": (
                    "unknown is newflow; legacy-undated is separate; categories overlap total"
                ),
                "active_job_records_total": len(active_jobs),
                "newflow_active_jobs_including_unknown": len(active_jobs),
                "unknown_active_jobs": sum(job["state"] == "unknown" for job in active_jobs),
                "completed_sample_jobs_still_active": sum(
                    job["state"] != "unknown" for job in active_jobs
                ),
                "item_month_records": len(archived_items),
                "job_month_records": len(archived_jobs),
                "transaction_month_records": len(archived_tx),
                "transaction_family_records": {
                    "capture_intake": sum(name.startswith("intake-") for name in archived_tx),
                    "mutation": sum(name.startswith("mutation-") for name in archived_tx),
                    "write_intent_sha_total": len(sha_records),
                    "write_intent_sha_bulk_sample": sum(
                        hashlib.sha256(operation_id.encode()).hexdigest() + ".json" in sha_records
                        for operation_id in sha_operation_ids
                    ),
                    "write_intent_sha_setup": len(sha_records) - len(sha_operation_ids),
                    "feishu_import_synthetic_compression_records": sum(
                        name.startswith("feishu-import-") for name in archived_tx
                    ),
                    "feishu_import_fake_provider_replay_test": (
                        "separate integration regression; not counted as bulk provider activity"
                    ),
                },
                "monthly_summary_files": month_summaries,
                "original_files": sources_count,
                "draft_files_with_full_body": len(drafts),
                "checkpoint_files_after_completion": _count(intake_root / "checkpoints", "*.json"),
                "lease_files_after_completion": _count(
                    root / ".summit-everything" / "attempt-leases", "*.lock"
                ),
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    finally:
        for module, value in originals.items():
            module.datetime = value


if __name__ == "__main__":
    main()
