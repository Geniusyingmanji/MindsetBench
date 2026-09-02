from __future__ import annotations

import re
from collections.abc import Iterable

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

Rule = tuple[frozenset[str], str]
Records = dict[str, frozenset[str]]


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


def _result(case: Case, checks: list[VerificationCheck]) -> VerificationResult:
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


def _gold(case: Case) -> str:
    return case.target.answer.legacy_value()


def _lure(case: Case) -> str:
    assert case.lure and case.lure.answer
    return case.lure.answer.legacy_value()


def _copy(case: Case) -> str:
    assert case.copy_probe
    return case.copy_probe.answer.legacy_value()


def _least_fixed_point(initial: frozenset[str], rules: Iterable[Rule]) -> frozenset[str]:
    facts = set(initial)
    normalized_rules = tuple(rules)
    while True:
        additions = {
            consequent
            for antecedents, consequent in normalized_rules
            if antecedents <= facts and consequent not in facts
        }
        if not additions:
            return frozenset(facts)
        facts.update(additions)


def _initial_fact_one_pass(initial: frozenset[str], rules: Iterable[Rule]) -> frozenset[str]:
    additions = {consequent for antecedents, consequent in rules if antecedents <= initial}
    return initial | additions


def _general_violation(facts: frozenset[str]) -> bool:
    exception = {"mercy", "sponsor"} <= facts
    return "route" in facts and "authorized" not in facts and not exception


def _priority_violation(facts: frozenset[str]) -> bool:
    return "volatile" in facts and "neutralized" not in facts


def _violations(records: Records, rules: list[Rule], *, one_pass: bool = False) -> list[str]:
    closure = _initial_fact_one_pass if one_pass else _least_fixed_point
    return [
        record_id
        for record_id, initial in records.items()
        if (_general_violation(facts := closure(initial, rules)) or _priority_violation(facts))
    ]


def _rules(*, include_stable_to_cleared: bool = True) -> list[Rule]:
    rules: list[Rule] = [
        (frozenset({"kiln", "sealed"}), "stable"),
        (frozenset({"silver"}), "cleared"),
        (frozenset({"cleared", "beacon"}), "priority"),
        (frozenset({"priority"}), "authorized"),
        (frozenset({"stable", "antidote"}), "neutralized"),
    ]
    if include_stable_to_cleared:
        rules.insert(1, (frozenset({"stable"}), "cleared"))
    return rules


def _verify_labels(
    case: Case,
    *,
    records: Records,
    rules: list[Rule],
    expected: list[str],
    expected_one_pass: list[str],
) -> VerificationResult:
    target = _violations(records, rules)
    lure = _violations(records, rules, one_pass=True)
    return _result(
        case,
        [
            _check("fixed-point-violations", target, expected),
            _check("initial-fact-one-pass-violations", lure, expected_one_pass),
            _check("stored-target", _gold(case), ";".join(target)),
            _check("stored-lure", _lure(case), ";".join(lure)),
            _check("copy-equals-lure", _copy(case), _lure(case)),
            _check("copy-differs-from-target", _copy(case) != _gold(case), True),
        ],
    )


@register("FORMAL-P4-CLOSURE-L0-01")
def verify_formal_p4_closure_l0_01(case: Case) -> VerificationResult:
    records = {
        "A": frozenset({"route", "kiln", "sealed"}),
        "B": frozenset({"route", "kiln"}),
    }
    rules = [
        (frozenset({"kiln", "sealed"}), "stable"),
        (frozenset({"stable"}), "authorized"),
    ]
    return _verify_labels(
        case,
        records=records,
        rules=rules,
        expected=["B"],
        expected_one_pass=["A", "B"],
    )


@register("FORMAL-P4-CLOSURE-L1-01")
def verify_formal_p4_closure_l1_01(case: Case) -> VerificationResult:
    records = {
        "P1": frozenset({"route", "kiln", "sealed", "beacon"}),
        "P2": frozenset({"route", "kiln", "sealed"}),
        "P3": frozenset({"route", "silver", "beacon"}),
        "P4": frozenset({"kiln", "sealed", "beacon"}),
    }
    rules = [
        (frozenset({"kiln", "sealed"}), "stable"),
        (frozenset({"stable"}), "cleared"),
        (frozenset({"silver"}), "cleared"),
        (frozenset({"cleared", "beacon"}), "authorized"),
    ]
    return _verify_labels(
        case,
        records=records,
        rules=rules,
        expected=["P2"],
        expected_one_pass=["P1", "P2", "P3"],
    )


def _source_records() -> Records:
    return {
        "S1": frozenset({"route", "kiln", "sealed", "beacon"}),
        "S2": frozenset({"route", "silver", "beacon"}),
        "S3": frozenset({"route", "kiln", "sealed"}),
        "S4": frozenset({"route", "mercy", "sponsor"}),
        "S5": frozenset({"route", "mercy"}),
        "S6": frozenset({"volatile", "kiln", "sealed", "antidote"}),
        "S7": frozenset({"volatile", "kiln", "sealed"}),
        "S8": frozenset(
            {"route", "volatile", "kiln", "sealed", "beacon", "antidote"}
        ),
        "S9": frozenset({"route", "volatile", "silver", "beacon"}),
        "S10": frozenset({"volatile", "kiln", "sealed", "antidote"}),
        "S11": frozenset({"route", "kiln", "sealed", "beacon", "mercy"}),
        "S12": frozenset({"route", "kiln", "sealed", "beacon", "silver"}),
    }


