"""Small, deterministic query hints for explicit subjects and short follow-ups."""

from __future__ import annotations

import re
from dataclasses import dataclass

_FOLLOW_UP = re.compile(
    r"^(?:它|这(?:个|项|件|里|些)?|那(?:个|项|件|里|些)?|上述|继续|还有|再问|then\b|"
    r"what about\b|and\s+it\b)",
    re.I,
)
_SUBJECT_SPLIT = re.compile(r"(?:和|与|及|、|,|，|\bvs\.?\b|\band\b|\bor\b)", re.I)
_LEADING_FILLER = re.compile(r"^(?:(?:请问|关于|当前|目前|请帮我看下|请帮我查下)\s*)+")
_TRAILING_CONTEXT = re.compile(r"(?:目前|当前|现行|最新|已确认|相关)$")
_GENERIC_SUBJECTS = {
    "项目",
    "计划",
    "资料",
    "内容",
    "合同",
    "预算",
    "工作",
    "材料",
    "它",
    "这个",
    "那个",
}
_GENERIC_PREFIXES = ("这个", "那个", "该", "此", "本", "我们", "我的", "你的")


@dataclass(frozen=True)
class RetrievalPlan:
    search_question: str
    explicit_subjects: tuple[str, ...]
    used_history_hint: bool


def plan_retrieval(question: str, previous_user_questions: list[str]) -> RetrievalPlan:
    """Add at most the latest user question for clear anaphoric follow-ups.

    The hint only shapes retrieval. The original question and full bounded history
    remain separate in AnswerContext for the answer provider; no prior answer is read.
    """
    normalized = question.strip()
    used_history_hint = bool(
        previous_user_questions and len(normalized) <= 32 and _FOLLOW_UP.search(normalized)
    )
    search_question = normalized
    if used_history_hint:
        latest = previous_user_questions[-1].strip()
        if latest:
            search_question = f"{latest}\n追问：{normalized}"
        else:
            used_history_hint = False
    subjects = _extract_explicit_subjects(search_question)
    return RetrievalPlan(search_question, subjects, used_history_hint)


def matches_explicit_subject(text: str, subjects: tuple[str, ...]) -> bool:
    """Require at least one explicitly named query subject in a candidate passage."""
    if not subjects:
        return True
    normalized_text = re.sub(r"\s+", "", text).casefold()
    return any(re.sub(r"\s+", "", subject).casefold() in normalized_text for subject in subjects)


def _extract_explicit_subjects(question: str) -> tuple[str, ...]:
    source_question = question.split("\n追问：", maxsplit=1)[0]
    if "的" in source_question:
        subject_clause = source_question.split("的", maxsplit=1)[0]
    else:
        english_subject = re.search(r"\bfor\s+([^?!.]+)", source_question, re.I)
        possessive_subject = re.search(r"\b([\w -]+)'s\b", source_question, re.I)
        subject_clause = (
            english_subject.group(1)
            if english_subject
            else possessive_subject.group(1)
            if possessive_subject
            else ""
        )
    subject_clause = _LEADING_FILLER.sub("", subject_clause.strip())
    # Follow-up text may not carry a subject; the preceding question does.
    if not subject_clause:
        return ()
    candidates = []
    for raw in _SUBJECT_SPLIT.split(subject_clause):
        candidate = _TRAILING_CONTEXT.sub("", raw.strip(" ？?，,。；;：:"))
        if (
            len(candidate) < 2
            or candidate in _GENERIC_SUBJECTS
            or candidate.startswith(_GENERIC_PREFIXES)
        ):
            continue
        if candidate not in candidates:
            candidates.append(candidate)
    return tuple(candidates)
