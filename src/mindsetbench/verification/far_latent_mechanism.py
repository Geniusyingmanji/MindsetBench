"""Executable verifier for latent-mechanism far-transfer candidates.

The target does not expose a response matrix.  It describes six procedural
rules and five fact patterns; the verifier derives every counterfactual result
from those rules, then exhaustively solves the bounded adaptive query problem.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

ALLOW = "ALLOW"
DENY = "DENY"
REMAND = "REMAND"
OUTCOMES = (ALLOW, DENY, REMAND)
VERIFIER = "far_latent_mechanism"


@dataclass(frozen=True)
class Facts:
    emergency: bool = False
    reliance: bool = False
    notice: bool = False


Rule = Callable[[Facts], str]


def rule_a(facts: Facts) -> str:
    if facts.emergency:
        return DENY
    if facts.notice:
        return ALLOW
    if facts.reliance:
        return DENY
    return REMAND


def rule_b(facts: Facts) -> str:
    return ALLOW if not (facts.emergency or facts.reliance or facts.notice) else DENY


def rule_c(facts: Facts) -> str:
    if facts.emergency:
        return DENY
    if not facts.reliance:
        return REMAND
    return DENY if facts.notice else ALLOW


def rule_d(facts: Facts) -> str:
    return ALLOW if facts.emergency or (facts.reliance and facts.notice) else REMAND


def rule_e(facts: Facts) -> str:
    no_trigger = not (facts.emergency or facts.reliance or facts.notice)
    return ALLOW if facts.emergency or no_trigger else REMAND


def rule_f(facts: Facts) -> str:
    should_deny = facts.emergency or (facts.reliance and not facts.notice)
    return DENY if should_deny else REMAND


RULES: Mapping[str, Rule] = {
    "甲": rule_a,
    "乙": rule_b,
    "丙": rule_c,
    "丁": rule_d,
    "戊": rule_e,
    "己": rule_f,
}
CASES: Mapping[str, Facts] = {
    "V": Facts(),
    "W": Facts(notice=True),
    "X": Facts(reliance=True),
    "Y": Facts(reliance=True, notice=True),
    "Z": Facts(emergency=True),
}
COSTS: Mapping[str, int] = {"V": 3, "W": 2, "X": 4, "Y": 5, "Z": 6}


def response_matrix() -> dict[str, dict[str, str]]:
    return {
        case_name: {rule_name: rule(facts) for rule_name, rule in RULES.items()}
        for case_name, facts in CASES.items()
    }


def partition(
    candidates: Iterable[str], responses: Mapping[str, str]
) -> dict[str, tuple[str, ...]]:
    groups: dict[str, list[str]] = {}
    for candidate in candidates:
        groups.setdefault(responses[candidate], []).append(candidate)
    return {outcome: tuple(group) for outcome, group in groups.items()}


def distinguishing_queries(
    candidates: tuple[str, ...],
    *,
    exclude: str,
    matrix: Mapping[str, Mapping[str, str]],
) -> tuple[str, ...]:
    return tuple(
        query
        for query, responses in matrix.items()
        if query != exclude
        and len(partition(candidates, responses)) == len(candidates)
    )


@dataclass(frozen=True)
class Policy:
    first: str
    followups: Mapping[str, str]
    worst_cost: int


def feasible_policy(first: str) -> Policy | None:
    matrix = response_matrix()
    first_groups = partition(RULES, matrix[first])
    followups: dict[str, str] = {}
    worst = COSTS[first]
    for outcome in OUTCOMES:
        group = first_groups.get(outcome, ())
        if len(group) <= 1:
            followups[outcome] = "STOP"
            continue
        candidates = distinguishing_queries(group, exclude=first, matrix=matrix)
        if not candidates:
            return None
        second = min(candidates, key=lambda query: (COSTS[query], query))
        followups[outcome] = second
        worst = max(worst, COSTS[first] + COSTS[second])
    return Policy(first=first, followups=followups, worst_cost=worst)


def optimal_policies() -> tuple[Policy, ...]:
    policies = tuple(
        policy
        for first in CASES
        if (policy := feasible_policy(first)) is not None
    )
    best = min(policy.worst_cost for policy in policies)
    return tuple(policy for policy in policies if policy.worst_cost == best)


def render(policy: Policy) -> str:
    return (
        f"FIRST={policy.first};IF_ALLOW={policy.followups[ALLOW]};"
        f"IF_DENY={policy.followups[DENY]};IF_REMAND={policy.followups[REMAND]};"
        f"WORST={policy.worst_cost}"
    )


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


@register("FAR-LATENT-PRECEDENT-L4-01")
def verify_latent_precedent(case: Case) -> VerificationResult:
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None
    policies = optimal_policies()
    gold = render(policies[0])
    lure = "FIRST=Y;IF_ALLOW=W;IF_DENY=W;IF_REMAND=V;WORST=8"
    matrix = response_matrix()
    required = (
        "甲：",
        "乙：",
        "丙：",
        "丁：",
        "戊：",
        "己：",
        "V 卷三项事实都没有",
        "X 卷只有 L",
        "最多调阅两个不同卷宗",
        "最坏情况下",
    )
    checks = [
        _check("stored-source-answer", case.source.answer, "R;IF_RED=STOP;IF_BLUE=Q;IF_WHITE=P;7"),
        _check(
            "target-text-carries-latent-world",
            all(phrase in case.target.problem for phrase in required),
            True,
        ),
        _check(
            "derived-x-responses",
            tuple(matrix["X"].values()),
            (DENY, DENY, ALLOW, REMAND, REMAND, DENY),
        ),
        _check("unique-optimal-first-query", tuple(policy.first for policy in policies), ("X",)),
        _check("stored-target-answer", case.target.answer.legacy_value(), gold),
        _check("stored-lure-answer", case.lure.answer.legacy_value(), lure),
        _check("stored-copy-probe", case.copy_probe.answer.legacy_value(), lure),
        _check("copy-probe-differs-from-gold", lure != gold, True),
    ]
    return VerificationResult(case_id=case.id, checks=checks, verifier=VERIFIER)
