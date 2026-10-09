"""Trust boundaries with synthetic facts and independently calculated proof fixtures."""

from copy import deepcopy
from importlib import import_module
from types import ModuleType

import pytest

BODY = "## 事实\n合同尚未签署。\n"
DIGESTS = {
    "current": "60943005e8117f119709d54552a16d00b6def648e0ad82ba553e5470f33c9bd3",
    "superseded": "98ad5dce3826c9fe9dc7fe5eb0b380487e71bb45b08bb993d28ad9ae9c59af19",
    "invalid": "2bfd868d5d25161452f04e22bc408bc9925afb45a3039003cc70fc593372afab",
}


def core() -> ModuleType:
    try:
        return import_module("summit_everything.domain.content")
    except ModuleNotFoundError:
        pytest.fail("核心内容信任契约尚未实现")


def approved(validity: str = "current") -> dict[str, object]:
    return {
        "id": "note-demo",
        "title": "示例对象",
        "role": "knowledge",
        "kind": "object",
        "line_id": "line-demo",
        "project_id": "project-demo",
        "validity": validity,
        "approval": {
            "version": 1,
            "content_sha256": DIGESTS[validity],
            "confirmed_at": "2026-10-09T04:00:00+00:00",
            "confirmation_id": "confirmation-demo",
        },
    }


def test_hash_matches_independent_utf8_json_fixture() -> None:
    assert core().content_sha256(approved(), BODY) == DIGESTS["current"]


def test_metadata_order_and_line_endings_do_not_change_content_version() -> None:
    api = core()
    assert (
        api.content_sha256(dict(reversed(list(approved().items()))), BODY.replace("\n", "\r\n"))
        == DIGESTS["current"]
    )


def test_current_approved_content_can_be_used() -> None:
    api = core()
    assert api.retrieval_eligibility(approved(), BODY, area=api.StorageArea.FORMAL).eligible


@pytest.mark.parametrize("area", ["source", "draft", "system"])
def test_nonformal_storage_cannot_be_laundered_by_an_approval(area: str) -> None:
    api = core()
    assert not api.retrieval_eligibility(approved(), BODY, area=api.StorageArea(area)).eligible


def test_changed_body_cannot_reuse_old_approval() -> None:
    api = core()
    result = api.retrieval_eligibility(
        approved(), BODY.replace("尚未", "已经"), area=api.StorageArea.FORMAL
    )
    assert not result.eligible
    assert result.reason == "approval_mismatch"


def test_changed_semantic_metadata_cannot_reuse_old_approval() -> None:
    api = core()
    metadata = approved()
    metadata["project_id"] = "different-project"
    assert not api.retrieval_eligibility(metadata, BODY, area=api.StorageArea.FORMAL).eligible


def test_reapproved_new_version_cannot_validate_an_old_cached_chunk() -> None:
    api = core()
    metadata = approved()
    new_body = BODY.replace("尚未", "已经")
    proof = deepcopy(metadata["approval"])
    assert isinstance(proof, dict)
    proof["content_sha256"] = api.content_sha256(metadata, new_body)
    metadata["approval"] = proof
    result = api.retrieval_eligibility(
        metadata,
        new_body,
        area=api.StorageArea.FORMAL,
        expected_content_sha256=DIGESTS["current"],
    )
    assert not result.eligible
    assert result.reason == "stale_snapshot"


@pytest.mark.parametrize("validity", ["superseded", "invalid"])
def test_historical_only_content_needs_explicit_historical_purpose(validity: str) -> None:
    api = core()
    metadata = approved(validity)
    assert not api.retrieval_eligibility(metadata, BODY, area=api.StorageArea.FORMAL).eligible
    assert api.retrieval_eligibility(
        metadata, BODY, area=api.StorageArea.FORMAL, purpose=api.RetrievalPurpose.HISTORY
    ).eligible


@pytest.mark.parametrize("proof", [None, {}, {"version": True}, {"version": 99}])
def test_missing_or_malformed_proof_is_denied(proof: object) -> None:
    api = core()
    metadata = approved()
    metadata["approval"] = proof
    assert not api.retrieval_eligibility(metadata, BODY, area=api.StorageArea.FORMAL).eligible


def test_source_role_is_denied_even_in_a_formal_directory() -> None:
    api = core()
    metadata = approved()
    metadata["role"] = "source"
    proof = deepcopy(metadata["approval"])
    assert isinstance(proof, dict)
    proof["content_sha256"] = api.content_sha256(metadata, BODY)
    metadata["approval"] = proof
    assert not api.retrieval_eligibility(metadata, BODY, area=api.StorageArea.FORMAL).eligible


def test_boolean_version_cannot_impersonate_contract_version_one() -> None:
    api = core()
    metadata = approved()
    proof = deepcopy(metadata["approval"])
    assert isinstance(proof, dict)
    proof["version"] = True
    metadata["approval"] = proof
    assert not api.retrieval_eligibility(metadata, BODY, area=api.StorageArea.FORMAL).eligible


def test_body_whitespace_changes_are_bound_to_the_confirmed_version() -> None:
    api = core()
    assert api.content_sha256(approved(), BODY + "\n") != DIGESTS["current"]


def test_business_completion_does_not_invalidate_confirmed_knowledge() -> None:
    api = core()
    metadata = approved()
    metadata["business_status"] = "completed"
    proof = deepcopy(metadata["approval"])
    assert isinstance(proof, dict)
    proof["content_sha256"] = api.content_sha256(metadata, BODY)
    metadata["approval"] = proof
    assert api.retrieval_eligibility(metadata, BODY, area=api.StorageArea.FORMAL).eligible


def test_non_json_metadata_is_denied_without_crashing_retrieval() -> None:
    api = core()
    metadata = approved()
    metadata["unexpected"] = object()
    assert not api.retrieval_eligibility(metadata, BODY, area=api.StorageArea.FORMAL).eligible


def test_approval_timestamp_requires_a_timezone() -> None:
    api = core()
    metadata = approved()
    proof = deepcopy(metadata["approval"])
    assert isinstance(proof, dict)
    proof["confirmed_at"] = "2026-10-09T12:00:00"
    metadata["approval"] = proof
    assert not api.retrieval_eligibility(metadata, BODY, area=api.StorageArea.FORMAL).eligible


def test_formal_content_rejects_bom_and_empty_body() -> None:
    api = core()
    with pytest.raises(ValueError):
        api.content_sha256(approved(), "\ufeff" + BODY)
    assert not api.retrieval_eligibility(approved(), " \n", area=api.StorageArea.FORMAL).eligible
