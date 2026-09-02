from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.norm_priority import (
    Decision,
    PriorityRule,
    denied_record_ids,
    evaluate_policy,
)
from mindsetbench.verification.registry import register

Records = dict[str, frozenset[str]]

ELIGIBLE_LEFT = "eligible_left"
ELIGIBLE_RIGHT = "eligible_right"
ORDINARY_BAR = "ordinary_bar"
EXCEPTION_LEFT = "exception_left"
EXCEPTION_RIGHT = "exception_right"
ABSOLUTE_BAR = "absolute_bar"
TOP_EXCEPTION = "top_exception"


def _rule(
    name: str,
    conditions: set[str],
    decision: Decision,
    priority: int,
) -> PriorityRule:
    return PriorityRule(name, frozenset(conditions), decision, priority)


def _standard_rules(*, exception_priority: int = 3) -> tuple[PriorityRule, ...]:
    return (
        _rule(
            "baseline-eligibility",
            {ELIGIBLE_LEFT, ELIGIBLE_RIGHT},
            Decision.ALLOW,
            1,
        ),
        _rule("ordinary-bar", {ORDINARY_BAR}, Decision.DENY, 2),
        _rule(
            "paired-exception",
            {EXCEPTION_LEFT, EXCEPTION_RIGHT},
            Decision.ALLOW,
            exception_priority,
        ),
        _rule("absolute-bar", {ABSOLUTE_BAR}, Decision.DENY, 4),
    )


def _records(*rows: tuple[str, set[str]]) -> Records:
    return {record_id: frozenset(facts) for record_id, facts in rows}


SOURCE_ALIASES = {
    "正式成员": ELIGIBLE_LEFT,
    "任务已登记": ELIGIBLE_RIGHT,
    "事故审查中": ORDINARY_BAR,
    "安全主管书面批准": EXCEPTION_LEFT,
    "独立复核完成": EXCEPTION_RIGHT,
    "法律保全中": ABSOLUTE_BAR,
}


def _source_records() -> Records:
    return _records(
        ("T1", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT}),
        ("T2", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT, ORDINARY_BAR}),
        (
            "T3",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
            },
        ),
        (
            "T4",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
                ABSOLUTE_BAR,
            },
        ),
        ("T5", {ELIGIBLE_LEFT}),
    )


SOURCE_REQUIRED_PHRASES = (
    "未被条款准入的请求一律拒绝",
    "事故审查条款优先于成员准入条款",
    "双重批准例外优先于事故审查条款",
    "法律保全条款优先于其他全部条款",
)


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


def _result(case: Case, checks: list[VerificationCheck]) -> VerificationResult:
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


def _parse_records(problem: str, aliases: Mapping[str, str]) -> Records:
    records: Records = {}
    for record_id, raw_facts in re.findall(r"([A-Z]\d*)【([^】]+)】", problem):
        if record_id in records:
            raise ValueError(f"duplicate record id {record_id}")
        normalized: set[str] = set()
        for raw_fact in raw_facts.split("、"):
            fact = raw_fact.strip()
            try:
                normalized.add(aliases[fact])
            except KeyError as exc:
                raise ValueError(f"unknown fact {fact!r} in {record_id}") from exc
        records[record_id] = frozenset(normalized)
    if not records:
        raise ValueError("no bracketed records found")
    return records


def _parse_for_check(problem: str, aliases: Mapping[str, str]) -> Records | str:
    try:
        return _parse_records(problem, aliases)
    except ValueError as exc:
        return f"parse error: {exc}"


def _contains_all(text: str, phrases: Sequence[str]) -> bool:
    return all(phrase in text for phrase in phrases)


def _source_checks(case: Case) -> list[VerificationCheck]:
    records = _source_records()
    denied = denied_record_ids(records, _standard_rules())
    return [
        _check(
            "source-text-records",
            _parse_for_check(case.source.problem, SOURCE_ALIASES),
            records,
        ),
        _check(
            "source-text-priority-clauses",
            _contains_all(case.source.problem, SOURCE_REQUIRED_PHRASES),
            True,
        ),
        _check("source-policy-denials", denied, ["T2", "T4", "T5"]),
        _check("stored-source", case.source.answer, ";".join(denied)),
    ]


