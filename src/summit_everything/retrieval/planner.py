"""Small, deterministic query hints for explicit subjects and short follow-ups."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

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
    r"(?:分别|分别是多少|是什么|是谁|有什么|如何|怎么|多少|哪些|哪一个|哪项|规则|情况|信息|资料|内容|上限|是多少|是|设备|年度|专项|工作|列出|缺失|吗|呢|知道|先|核对|确认|希望|比较|对比|汇总|现有|目前|当前|现行|最新|和|与|及|并|制定|提出|给出|下一步|需要补什么|补什么|需要补充|还缺什么|方案|建议|？|\?|。|！|!)"
)
_TOPIC_REQUEST_SUFFIX = re.compile(r"(?:提出|制定|给出|说明|告诉|并列出|列出|再给|请|帮我).*")
_TOPIC_PREFIX = re.compile(
    r"^(?:(?:麻烦(?:帮我)?|请问|请|我希望|我想(?:知道|问|了解)?|你能告诉我|您能告诉我|"
    r"帮我|先核对|核对|确认|查询|了解|能否|可否|比较|对比|对照|分析一下|为|给|针对|关于|"
    r"制定|提出|汇总|总结|查看|查一下|查|告诉我|说明一下|梳理|并)+)+"
)
_TOPIC_SUFFIX = re.compile(
    r"(?:(?:分别|是什么|是谁|有什么|怎么(?:安排|处理|办|做)?|如何|安排|办理|办法|方式|流程|手续|"
    r"规则|情况|信息|资料|内容|建议|方案|上限|多少|哪些|哪一个|哪项|吗|呢|吧|啊|一下|"
    r"再给简短结论|并汇总现有资料|并汇总|现有资料|简短结论|。|！|!|？|\?)+)$"
)
_ENTITY_SUFFIXES = ("项目", "计划", "工程", "专项", "工作坊", "课题", "产品")
_EXPLICIT_TOPIC_FORM = re.compile(r"(?:规则|办法|流程|手续|安排|方案|程序|制度|规范|要求|指南)")
_OPEN_FACT_QUESTION = re.compile(r"(?:哪里|哪儿|在哪|多少|什么时候|何时|几号|几点)")
_DATE_VALUE = re.compile(
    r"(?:[0-9一二三四五六七八九十]+年)?[0-9一二三四五六七八九十]+月"
    r"[0-9一二三四五六七八九十]+日"
)


@dataclass(frozen=True)
class RetrievalPlan:
    search_question: str
    explicit_subjects: tuple[str, ...]
    used_history_hint: bool
    unresolved_topic: bool = False
    dimensions: tuple[str, ...] = ()
    required_pairs: tuple[tuple[str, str], ...] = ()
    scope_kind: Literal["explicit_topic", "generic_plan", "open", "unresolved"] = "open"


def plan_retrieval(
    question: str,
    previous_user_questions: list[str],
    subject_aliases: Iterable[str] = (),
    *,
    object_aliases: Iterable[str] = (),
) -> RetrievalPlan:
    """Use only an explicit subject or the nearest bounded user-question topic.

    Prior assistant answers are never supplied. A complete user question is a topic
    boundary even when its subject is unknown or cannot be parsed confidently.
    """
    normalized = question.strip()
    aliases = _clean_aliases(subject_aliases)
    object_names = set(_clean_aliases(object_aliases))
    is_follow_up = _is_follow_up(normalized)
    current_subjects, current_unresolved = _extract_explicit_subjects(
        normalized, aliases, object_names
    )
    dimensions, required_pairs = query_scope(normalized, current_subjects)
    current_scope_kind = _scope_kind(normalized, dimensions, current_unresolved)

    if current_subjects or current_unresolved or not is_follow_up:
        return RetrievalPlan(
            normalized,
            current_subjects,
            False,
            unresolved_topic=current_unresolved,
            dimensions=dimensions,
            required_pairs=required_pairs,
            scope_kind=current_scope_kind,
        )

    # Skip intervening pronoun-only questions, but never cross a complete question.
    for prior_question in reversed(previous_user_questions):
        prior = prior_question.strip()
        if not prior:
            continue
        prior_subjects, prior_unresolved = _extract_explicit_subjects(prior, aliases, object_names)
        if prior_subjects:
            followup_dimensions, followup_pairs = query_scope(normalized, prior_subjects)
            return RetrievalPlan(
                f"{prior}\n追问：{normalized}",
                prior_subjects,
                True,
                dimensions=followup_dimensions,
                required_pairs=followup_pairs,
                scope_kind=_scope_kind(normalized, followup_dimensions, False),
            )
        if _is_follow_up(prior) and not prior_unresolved:
            continue
        # An unresolved or subjectless complete question still starts a new topic.
        return RetrievalPlan(normalized, (), False, unresolved_topic=True, scope_kind="unresolved")

    return RetrievalPlan(normalized, (), False, unresolved_topic=True, scope_kind="unresolved")


def matches_explicit_subject(text: str, subjects: tuple[str, ...]) -> bool:
    """Require at least one explicitly named query subject in a candidate passage."""
    if not subjects:
        return True
    normalized_text = _normalize(text)
    return any(_normalize(subject) in normalized_text for subject in subjects)


def _scope_kind(
    question: str,
    dimensions: tuple[str, ...],
    unresolved: bool,
) -> Literal["explicit_topic", "generic_plan", "open", "unresolved"]:
    if unresolved:
        return "unresolved"
    if dimensions:
        return "explicit_topic"
    if re.search(r"(?:下一步|工作方案|方案建议|制定方案)", question):
        return "generic_plan"
    return "open"


def _is_follow_up(question: str) -> bool:
    return bool(_FOLLOW_UP.search(question.lstrip(" \t\r\n\"'“‘([{《「『")))


def _extract_explicit_subjects(
    question: str, aliases: tuple[str, ...], object_aliases: set[str] | None = None
) -> tuple[tuple[str, ...], bool]:
    object_aliases = object_aliases or set()
    source_question = question.split("\n追问：", maxsplit=1)[0]
    subject_clause = _subject_clause(source_question, aliases)
    all_matches = _matching_aliases(question, aliases)
    if subject_clause:
        matched = tuple(
            alias
            for alias in all_matches
            if _alias_has_entity_role(alias) or alias in object_aliases
        )
    else:
        matched = tuple(
            alias
            for alias in all_matches
            if _alias_is_subject_in_question(source_question, alias)
            or (alias in object_aliases and _alias_has_topic_after(source_question, alias))
        )
    entity_mentions = _entity_mentions(source_question, matched)
    subject_clause = _TRAILING_CONTEXT.sub("", subject_clause.strip(" \t\r\n？?，,。；;：:"))
    # If the clause is a request sentence, its whole prefix is not a safe entity.
    # An unrecognized request is treated as unresolved instead of filtering on that text.
    cleaned_clause = _COMPARISON_PREFIX.sub("", subject_clause).strip()
    request_like = bool(subject_clause and _REQUEST_CLAUSE.search(subject_clause))
    candidates = []
    subject_regions = [cleaned_clause] if cleaned_clause else []
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
            candidate = _trim_topic_after_entity_suffix(candidate)
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
    entity_keys = {_normalize(value) for value in entity_mentions}
    filtered_candidates = [
        candidate
        for candidate in candidates
        if not any(
            key != _normalize(candidate) and key in _normalize(candidate) for key in entity_keys
        )
    ]
    values = [*matched, *entity_mentions, *filtered_candidates]
    unresolved_request = (
        request_like and not values and not query_dimensions(source_question, tuple(values))
    )
    return tuple(dict.fromkeys(values)), unresolved_request


def query_dimensions(question: str, subjects: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Return an explicit family or exact topic after removing object spans."""
    topic_phrase = _topic_phrase(question, subjects)
    normalized = _normalize(topic_phrase)
    matched = [
        label
        for label, terms in _TOPIC_CLASSES.items()
        if any(_normalize(term) in normalized for term in terms)
    ]
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
    exact = _normalize(topic_phrase)
    if len(exact) >= 2:
        if not _EXPLICIT_TOPIC_FORM.search(question) and (
            _OPEN_FACT_QUESTION.search(question) or _DATE_VALUE.search(question)
        ):
            return ()
        return (f"term:{exact}",)
    # Empty topic phrases are genuinely open questions or generic plans; an
    # unfamiliar but explicit noun phrase remains an exact local scope.
    return ()


