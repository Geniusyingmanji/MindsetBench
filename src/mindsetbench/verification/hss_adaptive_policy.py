from __future__ import annotations

from collections.abc import Mapping, Sequence

from mindsetbench.models.case import Case
from mindsetbench.verification.active_query import (
    AdaptivePolicy,
    DiagnosticWorld,
    best_two_stage_policies,
    encode_two_stage_policy,
    score_queries,
)
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.hss_active_query import (
    _evidence_verdict,
    _p4_outcomes,
    _p6_fatal,
    _p6_outcomes,
    _p8_outcomes,
)
from mindsetbench.verification.institutional_mechanism import (
    MechanismCase,
    classify_mechanism,
)
from mindsetbench.verification.registry import register

QUERY_IDS = ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6")
QUERY_COSTS = {"Q1": 2, "Q2": 3, "Q3": 4, "Q4": 5, "Q5": 6, "Q6": 7}
OBSERVATION_ORDER = ("R", "B")


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


def _worlds(
    outcomes: Sequence[str],
    observations_by_query: Mapping[str, Sequence[str]],
) -> tuple[DiagnosticWorld, ...]:
    if set(observations_by_query) != set(QUERY_IDS):
        raise ValueError("adaptive query matrix must define Q1 through Q6 exactly once")
    if any(len(observations) != len(outcomes) for observations in observations_by_query.values()):
        raise ValueError("every adaptive query must predict one observation per world")
    return tuple(
        DiagnosticWorld(
            world_id=f"W{index + 1}",
            outcome=outcome,
            observations=tuple(
                (query_id, observations_by_query[query_id][index]) for query_id in QUERY_IDS
            ),
        )
        for index, outcome in enumerate(outcomes)
    )


def _adaptive_answer(
    worlds: Sequence[DiagnosticWorld],
) -> tuple[AdaptivePolicy, str]:
    winners = best_two_stage_policies(worlds, QUERY_IDS, QUERY_COSTS)
    if len(winners) != 1:
        raise ValueError(f"adaptive policy is not unique: {len(winners)} winners")
    winner = winners[0]
    return winner, encode_two_stage_policy(
        winner,
        root_observation_order=OBSERVATION_ORDER,
        second_observation_order=OBSERVATION_ORDER,
    )


def _verify_adaptive_case(
    case: Case,
    *,
    target_outcomes: Sequence[str],
    lure_outcomes: Sequence[str],
    observations: Mapping[str, Sequence[str]],
    expected_target_root: str,
    expected_lure_root: str,
    required_phrases: Sequence[str],
) -> VerificationResult:
    target_worlds = _worlds(target_outcomes, observations)
    lure_worlds = _worlds(lure_outcomes, observations)
    target_policy, target_answer = _adaptive_answer(target_worlds)
    lure_policy, lure_answer = _adaptive_answer(lure_worlds)
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None
    single_query_scores = score_queries(target_worlds, QUERY_IDS)
    checks = [
        _check(
            "target-text-contract",
            all(p in case.target.problem for p in required_phrases),
            True,
        ),
        _check("target-policy-unique-root", target_policy.root_query, expected_target_root),
        _check("lure-policy-unique-root", lure_policy.root_query, expected_lure_root),
        _check(
            "requires-two-stages",
            all(score.worst_outcome_ambiguity > 1 for score in single_query_scores.values()),
            True,
        ),
        _check(
            "target-second-step-adapts",
            len({branch.second_query for branch in target_policy.branches}),
            2,
        ),
        _check("stored-target", case.target.answer.legacy_value(), target_answer),
        _check("stored-lure", case.lure.answer.legacy_value(), lure_answer),
        _check("copy-equals-lure", case.copy_probe.answer.legacy_value(), lure_answer),
        _check("copy-differs-target", case.copy_probe.answer != case.target.answer, True),
    ]
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


def _p4_adaptive_outcomes(*, unrestricted_pair: bool) -> list[str]:
    return [*_p4_outcomes(unrestricted_pair=unrestricted_pair), "DENY", "DENY"]


@register("HSS-ADAPTIVE-P4-PERFORMANCE-L4-01")
def verify_hss_adaptive_p4_performance_l4_01(case: Case) -> VerificationResult:
    observations = {
        "Q1": ("R", "R", "R", "R", "B", "R", "B", "B"),
        "Q2": ("B", "B", "R", "R", "B", "B", "B", "R"),
        "Q3": ("B", "R", "B", "B", "R", "R", "R", "B"),
        "Q4": ("R", "R", "B", "R", "B", "R", "R", "B"),
        "Q5": ("B", "R", "B", "B", "B", "B", "R", "B"),
        "Q6": ("R", "R", "R", "R", "R", "B", "B", "R"),
    }
    return _verify_adaptive_case(
        case,
        target_outcomes=_p4_adaptive_outcomes(unrestricted_pair=False),
        lure_outcomes=_p4_adaptive_outcomes(unrestricted_pair=True),
        observations=observations,
        expected_target_root="Q4",
        expected_lure_root="Q3",
        required_phrases=("八份复排提案", "Q1成本2", "Q6成本7", "最多两次", "第二次"),
    )