@register("FORMAL-P4-CLOSURE-L2-01")
def verify_formal_p4_closure_l2_01(case: Case) -> VerificationResult:
    records = {
        f"C{index}": facts
        for index, facts in enumerate(_source_records().values(), start=1)
        if index <= 7
    }
    return _verify_labels(
        case,
        records=records,
        rules=_rules(),
        expected=["C3", "C5", "C7"],
        expected_one_pass=["C1", "C2", "C3", "C5", "C6", "C7"],
    )


PROFILE_TO_TARGET = {
    "S1": "Q7",
    "S2": "Q2",
    "S3": "Q11",
    "S4": "Q5",
    "S5": "Q1",
    "S6": "Q9",
    "S7": "Q4",
    "S8": "Q12",
    "S9": "Q6",
    "S10": "Q3",
    "S11": "Q10",
    "S12": "Q8",
}
TARGET_WEIGHTS = {
    "Q7": 41,
    "Q2": 73,
    "Q11": 89,
    "Q5": 107,
    "Q1": 131,
    "Q9": 151,
    "Q4": 173,
    "Q12": 197,
    "Q6": 211,
    "Q3": 233,
    "Q10": 257,
    "Q8": 281,
}
TARGET_TO_INTERNAL = {
    "dispatch": "route",
    "ore": "kiln",
    "latched": "sealed",
    "signal": "beacon",
    "opal": "silver",
    "aid": "mercy",
    "seal": "sponsor",
    "reactive": "volatile",
    "remedy": "antidote",
    "balanced": "stable",
    "screened": "cleared",
    "urgent": "priority",
    "licensed": "authorized",
    "quenched": "neutralized",
}


def _target_records() -> Records:
    source = _source_records()
    return {target: source[source_id] for source_id, target in PROFILE_TO_TARGET.items()}


def _weighted_checksum(record_ids: Iterable[str]) -> int:
    return sum(TARGET_WEIGHTS[record_id] for record_id in record_ids) % 1000


def _parse_target_records(problem: str) -> tuple[Records, dict[str, int]]:
    records: Records = {}
    weights: dict[str, int] = {}
    for number, weight, raw_facts in re.findall(r"Q(\d+)\((\d+)\):([a-z,]+)", problem):
        record_id = f"Q{number}"
        records[record_id] = frozenset(
            TARGET_TO_INTERNAL[fact] for fact in raw_facts.split(",")
        )
        weights[record_id] = int(weight)
    return records, weights


def _parse_target_rules(problem: str) -> set[Rule]:
    active_text = problem.split("一般条款", 1)[0].split("注意旧规则", 1)[0]
    parsed: set[Rule] = set()
    for raw_antecedents, consequent in re.findall(
        r"([a-z]+(?:∧[a-z]+)?)→([a-z]+)", active_text
    ):
        parsed.add(
            (
                frozenset(
                    TARGET_TO_INTERNAL[antecedent]
                    for antecedent in raw_antecedents.split("∧")
                ),
                TARGET_TO_INTERNAL[consequent],
            )
        )
    return parsed


def _verify_full_case(
    case: Case,
    *,
    include_stable_to_cleared: bool,
    expected: int,
) -> VerificationResult:
    records = _target_records()
    rules = _rules(include_stable_to_cleared=include_stable_to_cleared)
    target_ids = _violations(records, rules)
    one_pass_ids = _violations(records, rules, one_pass=True)
    target_checksum = _weighted_checksum(target_ids)
    one_pass_checksum = _weighted_checksum(one_pass_ids)
    parsed_records, parsed_weights = _parse_target_records(case.target.problem)
    parsed_rules = _parse_target_rules(case.target.problem)
    return _result(
        case,
        [
            _check("target-text-records", parsed_records, records),
            _check("target-text-weights", parsed_weights, TARGET_WEIGHTS),
            _check("target-text-active-rules", parsed_rules, set(rules)),
            _check("fixed-point-violation-checksum", target_checksum, expected),
            _check("initial-fact-one-pass-checksum", one_pass_checksum, 837),
            _check("stored-target", _gold(case), str(target_checksum)),
            _check("stored-lure", _lure(case), str(one_pass_checksum)),
            _check("copy-equals-lure", _copy(case), _lure(case)),
            _check("copy-differs-from-target", _copy(case) != _gold(case), True),
        ],
    )


@register("FORMAL-P4-CLOSURE-L3-01")
def verify_formal_p4_closure_l3_01(case: Case) -> VerificationResult:
    result = _verify_full_case(case, include_stable_to_cleared=True, expected=604)
    baseline_source = _violations(_source_records(), _rules())
    mapped = [PROFILE_TO_TARGET[record_id] for record_id in baseline_source]
    result.checks.extend(
        [
            _check("source-baseline-violations", baseline_source, ["S3", "S5", "S7", "S9"]),
            _check("profile-isomorphic-target-violations", mapped, ["Q11", "Q1", "Q4", "Q6"]),
        ]
    )
    return result


@register("FORMAL-P4-CLOSURE-L4-01")
def verify_formal_p4_closure_l4_01(case: Case) -> VerificationResult:
    result = _verify_full_case(case, include_stable_to_cleared=False, expected=99)
    baseline = set(_violations(_source_records(), _rules()))
    ablated = set(
        _violations(_source_records(), _rules(include_stable_to_cleared=False))
    )
    added = sorted(ablated - baseline, key=lambda value: int(value[1:]))
    mapped_added = [PROFILE_TO_TARGET[record_id] for record_id in added]
    updated_weight = (604 + sum(TARGET_WEIGHTS[item] for item in mapped_added)) % 1000
    result.checks.extend(
        [
            _check("source-rule-ablation-additions", added, ["S1", "S8", "S11"]),
            _check("mapped-rule-ablation-additions", mapped_added, ["Q7", "Q12", "Q10"]),
            _check("baseline-plus-ablation-weight", updated_weight, 99),
        ]
    )
    return result
