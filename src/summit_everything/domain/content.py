"""Version-bound trust gate shared by indexing and retrieval.

Storage classification must come from the workspace reader, never model output.
This module performs no I/O and does not issue approval proofs.
"""

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class StorageArea(StrEnum):
    FORMAL = "formal"
    SOURCE = "source"
    DRAFT = "draft"
    SYSTEM = "system"


class RetrievalPurpose(StrEnum):
    CURRENT = "current"
    HISTORY = "history"


@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    reason: str
    content_sha256: str | None = None


_KINDS = frozenset({"project_overview", "object", "case", "topic", "decision", "log", "thought"})
_UNBOUND_KINDS = frozenset({"log", "thought"})
_VALIDITIES = frozenset({"current", "superseded", "invalid"})
_DIGEST = re.compile(r"[0-9a-f]{64}")


def content_sha256(metadata: Mapping[str, object], body: str) -> str:
    """Hash all JSON metadata except approval plus the LF-normalized body.

    Metadata ordering and CRLF are presentation changes. All other body whitespace
    and all semantic metadata participate. Filesystem paths are not an input.
    Boundary readers must convert YAML dates to ISO strings before calling this.
    """
    if body.startswith("\ufeff"):
        raise ValueError("UTF-8 BOM is not allowed in formal Markdown")
    payload = {
        "metadata": {key: value for key, value in metadata.items() if key != "approval"},
        "body": body.replace("\r\n", "\n").replace("\r", "\n"),
    }
    serialized = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def retrieval_eligibility(
    metadata: Mapping[str, object],
    body: str,
    *,
    area: StorageArea,
    purpose: RetrievalPurpose = RetrievalPurpose.CURRENT,
    expected_content_sha256: str | None = None,
) -> Eligibility:
    """Default-deny gate; HISTORY also admits approved superseded/invalid pages.

    Call with HISTORY while indexing the qualified corpus. Call again against
    freshly read content for every final query candidate and citation, passing its
    cached version as expected_content_sha256. This also rejects stale chunks after
    the new content has been reapproved.
    """
    if area != StorageArea.FORMAL:
        return Eligibility(False, "excluded_storage")
    if metadata.get("role") != "knowledge":
        return Eligibility(False, "not_knowledge")
    kind = metadata.get("kind")
    validity = metadata.get("validity", "current")
    if (
        not isinstance(kind, str)
        or kind not in _KINDS
        or not isinstance(validity, str)
        or validity not in _VALIDITIES
        or not all(_nonempty_string(metadata.get(key)) for key in ("id", "title"))
        or (
            kind not in _UNBOUND_KINDS
            and not all(_nonempty_string(metadata.get(key)) for key in ("line_id", "project_id"))
        )
    ):
        return Eligibility(False, "invalid_metadata")
    if not body.strip():
        return Eligibility(False, "empty_body")
    proof = metadata.get("approval")
    if not isinstance(proof, Mapping):
        return Eligibility(False, "invalid_approval")
    digest, timestamp = proof.get("content_sha256"), proof.get("confirmed_at")
    if (
        type(proof.get("version")) is not int
        or proof.get("version") != 1
        or not isinstance(digest, str)
        or _DIGEST.fullmatch(digest) is None
        or not isinstance(timestamp, str)
        or not _nonempty_string(proof.get("confirmation_id"))
    ):
        return Eligibility(False, "invalid_approval")
    try:
        if datetime.fromisoformat(timestamp).utcoffset() is None:
            return Eligibility(False, "invalid_approval")
        actual = content_sha256(metadata, body)
    except (TypeError, ValueError):
        return Eligibility(False, "invalid_approval")
    if digest != actual:
        return Eligibility(False, "approval_mismatch", actual)
    if expected_content_sha256 is not None and expected_content_sha256 != actual:
        return Eligibility(False, "stale_snapshot", actual)
    if validity != "current" and purpose != RetrievalPurpose.HISTORY:
        return Eligibility(False, "historical_only", actual)
    return Eligibility(True, "approved", actual)