def query_scope(
    question: str, subjects: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
    """Resolve local subject/topic pairs first; dimensions are their union."""
    if not subjects:
        dimensions = _topic_dimensions(question)
        if not dimensions:
            dimensions = query_dimensions(question)
        return dimensions, tuple(("", dimension) for dimension in dimensions)

    local = _local_subject_topics(question, subjects)
    if not any(local.values()):
        dimensions = query_dimensions(question, subjects)
        pairs = tuple((subject, dimension) for subject in subjects for dimension in dimensions)
        if not dimensions:
            pairs = tuple((subject, "") for subject in subjects)
        return dimensions, pairs

    # A topic after the last subject is shared only when every preceding
    # subject span contains connectors but no local topic of its own.
    last_subject = max(
        subjects,
        key=lambda subject: question.find(subject) if question.find(subject) >= 0 else -1,
    )
    earlier = [subject for subject in subjects if subject != last_subject]
    if local[last_subject] and all(not local[subject] for subject in earlier):
        pairs = tuple(
            (subject, dimension) for subject in subjects for dimension in local[last_subject]
        )
    else:
        pairs = tuple(
            (subject, dimension) for subject in subjects for dimension in (local[subject] or ("",))
        )
    dimensions = tuple(dict.fromkeys(dimension for _, dimension in pairs if dimension))
    return dimensions, pairs


def _local_subject_topics(question: str, subjects: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    occurrences: list[tuple[int, int, str]] = []
    for subject in subjects:
        start = question.find(subject)
        if start >= 0:
            occurrences.append((start, start + len(subject), subject))
    occurrences.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    # If a long alias and its short stem overlap at the same span, retain only
    # the maximal source span. Keep distinct aliases at distinct positions.
    selected: list[tuple[int, int, str]] = []
    for occurrence in occurrences:
        if selected and occurrence[0] < selected[-1][1]:
            continue
        selected.append(occurrence)

    topics: dict[str, tuple[str, ...]] = {subject: () for subject in subjects}
    for index, (_start, end, subject) in enumerate(selected):
        next_start = selected[index + 1][0] if index + 1 < len(selected) else len(question)
        span = question[end:next_start]
        topics[subject] = _topic_dimensions(span)
    return topics


def _topic_dimensions(span: str) -> tuple[str, ...]:
    normalized_span = span.strip(" \t\r\n的和与及、,，:：")
    if not normalized_span:
        return ()

    # Split only when each side independently expresses a topic. This keeps
    # modifiers such as “彩色牙刷储存规则” as one exact scope.
    fragments = re.split(r"(?:和|与|及|、|,|，)", normalized_span)
    if len(fragments) > 1:
        fragment_dimensions = [_single_topic_dimension(fragment) for fragment in fragments]
        if all(fragment_dimensions):
            return tuple(
                dict.fromkeys(dimension for values in fragment_dimensions for dimension in values)
            )
    return _single_topic_dimension(normalized_span)


def _single_topic_dimension(span: str) -> tuple[str, ...]:
    cleaned = _TOPIC_PREFIX.sub("", span.strip())
    cleaned = _TOPIC_SUFFIX.sub("", cleaned)
    dimensions = query_dimensions(cleaned)
    return dimensions


def _topic_phrase(question: str, subjects: tuple[str, ...]) -> str:
    source_question = question.split("\n追问：", maxsplit=1)[-1]
    masked = source_question
    for subject in sorted(subjects, key=len, reverse=True):
        masked = re.sub(re.escape(subject), " ", masked, flags=re.IGNORECASE)
    masked = masked.replace("的", " ")
    topic = _TOPIC_PREFIX.sub("", masked.strip())
    previous = None
    while topic != previous:
        previous = topic
        topic = _TOPIC_SUFFIX.sub("", topic.strip())
        topic = _TOPIC_FILLER.sub("", topic)
    return topic


def _alias_is_subject_in_question(question: str, alias: str) -> bool:
    normalized_question = _normalize(question)
    normalized_alias = _normalize(alias)
    position = normalized_question.find(normalized_alias)
    if position < 0:
        return False
    if "的" in question:
        before_de = _normalize(question.split("的", maxsplit=1)[0])
        if normalized_alias in before_de and _alias_has_entity_role(alias):
            return True
    if _alias_has_entity_role(alias):
        return True
    tail = normalized_question[position + len(normalized_alias) :]
    if any(_normalize(term) in tail for terms in _TOPIC_CLASSES.values() for term in terms):
        return True
    cleaned_tail = _TOPIC_SUFFIX.sub("", tail)
    cleaned_tail = _TOPIC_FILLER.sub("", cleaned_tail)
    return len(cleaned_tail) >= 2 and not _topic_phrase(tail, ())


def _alias_has_entity_role(alias: str) -> bool:
    normalized_alias = _normalize(alias)
    return any(_normalize(suffix) in normalized_alias for suffix in _ENTITY_SUFFIXES)


def _entity_mentions(question: str, known_subjects: tuple[str, ...]) -> tuple[str, ...]:
    """Find source-local names ending in a known entity noun, independent of order."""
    pattern = re.compile(r"[\u3400-\u9fffA-Za-z0-9]{1,16}?(?:项目|计划|工程|专项|工作坊|课题|产品)")
    stripped = _TOPIC_PREFIX.sub("", question.strip())
    for subject in sorted(known_subjects, key=len, reverse=True):
        stripped = stripped.replace(subject, " " * len(subject))
    values: list[str] = []
    for region in re.split(r"(?:和|与|及|、|,|，|。|？|\?|；|;)", stripped):
        region = _COMPARISON_PREFIX.sub("", region).strip()
        for match in pattern.finditer(region):
            candidate = match.group().strip()
            if candidate and not _is_generic_subject(candidate):
                values.append(candidate)
    return tuple(values)


def _trim_topic_after_entity_suffix(candidate: str) -> str:
    """Separate a recognized topic only when an entity suffix closes the name."""
    for terms in _TOPIC_CLASSES.values():
        for term in sorted(terms, key=len, reverse=True):
            position = candidate.find(term)
            if position <= 0:
                continue
            prefix = candidate[:position]
            if any(prefix.endswith(suffix) for suffix in _ENTITY_SUFFIXES):
                return prefix
    return candidate


def _alias_has_topic_after(question: str, alias: str) -> bool:
    normalized_question = _normalize(question)
    normalized_alias = _normalize(alias)
    position = normalized_question.find(normalized_alias)
    if position < 0:
        return False
    topic_tail = normalized_question[position + len(normalized_alias) :]
    return bool(_topic_phrase(topic_tail, ()))


def supported_dimensions(text: str, dimensions: tuple[str, ...]) -> tuple[str, ...]:
    """List only requested topics that this specific passage visibly supports."""
    normalized = _normalize(text)
    supported: list[str] = []
    for dimension in dimensions:
        found = all(_dimension_part_supported(normalized, part) for part in dimension.split("&"))
        if found:
            supported.append(dimension)
    return tuple(supported)


def _dimension_part_supported(normalized_text: str, part: str) -> bool:
    if part.startswith("term:"):
        return part[5:] in normalized_text
    labels = part.split("+")
    return all(
        any(_normalize(term) in normalized_text for term in _TOPIC_CLASSES.get(label, ()))
        for label in labels
    )


def _subject_clause(question: str, aliases: tuple[str, ...] = ()) -> str:
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
    scan_question = question
    for alias in sorted(aliases, key=len, reverse=True):
        scan_question = re.sub(
            re.escape(alias),
            lambda match: " " * len(match.group(0)),
            scan_question,
        )
    prefix = _COMPARISON_PREFIX.sub("", scan_question.strip())
    markers = [term for terms in _TOPIC_CLASSES.values() for term in terms if term in prefix]
    markers.extend(("制定", "提出", "给出", "下一步", "方案"))
    positions = [prefix.find(marker) for marker in markers if prefix.find(marker) >= 0]
    if not positions:
        return ""
    # Reapply the same leading comparison wrapper to retain source offsets.
    raw_prefix = question.strip()
    wrapper = _COMPARISON_PREFIX.match(raw_prefix)
    offset = wrapper.end() if wrapper else 0
    return question[offset : offset + min(positions)].strip(" \t\r\n？?，,。；;：:")


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
    topical_terms = {_normalize(term) for terms in _TOPIC_CLASSES.values() for term in terms}
    for value in values:
        candidate = value.strip()
        normalized = _normalize(candidate)
        if len(normalized) < 2 or _is_generic_subject(candidate) or normalized in topical_terms:
            continue
        # A page title like “青岚计划预算” can hint at its object, while the
        # trailing family word remains part of the question topic.
        for terms in _TOPIC_CLASSES.values():
            for term in sorted(terms, key=len, reverse=True):
                if candidate.endswith(term):
                    stem = candidate[: -len(term)].strip()
                    if len(_normalize(stem)) >= 2 and any(
                        _normalize(suffix) in _normalize(stem) for suffix in _ENTITY_SUFFIXES
                    ):
                        candidate = stem
                        normalized = _normalize(candidate)
                    break
        if candidate not in aliases:
            aliases.append(candidate)
        for suffix in ("项目", "计划", "工程"):
            if candidate.endswith(suffix):
                stem = candidate[: -len(suffix)].strip()
                if (
                    len(_normalize(stem)) >= 2
                    and not _is_generic_subject(stem)
                    and stem not in aliases
                ):
                    aliases.append(stem)
                break
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
    topical_terms = {_normalize(term) for terms in _TOPIC_CLASSES.values() for term in terms}
    return normalized in {_normalize(item) for item in _GENERIC_SUBJECTS} | topical_terms


def _normalize(value: str) -> str:
    return re.sub(r"[^\w\u3400-\u9fff]+", "", value, flags=re.UNICODE).casefold()
