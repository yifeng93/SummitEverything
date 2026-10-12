"""Small, deterministic query hints for explicit subjects and short follow-ups."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

_FOLLOW_UP = re.compile(
    r"^(?:它|这(?:个|项|件|里|些)?|那(?:个|项|件|里|些)?|上述|继续|还有|再问|then\b|"
    r"what about\b|and\s+it\b)",
    re.I,
)
_SUBJECT_SPLIT = re.compile(r"(?:和|与|及|、|,|，|\bvs\.?\b|\band\b|\bor\b)", re.I)
_QUESTION_SPLIT = re.compile(r"[。！？!?；;\n]+")
_TRAILING_CONTEXT = re.compile(r"(?:目前|当前|现行|最新|已确认|相关)$")
_REQUEST_CLAUSE = re.compile(
    r"(?:我.*(?:想知道|希望|想问|想了解)|(?:你|您).*(?:能|可以|可否|能否|告诉|说明|帮)|"
    r"^(?:请|麻烦)(?:帮我)?|^(?:能否|可否))"
)
_GENERIC_SUBJECTS = {
    "项目",
    "计划",
    "资料",
    "内容",
    "合同",
    "预算",
    "工作",
    "材料",
    "现在",
    "目前",
    "当前",
    "现行",
    "最新",
    "情况",
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
    unresolved_topic: bool = False


def plan_retrieval(
    question: str,
    previous_user_questions: list[str],
    subject_aliases: Iterable[str] = (),
) -> RetrievalPlan:
    """Use only an explicit subject or the nearest bounded user-question topic.

    Prior assistant answers are never supplied. A complete user question is a topic
    boundary even when its subject is unknown or cannot be parsed confidently.
    """
    normalized = question.strip()
    aliases = _clean_aliases(subject_aliases)
    is_follow_up = _is_follow_up(normalized)
    current_subjects, current_unresolved = _extract_explicit_subjects(normalized, aliases)

    if current_subjects or current_unresolved or not is_follow_up:
        return RetrievalPlan(
            normalized,
            current_subjects,
            False,
            unresolved_topic=current_unresolved,
        )

    # Skip intervening pronoun-only questions, but never cross a complete question.
    for prior_question in reversed(previous_user_questions):
        prior = prior_question.strip()
        if not prior or _is_follow_up(prior):
            continue
        prior_subjects, _ = _extract_explicit_subjects(prior, aliases)
        if prior_subjects:
            return RetrievalPlan(f"{prior}\n追问：{normalized}", prior_subjects, True)
        # An unresolved or subjectless complete question still starts a new topic.
        return RetrievalPlan(normalized, (), False, unresolved_topic=True)

    return RetrievalPlan(normalized, (), False, unresolved_topic=True)


def matches_explicit_subject(text: str, subjects: tuple[str, ...]) -> bool:
    """Require at least one explicitly named query subject in a candidate passage."""
    if not subjects:
        return True
    normalized_text = _normalize(text)
    return any(_normalize(subject) in normalized_text for subject in subjects)


def _is_follow_up(question: str) -> bool:
    return bool(_FOLLOW_UP.search(question.lstrip(" \t\r\n\"'“‘([{《「『")))


def _extract_explicit_subjects(
    question: str, aliases: tuple[str, ...]
) -> tuple[tuple[str, ...], bool]:
    source_question = question.split("\n追问：", maxsplit=1)[0]
    subject_clause = _subject_clause(source_question)
    search_region = subject_clause if subject_clause else source_question
    matched = _matching_aliases(search_region, aliases)
    if matched:
        return matched, False

    if not subject_clause:
        return (), False
    subject_clause = _TRAILING_CONTEXT.sub("", subject_clause.strip(" \t\r\n？?，,。；;：:"))
    if not subject_clause or _is_generic_subject(subject_clause):
        return (), False
    # If the clause is a request sentence, its whole prefix is not a safe entity.
    # An unrecognized request is treated as unresolved instead of filtering on that text.
    if _REQUEST_CLAUSE.search(subject_clause):
        return (), True

    candidates = []
    for raw in _SUBJECT_SPLIT.split(subject_clause):
        candidate = _TRAILING_CONTEXT.sub("", raw.strip(" \t\r\n\"'“”‘’()（）[]【】"))
        if not candidate or _is_generic_subject(candidate):
            continue
        for prefix in _GENERIC_PREFIXES:
            if candidate.startswith(prefix):
                candidate = candidate[len(prefix) :]
                break
        if len(candidate) >= 2 and candidate not in candidates:
            candidates.append(candidate)
    return tuple(candidates), False


def _subject_clause(question: str) -> str:
    if "的" in question:
        return question.split("的", maxsplit=1)[0]
    english_subject = re.search(r"\bfor\s+([^?!.]+)", question, re.I)
    possessive_subject = re.search(r"\b([\w -]+)'s\b", question, re.I)
    return (
        english_subject.group(1)
        if english_subject
        else possessive_subject.group(1)
        if possessive_subject
        else ""
    )


def _matching_aliases(region: str, aliases: tuple[str, ...]) -> tuple[str, ...]:
    normalized_region = _normalize(region)
    matches = [alias for alias in aliases if _normalize(alias) in normalized_region]
    # Keep the most specific names when aliases overlap (for example a project and
    # the line that contains it), while preserving separate comparison subjects.
    maximal = [
        alias
        for alias in matches
        if not any(
            _normalize(alias) != _normalize(other) and _normalize(alias) in _normalize(other)
            for other in matches
        )
    ]
    return tuple(dict.fromkeys(maximal))


def _clean_aliases(values: Iterable[str]) -> tuple[str, ...]:
    aliases: list[str] = []
    for value in values:
        candidate = value.strip()
        if len(_normalize(candidate)) < 2 or _is_generic_subject(candidate):
            continue
        if candidate not in aliases:
            aliases.append(candidate)
    return tuple(sorted(aliases, key=lambda value: len(_normalize(value)), reverse=True))


def aliases_from_subject_text(text: str) -> tuple[str, ...]:
    """Extract short, explicit subject clauses from current corpus text."""
    aliases: list[str] = []
    for fragment in _QUESTION_SPLIT.split(text):
        for clause in re.split(r"[，,：:]", fragment):
            if "的" not in clause:
                continue
            subject = clause.split("的", maxsplit=1)[0].strip(" \t\r\n\"'“”‘’()（）[]【】")
            if not subject or _REQUEST_CLAUSE.search(subject) or _is_generic_subject(subject):
                continue
            if len(_normalize(subject)) <= 32 and subject not in aliases:
                aliases.append(subject)
    return tuple(aliases)


def _is_generic_subject(value: str) -> bool:
    normalized = _normalize(value)
    return normalized in {_normalize(item) for item in _GENERIC_SUBJECTS}


def _normalize(value: str) -> str:
    return re.sub(r"[^\w\u3400-\u9fff]+", "", value, flags=re.UNICODE).casefold()