def _verify_policy_case(
    case: Case,
    *,
    aliases: Mapping[str, str],
    records: Records,
    target_rules: Sequence[PriorityRule],
    lure_rules: Sequence[PriorityRule],
    required_phrases: Sequence[str],
    expected_target: Sequence[str],
    expected_lure: Sequence[str],
) -> VerificationResult:
    target = denied_record_ids(records, target_rules)
    lure = denied_record_ids(records, lure_rules)
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None
    checks = _source_checks(case)
    checks.extend(
        [
            _check(
                "target-text-records",
                _parse_for_check(case.target.problem, aliases),
                records,
            ),
            _check(
                "target-text-policy-clauses",
                _contains_all(case.target.problem, required_phrases),
                True,
            ),
            _check("policy-denials", target, list(expected_target)),
            _check("negative-control-denials", lure, list(expected_lure)),
            _check("stored-target", case.target.answer.legacy_value(), ";".join(target)),
            _check("stored-lure", case.lure.answer.legacy_value(), ";".join(lure)),
            _check(
                "copy-equals-lure",
                case.copy_probe.answer.legacy_value(),
                case.lure.answer.legacy_value(),
            ),
            _check(
                "copy-differs-from-target",
                case.copy_probe.answer != case.target.answer,
                True,
            ),
        ]
    )
    return _result(case, checks)


@register("HSS-P4-NORM-PRECEDENT-L0-01")
def verify_hss_p4_norm_precedent_l0_01(case: Case) -> VerificationResult:
    aliases = {
        "正式成员": ELIGIBLE_LEFT,
        "任务已登记": ELIGIBLE_RIGHT,
        "事故审查中": ORDINARY_BAR,
    }
    records = _records(
        ("A", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT}),
        ("B", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT, ORDINARY_BAR}),
        ("C", {ELIGIBLE_LEFT}),
    )
    target_rules = _standard_rules()[:2]
    lure_rules = (
        _rule("baseline-eligibility", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT}, Decision.ALLOW, 3),
        _rule("ordinary-bar", {ORDINARY_BAR}, Decision.DENY, 2),
    )
    return _verify_policy_case(
        case,
        aliases=aliases,
        records=records,
        target_rules=target_rules,
        lure_rules=lure_rules,
        required_phrases=(
            "未被准入的请求默认拒绝",
            "事故审查条款优先于成员准入条款",
        ),
        expected_target=("B", "C"),
        expected_lure=("C",),
    )


@register("HSS-P4-NORM-PRECEDENT-L1-01")
def verify_hss_p4_norm_precedent_l1_01(case: Case) -> VerificationResult:
    records = _records(
        ("P1", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT}),
        ("P2", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT, ORDINARY_BAR}),
        (
            "P3",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
            },
        ),
        (
            "P4",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
                ABSOLUTE_BAR,
            },
        ),
        ("P5", {ELIGIBLE_LEFT}),
    )
    return _verify_policy_case(
        case,
        aliases=SOURCE_ALIASES,
        records=records,
        target_rules=_standard_rules(),
        lure_rules=_standard_rules(exception_priority=5),
        required_phrases=SOURCE_REQUIRED_PHRASES,
        expected_target=("P2", "P4", "P5"),
        expected_lure=("P2", "P5"),
    )


MUSEUM_ALIASES = {
    "已编目藏品": ELIGIBLE_LEFT,
    "保存方案完备": ELIGIBLE_RIGHT,
    "来源权属争议": ORDINARY_BAR,
    "返还委员会建议": EXCEPTION_LEFT,
    "请求方书面同意": EXCEPTION_RIGHT,
    "法院保全令": ABSOLUTE_BAR,
}


@register("HSS-P4-NORM-PRECEDENT-L2-01")
def verify_hss_p4_norm_precedent_l2_01(case: Case) -> VerificationResult:
    records = _records(
        ("M1", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT}),
        ("M2", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT, ORDINARY_BAR}),
        (
            "M3",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
            },
        ),
        (
            "M4",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
                ABSOLUTE_BAR,
            },
        ),
        ("M5", {ELIGIBLE_LEFT}),
        (
            "M6",
            {ELIGIBLE_LEFT, ELIGIBLE_RIGHT, ORDINARY_BAR, EXCEPTION_LEFT},
        ),
    )
    return _verify_policy_case(
        case,
        aliases=MUSEUM_ALIASES,
        records=records,
        target_rules=_standard_rules(),
        lure_rules=_standard_rules(exception_priority=5),
        required_phrases=(
            "未满足任何出借条款时默认不出借",
            "权属争议条款优先于常规出借条款",
            "双方完备的返还审查例外优先于权属争议条款",
            "法院保全令优先于其他全部条款",
        ),
        expected_target=("M2", "M4", "M5", "M6"),
        expected_lure=("M2", "M5", "M6"),
    )


LABOR_ALIASES = {
    "按期提出": ELIGIBLE_LEFT,
    "具备申诉资格": ELIGIBLE_RIGHT,
    "涉及保密人事材料": ORDINARY_BAR,
    "工会共同签署": EXCEPTION_LEFT,
    "劳动者明示同意": EXCEPTION_RIGHT,
    "法定期限届满": ABSOLUTE_BAR,
}


