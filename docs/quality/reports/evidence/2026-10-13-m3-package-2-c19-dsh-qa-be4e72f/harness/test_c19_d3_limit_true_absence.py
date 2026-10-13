from __future__ import annotations

from pathlib import Path

import pytest
from test_c19_r2_expanded_matrix import ask, make_query


PAGES = [
    ("云岬营地", f"预算记录{i}", f"云岬营地预算额度第{i}项为{i * 10000 + 30000}元。", None)
    for i in range(1, 7)
] + [
    ("汀屿计划", "流程记录", "汀屿计划访客登记须由前台核验。", None),
]
QUESTION = "比较云岬营地预算与汀屿计划的排期"


@pytest.mark.parametrize("mode", ["fact", "comparison", "plan"])
def test_default_limit_does_not_mask_genuinely_absent_pair(tmp_path: Path, mode: str) -> None:
    root, service, answerer = make_query(tmp_path, PAGES)
    answer = ask(service, root, QUESTION, mode)
    observed = {
        "citations": [citation.excerpt for citation in answer.citations],
        "provider_calls": len(answerer.calls),
        "missing": answer.missing_information,
        "text": answer.text,
    }
    print(observed)
    # The fixture has six valid A-budget candidates and no B-schedule support.
    # Default limit=5 may produce a cap notice for additionally uncovered pairs,
    # but must retain the independently true B absence rather than replace it.
    assert len(answer.citations) == 5, observed
    assert any("汀屿计划" in item and "缺少" in item for item in answer.missing_information), observed
    assert any("上限" in item for item in answer.missing_information), observed


def test_higher_limit_confirms_same_real_absence_without_truncation(tmp_path: Path) -> None:
    root, service, answerer = make_query(tmp_path, PAGES)
    answer = service.query(
        root, QUESTION, fingerprint="fresh-holdout-v1", answer_mode="comparison", limit=20
    )
    observed = {
        "citations": [citation.excerpt for citation in answer.citations],
        "provider_calls": len(answerer.calls),
        "missing": answer.missing_information,
        "text": answer.text,
    }
    print(observed)
    assert any("汀屿计划" in item and "缺少" in item for item in answer.missing_information), observed
    assert not any("上限" in item for item in answer.missing_information), observed