def _p6_adaptive_outcomes(*, treat_finance_as_control: bool) -> list[str]:
    outcomes = _p6_outcomes(treat_finance_as_control=treat_finance_as_control)
    outcomes.append(
        _p6_fatal(
            reverse_control=treat_finance_as_control,
            finance_only=not treat_finance_as_control,
        )
    )
    outcomes.append(_p6_fatal(reverse_control=True))
    return outcomes


@register("HSS-ADAPTIVE-P6-EXHIBITION-L4-01")
def verify_hss_adaptive_p6_exhibition_l4_01(case: Case) -> VerificationResult:
    observations = {
        "Q1": ("R", "B", "B", "B", "B", "B", "R", "R"),
        "Q2": ("R", "B", "R", "R", "R", "B", "B", "R"),
        "Q3": ("R", "B", "R", "B", "R", "R", "R", "B"),
        "Q4": ("R", "B", "R", "R", "B", "B", "B", "B"),
        "Q5": ("R", "B", "B", "B", "R", "B", "B", "B"),
        "Q6": ("B", "B", "R", "B", "B", "B", "B", "R"),
    }
    return _verify_adaptive_case(
        case,
        target_outcomes=_p6_adaptive_outcomes(treat_finance_as_control=False),
        lure_outcomes=_p6_adaptive_outcomes(treat_finance_as_control=True),
        observations=observations,
        expected_target_root="Q2",
        expected_lure_root="Q4",
        required_phrases=("八种策展复原", "Q1成本2", "Q6成本7", "最多两次", "第二次"),
    )


def _p7_adaptive_outcomes(*, surface_count: bool) -> list[str]:
    configurations = (
        (3, 2, 0, 0),
        (3, 1, 0, 0),
        (2, 2, 2, 2),
        (3, 1, 2, 2),
        (2, 2, 3, 1),
        (3, 1, 3, 1),
        (3, 1, 2, 2),
        (2, 2, 2, 2),
    )
    return [
        _evidence_verdict(*configuration, surface_count=surface_count)
        for configuration in configurations
    ]


@register("HSS-ADAPTIVE-P7-ORAL-L4-01")
def verify_hss_adaptive_p7_oral_l4_01(case: Case) -> VerificationResult:
    observations = {
        "Q1": ("B", "B", "R", "R", "R", "R", "B", "B"),
        "Q2": ("R", "B", "B", "R", "R", "R", "R", "B"),
        "Q3": ("R", "B", "B", "R", "B", "R", "B", "R"),
        "Q4": ("R", "R", "B", "R", "R", "B", "B", "R"),
        "Q5": ("B", "B", "R", "R", "B", "B", "R", "R"),
        "Q6": ("B", "R", "B", "R", "B", "R", "R", "R"),
    }
    return _verify_adaptive_case(
        case,
        target_outcomes=_p7_adaptive_outcomes(surface_count=False),
        lure_outcomes=_p7_adaptive_outcomes(surface_count=True),
        observations=observations,
        expected_target_root="Q5",
        expected_lure_root="Q1",
        required_phrases=("八种传唱史", "Q1成本2", "Q6成本7", "最多两次", "第二次"),
    )


def _p8_adaptive_outcomes(*, visible_form_only: bool) -> list[str]:
    outcomes = _p8_outcomes(visible_form_only=visible_form_only)
    outcomes.extend(
        (
            classify_mechanism(
                MechanismCase(
                    True,
                    costly_action=True,
                    actor_bears_cost=True,
                    committed_type_can_bear=True,
                )
            ).value,
            classify_mechanism(MechanismCase(True, removes_defection_option=True)).value,
        )
    )
    return outcomes


@register("HSS-ADAPTIVE-P8-DIPLOMACY-L4-01")
def verify_hss_adaptive_p8_diplomacy_l4_01(case: Case) -> VerificationResult:
    observations = {
        "Q1": ("B", "B", "B", "R", "R", "B", "R", "R"),
        "Q2": ("B", "R", "R", "R", "R", "B", "B", "R"),
        "Q3": ("R", "B", "R", "B", "R", "B", "R", "B"),
        "Q4": ("B", "B", "B", "B", "R", "B", "R", "B"),
        "Q5": ("B", "B", "B", "R", "R", "R", "R", "B"),
        "Q6": ("R", "R", "B", "B", "R", "R", "R", "R"),
    }
    return _verify_adaptive_case(
        case,
        target_outcomes=_p8_adaptive_outcomes(visible_form_only=False),
        lure_outcomes=_p8_adaptive_outcomes(visible_form_only=True),
        observations=observations,
        expected_target_root="Q3",
        expected_lure_root="Q6",
        required_phrases=("八种使节记录", "Q1成本2", "Q6成本7", "最多两次", "第二次"),
    )