@register("HSS-P4-NORM-PRECEDENT-L3-01")
def verify_hss_p4_norm_precedent_l3_01(case: Case) -> VerificationResult:
    records = _records(
        ("N1", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT}),
        ("N2", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT, ORDINARY_BAR}),
        (
            "N3",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
            },
        ),
        (
            "N4",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
                ABSOLUTE_BAR,
            },
        ),
        ("N5", {ELIGIBLE_RIGHT}),
        (
            "N6",
            {ELIGIBLE_LEFT, ELIGIBLE_RIGHT, ORDINARY_BAR, EXCEPTION_LEFT},
        ),
        ("N7", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT, ABSOLUTE_BAR}),
        (
            "N8",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
            },
        ),
    )
    return _verify_policy_case(
        case,
        aliases=LABOR_ALIASES,
        records=records,
        target_rules=_standard_rules(),
        lure_rules=_standard_rules(exception_priority=5),
        required_phrases=(
            "书记员将未获受理依据的申请登记为不受理",
            "保密条款压过通常的受理资格",
            "工会共同签署且劳动者明示同意时可以克服保密条款",
            "法定期限届满仍然终局阻却受理",
        ),
        expected_target=("N2", "N4", "N5", "N6", "N7"),
        expected_lure=("N2", "N5", "N6", "N7"),
    )


ARCHIVE_ALIASES = {
    "申请人具备研究资质": ELIGIBLE_LEFT,
    "材料已编目": ELIGIBLE_RIGHT,
    "存在现实安全风险": ORDINARY_BAR,
    "公益复核通过": EXCEPTION_LEFT,
    "监察员背书": EXCEPTION_RIGHT,
    "捐赠契约封存": ABSOLUTE_BAR,
    "法院解密令": TOP_EXCEPTION,
}


def _archive_rules(*, include_court_exception: bool) -> tuple[PriorityRule, ...]:
    rules = list(_standard_rules())
    if include_court_exception:
        rules.append(
            _rule(
                "court-declassification",
                {ABSOLUTE_BAR, TOP_EXCEPTION},
                Decision.ALLOW,
                5,
            )
        )
    return tuple(rules)


@register("HSS-P4-NORM-PRECEDENT-L4-01")
def verify_hss_p4_norm_precedent_l4_01(case: Case) -> VerificationResult:
    records = _records(
        ("U1", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT}),
        ("U2", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT, ORDINARY_BAR}),
        (
            "U3",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
            },
        ),
        (
            "U4",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
                ABSOLUTE_BAR,
            },
        ),
        (
            "U5",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
                ABSOLUTE_BAR,
                TOP_EXCEPTION,
            },
        ),
        ("U6", {ELIGIBLE_LEFT}),
        ("U7", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT, ABSOLUTE_BAR}),
        (
            "U8",
            {ELIGIBLE_LEFT, ELIGIBLE_RIGHT, ORDINARY_BAR, TOP_EXCEPTION},
        ),
    )
    result = _verify_policy_case(
        case,
        aliases=ARCHIVE_ALIASES,
        records=records,
        target_rules=_archive_rules(include_court_exception=True),
        lure_rules=_archive_rules(include_court_exception=False),
        required_phrases=(
            "先例甲",
            "先例乙",
            "先例丙",
            "先例丁",
            "先例戊",
            "法院命令改变了旧有的终局封存关系",
        ),
        expected_target=("U2", "U4", "U6", "U7", "U8"),
        expected_lure=("U2", "U4", "U5", "U6", "U7", "U8"),
    )

    precedent_records = _records(
        ("A", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT}),
        ("B", {ELIGIBLE_LEFT, ELIGIBLE_RIGHT, ORDINARY_BAR}),
        (
            "C",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
            },
        ),
        (
            "D",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
                ABSOLUTE_BAR,
            },
        ),
        (
            "E",
            {
                ELIGIBLE_LEFT,
                ELIGIBLE_RIGHT,
                ORDINARY_BAR,
                EXCEPTION_LEFT,
                EXCEPTION_RIGHT,
                ABSOLUTE_BAR,
                TOP_EXCEPTION,
            },
        ),
    )
    precedent_decisions = {
        record_id: decision.decision.value
        for record_id, decision in evaluate_policy(
            precedent_records,
            _archive_rules(include_court_exception=True),
        ).items()
    }
    result.checks.extend(
        [
            _check(
                "precedents-recover-priority-chain",
                precedent_decisions,
                {"A": "allow", "B": "deny", "C": "allow", "D": "deny", "E": "allow"},
            ),
            _check("target-omits-numeric-priorities", "优先级" not in case.target.problem, True),
        ]
    )
    return result
