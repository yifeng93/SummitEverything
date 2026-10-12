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
_SUBJECT_REQUEST_PREFIX = re.compile(
    r"^(?:(?:麻烦(?:帮我)?|请问|请|我希望|我想(?:知道|问|了解)?|你能告诉我|您能告诉我|"
    r"帮我|先核对|核对|确认|查询|了解|能否|可否))+"
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
_COMPARISON_PREFIX = re.compile(
    r"^(?:(?:请|麻烦|帮我|我想|我希望)(?:比较|对比|对照|分析一下)?|比较|对比|对照|分析一下|(?:为|给|针对|关于))"
)
_TOPIC_CLASSES: dict[str, tuple[str, ...]] = {
    "budget": ("预算", "经费", "费用", "成本", "资金", "额度", "储备", "金额"),
    "schedule": (
        "排期",
        "时间",
        "启动",
        "开始",
        "截止",
        "期限",
        "日期",
        "进度",
        "什么时候",
        "何时",
        "日程",
    ),
    "storage": ("存储", "储存", "保管", "存放", "备份", "归档"),
    "owner": ("负责人", "联系人", "所有者", "责任人"),
}
_TOPIC_FILLER = re.compile(
    r"(?:分别|分别是多少|是什么|是谁|有什么|如何|怎么|多少|哪些|哪一个|哪项|规则|情况|信息|资料|内容|上限|是多少|吗|呢|知道|先|核对|确认|希望|比较|对比|汇总|现有|目前|当前|现行|最新|和|与|及|并|下一步|需要补什么|补什么|需要补充|还缺什么|方案|建议|？|\?|。|！|!)"
)
_TOPIC_REQUEST_SUFFIX = re.compile(r"(?:提出|制定|给出|说明|告诉|并列出|列出|再给|请|帮我).*")


@dataclass(frozen=True)
class RetrievalPlan:
    search_question: str
    explicit_subjects: tuple[str, ...]
    used_history_hint: bool
    unresolved_topic: bool = False
    dimensions: tuple[str, ...] = ()
    required_pairs: tuple[tuple[str, str], ...] = ()


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
    dimension_subjects = _dimension_subjects(current_subjects, aliases)

    if current_subjects or current_unresolved or not is_follow_up:
        return RetrievalPlan(
            normalized,
            current_subjects,
            False,
            unresolved_topic=current_unresolved,
            dimensions=query_dimensions(normalized, dimension_subjects),
            required_pairs=query_pairs(
                normalized,
                current_subjects,
                query_dimensions(normalized, dimension_subjects),
            ),
        )

    # Skip intervening pronoun-only questions, but never cross a complete question.
    for prior_question in reversed(previous_user_questions):
        prior = prior_question.strip()
        if not prior:
            continue
        prior_subjects, prior_unresolved = _extract_explicit_subjects(prior, aliases)
        if prior_subjects:
            prior_dimension_subjects = _dimension_subjects(prior_subjects, aliases)
            return RetrievalPlan(
                f"{prior}\n追问：{normalized}",
                prior_subjects,
                True,
                dimensions=query_dimensions(normalized, prior_dimension_subjects),
                required_pairs=query_pairs(
                    normalized,
                    prior_subjects,
                    query_dimensions(normalized, prior_dimension_subjects),
                ),
            )
        if _is_follow_up(prior) and not prior_unresolved:
            continue
        # An unresolved or subjectless complete question still starts a new topic.
        return RetrievalPlan(normalized, (), False, unresolved_topic=True)

    return RetrievalPlan(normalized, (), False, unresolved_topic=True)


def matches_explicit_subject(text: str, subjects: tuple[str, ...]) -> bool:
    """Require at least one explicitly named query subject in a candidate passage."""
    if not subjects:
        return True
    normalized_text = _normalize(text)
    return any(_normalize(subject) in normalized_text for subject in subjects)


def _dimension_subjects(subjects: tuple[str, ...], aliases: tuple[str, ...]) -> tuple[str, ...]:
    """Remove established object names but retain a lone unknown topic descriptor."""
    known = tuple(subject for subject in subjects if _matching_aliases(subject, aliases))
    if known:
        return subjects if len(subjects) > 1 else known
    return subjects if len(subjects) > 1 else ()


def _is_follow_up(question: str) -> bool:
    return bool(_FOLLOW_UP.search(question.lstrip(" \t\r\n\"'“‘([{《「『")))


def _extract_explicit_subjects(
    question: str, aliases: tuple[str, ...]
) -> tuple[tuple[str, ...], bool]:
    source_question = question.split("\n追问：", maxsplit=1)[0]
    subject_clause = _subject_clause(source_question)
    matched = _matching_aliases(question, aliases)
    if not subject_clause:
        return matched, False
    subject_clause = _TRAILING_CONTEXT.sub("", subject_clause.strip(" \t\r\n？?，,。；;：:"))
    if not subject_clause or _is_generic_subject(subject_clause):
        return matched, False
    # If the clause is a request sentence, its whole prefix is not a safe entity.
    # An unrecognized request is treated as unresolved instead of filtering on that text.
    cleaned_clause = _COMPARISON_PREFIX.sub("", subject_clause).strip()
    request_like = bool(_REQUEST_CLAUSE.search(subject_clause))
    candidates = []
    subject_regions = [cleaned_clause]
    if "的" not in source_question:
        topic_terms = sorted(
            {term for terms in _TOPIC_CLASSES.values() for term in terms},
            key=len,
            reverse=True,
        )
        topic_pattern = re.compile("|".join(re.escape(term) for term in topic_terms))
        previous_end = 0
        for marker in topic_pattern.finditer(source_question):
            if previous_end:
                between_topics = source_question[previous_end : marker.start()]
                fragments = _SUBJECT_SPLIT.split(between_topics)
                if len(fragments) > 1:
                    subject_regions.append(fragments[-1])
            previous_end = marker.end()
    previous_de = question.find("的")
    while previous_de >= 0:
        next_de = question.find("的", previous_de + 1)
        if next_de < 0:
            break
        between = question[previous_de + 1 : next_de]
        fragments = _SUBJECT_SPLIT.split(between)
        if len(fragments) > 1:
            subject_regions.append(fragments[-1])
        previous_de = next_de
    for region in subject_regions:
        for raw in _SUBJECT_SPLIT.split(region):
            candidate = _TRAILING_CONTEXT.sub("", raw.strip(" \t\r\n\"'“”‘’()（）[]【】"))
            candidate = _COMPARISON_PREFIX.sub("", candidate).strip()
            if not candidate or _is_generic_subject(candidate):
                continue
            normalized_candidate = _normalize(candidate)
            for alias in matched:
                normalized_candidate = normalized_candidate.replace(_normalize(alias), "")
            candidate = _SUBJECT_REQUEST_PREFIX.sub("", normalized_candidate).strip()
            candidate = _TOPIC_FILLER.sub("", candidate).strip()
            if _REQUEST_CLAUSE.search(candidate):
                continue
            if not candidate or _is_generic_subject(candidate):
                continue
            for prefix in _GENERIC_PREFIXES:
                if candidate.startswith(prefix):
                    candidate = candidate[len(prefix) :]
                    break
            if len(candidate) >= 2 and candidate not in candidates:
                candidates.append(candidate)
    # Matched corpus names and unmatched parallel names are both part of the
    # requested set; a hit cannot erase a second, unknown comparison subject.
    values = [*matched, *candidates]
    unresolved_request = request_like and not values and not query_dimensions(source_question)
    return tuple(dict.fromkeys(values)), unresolved_request


def query_dimensions(question: str, subjects: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Return compact semantic topic labels, using exact terms for unfamiliar topics."""
    normalized = _normalize(question)
    matched = [
        label
        for label, terms in _TOPIC_CLASSES.items()
        if any(_normalize(term) in normalized for term in terms)
    ]
    source_question = question.split("\n追问：", maxsplit=1)[-1]
    topic_phrase = (
        source_question.rsplit("的", maxsplit=1)[-1] if "的" in source_question else source_question
    )
    for subject in subjects:
        topic_phrase = topic_phrase.replace(subject, " ")
    topic_phrase = _COMPARISON_PREFIX.sub("", topic_phrase)
    topic_phrase = _TOPIC_REQUEST_SUFFIX.sub("", topic_phrase)
    if matched:
        specific = topic_phrase
        for terms in _TOPIC_CLASSES.values():
            for term in terms:
                specific = specific.replace(term, " ")
        specific = _TOPIC_FILLER.sub("", specific)
        specific = _normalize(specific)
        if _REQUEST_CLAUSE.search(specific):
            return tuple(matched)
        if len(specific) >= 2:
            return (f"{'+'.join(matched)}&term:{specific}",)
        return tuple(matched)
    # Unknown exact terms refine a recognized topic family (for example,
    # storage of a named object). Ordinary open questions such as “where is
    # it?” keep the existing ranked retrieval path instead of becoming an
    # accidental exact-keyword gate.
    return ()


def supported_dimensions(text: str, dimensions: tuple[str, ...]) -> tuple[str, ...]:
    """List only requested topics that this specific passage visibly supports."""
    normalized = _normalize(text)
    supported: list[str] = []
    for dimension in dimensions:
        found = all(_dimension_part_supported(normalized, part) for part in dimension.split("&"))
        if found:
            supported.append(dimension)
    return tuple(supported)


def query_pairs(
    question: str, subjects: tuple[str, ...], dimensions: tuple[str, ...]
) -> tuple[tuple[str, str], ...]:
    """Resolve explicitly paired subjects/topics, otherwise use the shared scope."""
    if not subjects:
        return tuple(("", dimension) for dimension in dimensions)
    if not dimensions:
        return tuple((subject, "") for subject in subjects)
    if len(subjects) < 2:
        return tuple((subjects[0], dimension) for dimension in dimensions)

    normalized = _normalize(question)
    assignments: dict[str, tuple[str, ...]] = {}
    for subject in subjects:
        needle = _normalize(subject)
        position = normalized.find(needle)
        if position < 0:
            continue
        next_positions = [
            normalized.find(_normalize(other), position + len(needle))
            for other in subjects
            if other != subject
        ]
        next_positions = [value for value in next_positions if value >= 0]
        end = min(next_positions) if next_positions else len(normalized)
        # Normalize indices are stable here because both subject and question
        # use the same normalization that removes only punctuation/spacing.
        span = normalized[position + len(needle) : end]
        found = tuple(
            dimension for dimension in dimensions if _dimension_mentioned(span, dimension)
        )
        if found:
            assignments[subject] = found
    if len(assignments) == len(subjects):
        return tuple(
            (subject, dimension) for subject in subjects for dimension in assignments[subject]
        )
    # “A 和 B 的预算、排期” asks the shared dimensions of both subjects.
    return tuple((subject, dimension) for subject in subjects for dimension in dimensions)


def _dimension_mentioned(text: str, dimension: str) -> bool:
    return all(_dimension_part_supported(text, part) for part in dimension.split("&"))


def _dimension_part_supported(normalized_text: str, part: str) -> bool:
    if part.startswith("term:"):
        return part[5:] in normalized_text
    labels = part.split("+")
    return all(
        any(_normalize(term) in normalized_text for term in _TOPIC_CLASSES.get(label, ()))
        for label in labels
    )


def _subject_clause(question: str) -> str:
    if "的" in question:
        return question.split("的", maxsplit=1)[0]
    english_subject = re.search(r"\bfor\s+([^?!.]+)", question, re.I)
    possessive_subject = re.search(r"\b([\w -]+)'s\b", question, re.I)
    if english_subject:
        return english_subject.group(1)
    if possessive_subject:
        return possessive_subject.group(1)
    # Natural Chinese often omits “的” in compact comparisons and plans.
    # Bound the candidate object region at the first recognizable topic or
    # request predicate, so the whole request sentence is never treated as an
    # entity name.
    prefix = _COMPARISON_PREFIX.sub("", question.strip())
    markers = [term for terms in _TOPIC_CLASSES.values() for term in terms if term in prefix]
    markers.extend(("制定", "提出", "给出", "下一步", "方案"))
    positions = [prefix.find(marker) for marker in markers if prefix.find(marker) >= 0]
    return prefix[: min(positions)].strip(" \t\r\n？?，,。；;：:") if positions else ""


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
