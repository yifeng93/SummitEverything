from __future__ import annotations

from pathlib import Path

import pytest
from test_c19_r2_expanded_matrix import ask, excerpts, make_query


QUESTIONS = [
    ("fact", "白萤会展的年度访客信息登记办法是什么？"),
    ("comparison", "比较白萤会展的年度访客信息登记办法"),
    ("plan", "为白萤会展制定年度访客信息登记工作方案"),
]


@pytest.mark.parametrize(("mode", "question"), QUESTIONS)
def test_complete_information_qualifier_is_positive_evidence(tmp_path: Path, mode: str, question: str) -> None:
    root, service, answerer = make_query(tmp_path, [
        ("白萤会展", "年度访客信息登记", "白萤会展年度访客信息登记须核验身份。", None),
    ])
    answer = ask(service, root, question, mode)
    observed = {"citations": excerpts(answer), "missing": answer.missing_information,
                "provider_calls": len(answerer.calls), "text": answer.text}
    print(observed)
    assert answer.citations and "核验身份" in excerpts(answer), observed
    assert answerer.calls and "核验身份" in "\n".join(p["excerpt"] for p in answerer.calls[0][1]), observed
    assert not answer.missing_information, observed


@pytest.mark.parametrize(("mode", "question"), QUESTIONS)
def test_missing_information_qualifier_cannot_be_backfilled(tmp_path: Path, mode: str, question: str) -> None:
    root, service, answerer = make_query(tmp_path, [
        ("白萤会展", "年度访客登记", "白萤会展年度访客登记须核验身份。", None),
    ])
    answer = ask(service, root, question, mode)
    observed = {"citations": excerpts(answer), "missing": answer.missing_information,
                "provider_calls": len(answerer.calls), "text": answer.text}
    print(observed)
    assert not answer.citations, observed
    assert answer.missing_information, observed
    assert not answerer.calls, observed
