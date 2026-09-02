from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import combinations

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.formal_p5_chain import (
    FEATURE_RENAME,
    Plan,
    PlanningInstance,
    _best_plans,
    _identifier_key,
    _parse_instance,
    _rename_action,
    _replay,
    _source_instance,
    _target_full,
    _target_l0,
    _target_l1,
    _target_l2,
)
from mindsetbench.verification.registry import register


@dataclass(frozen=True)
class PlanningCertificate:
    best_cost: int
    best_plans: tuple[Plan, ...]
    lower_goal_count: int
    runner_up_cost: int
    runner_up_count: int


@dataclass(frozen=True)
class CertificateLevelSpec:
    target: PlanningInstance
    expected_plan: Plan
    expected_runner_up_cost: int
    expected_runner_up_count: int
    lure_kind: str
    expected_action_count: int


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


def _gold(case: Case) -> str:
    return case.target.answer.legacy_value()


def _lure(case: Case) -> str:
    assert case.lure and case.lure.answer
    return case.lure.answer.legacy_value()


def _copy(case: Case) -> str:
    assert case.copy_probe
    return case.copy_probe.answer.legacy_value()


def _planning_certificate(instance: PlanningInstance) -> PlanningCertificate:
    maximum_gap = sum(action.cost for action in instance.actions)
    plans: tuple[Plan, ...] = ()
    cost_layers: tuple[int, ...] = ()
    for extra_cost in range(maximum_gap + 1):
        plans = _best_plans(instance, extra_cost)
        cost_layers = tuple(sorted({plan.cost for plan in plans}))
        if len(cost_layers) >= 2:
            break
    if len(cost_layers) < 2:
        raise ValueError("planning certificate requires a reachable runner-up")
    best_cost, runner_up_cost = cost_layers[:2]
    return PlanningCertificate(
        best_cost=best_cost,
        best_plans=tuple(plan for plan in plans if plan.cost == best_cost),
        lower_goal_count=0,
        runner_up_cost=runner_up_cost,
        runner_up_count=sum(plan.cost == runner_up_cost for plan in plans),
    )


def _monotone_certificate(instance: PlanningInstance) -> PlanningCertificate:
    """Certificate for the preregistered wrong add-only subset model."""

    plans: list[Plan] = []
    for size in range(len(instance.actions) + 1):
        for selected in combinations(instance.actions, size):
            state = instance.initial | frozenset().union(*(action.adds for action in selected))
            if not instance.goal_present <= state:
                continue
            actions = tuple(
                action.name
                for action in sorted(selected, key=lambda action: _identifier_key(action.name))
            )
            plans.append(
                Plan(
                    cost=sum(action.cost for action in selected),
                    actions=actions,
                    final_state=state,
                )
            )
    cost_layers = tuple(sorted({plan.cost for plan in plans}))
    if len(cost_layers) < 2:
        raise ValueError("monotone certificate requires a runner-up subset")
    best_cost, runner_up_cost = cost_layers[:2]
    return PlanningCertificate(
        best_cost=best_cost,
        best_plans=tuple(
            sorted(
                (plan for plan in plans if plan.cost == best_cost),
                key=lambda plan: plan.actions,
            )
        ),
        lower_goal_count=0,
        runner_up_cost=runner_up_cost,
        runner_up_count=sum(plan.cost == runner_up_cost for plan in plans),
    )


def _format_certificate(certificate: PlanningCertificate) -> str:
    if len(certificate.best_plans) != 1:
        raise ValueError("certificate answer requires a unique optimum")
    return ";".join(
        (
            str(certificate.best_cost),
            ">".join(certificate.best_plans[0].actions),
            str(certificate.lower_goal_count),
            str(len(certificate.best_plans)),
            str(certificate.runner_up_cost),
            str(certificate.runner_up_count),
        )
    )


_CERTIFICATE_PATTERN = re.compile(
    r"证书：C\*=(\d+)；P\*=([A-Z]\d+(?:>[A-Z]\d+)*)；"
    r"N<C\*=(\d+)；N=C\*=(\d+)；Cnext=(\d+)；Nnext=(\d+)"
)


def _parse_solution_certificate(solution: str) -> tuple[int, str, int, int, int, int]:
    match = _CERTIFICATE_PATTERN.search(solution)
    if not match:
        raise ValueError("source solution is missing its machine-readable certificate")
    cost, path, lower, equal, runner_cost, runner_count = match.groups()
    return int(cost), path, int(lower), int(equal), int(runner_cost), int(runner_count)


SOURCE_PLAN = Plan(
    15,
    ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"),
    frozenset({"B", "F", "H", "I", "J"}),
)


LEVEL_SPECS = {
    0: CertificateLevelSpec(
        target=_target_l0(),
        expected_plan=Plan(2, ("A1", "A2"), frozenset({"x", "y", "z"})),
        expected_runner_up_cost=3,
        expected_runner_up_count=1,
        lure_kind="monotone-cover",
        expected_action_count=3,
    ),
    1: CertificateLevelSpec(
        target=_target_l1(),
        expected_plan=Plan(4, ("B1", "B2", "B3"), frozenset({"a", "b", "c", "e"})),
        expected_runner_up_cost=5,
        expected_runner_up_count=1,
        lure_kind="monotone-cover",
        expected_action_count=4,
    ),
    2: CertificateLevelSpec(
        target=_target_l2(),
        expected_plan=Plan(
            11,
            ("C2", "C1", "C3", "C4", "C5", "C6", "C7"),
            frozenset({"b", "c", "e", "f", "g", "h"}),
        ),
        expected_runner_up_cost=13,
        expected_runner_up_count=1,
        lure_kind="monotone-cover",
        expected_action_count=9,
    ),
    3: CertificateLevelSpec(
        target=_target_full(edited=False),
        expected_plan=Plan(
            15,
            ("K7", "K2", "K10", "K4", "K9", "K1", "K6", "K3"),
            frozenset({"v", "r", "s", "x", "y"}),
        ),
        expected_runner_up_cost=16,
        expected_runner_up_count=3,
        lure_kind="monotone-cover",
        expected_action_count=16,
    ),
    4: CertificateLevelSpec(
        target=_target_full(edited=True),
        expected_plan=Plan(
            17,
            ("K8", "K10", "K4", "K9", "K1", "K6"),
            frozenset({"v", "r", "s", "x", "y"}),
        ),
        expected_runner_up_cost=18,
        expected_runner_up_count=3,
        lure_kind="stale-pre-edit-certificate",
        expected_action_count=16,
    ),
}


def _certificate_summary(
    certificate: PlanningCertificate,
) -> tuple[int, str, int, int, int, int]:
    if len(certificate.best_plans) != 1:
        raise ValueError("summary requires a unique optimum")
    return (
        certificate.best_cost,
        ">".join(certificate.best_plans[0].actions),
        certificate.lower_goal_count,
        len(certificate.best_plans),
        certificate.runner_up_cost,
        certificate.runner_up_count,
    )


def _lure_certificate(level: int, target: PlanningInstance) -> PlanningCertificate:
    if level == 4:
        return _planning_certificate(_target_full(edited=False))
    return _monotone_certificate(target)


def _structural_checks(level: int, target: PlanningInstance) -> list[VerificationCheck]:
    if level < 3:
        return []
    renamed_source = tuple(_rename_action(action) for action in _source_instance().actions)
    target_by_name = {action.name: action for action in target.actions}
    mismatches = {
        action.name: (action, target_by_name[action.name])
        for action in renamed_source
        if action != target_by_name[action.name]
    }
    if level == 3:
        source = _source_instance()
        return [
            _check("complete-action-isomorphism", mismatches, {}),
            _check(
                "feature-isomorphism-initial",
                target.initial,
                frozenset(FEATURE_RENAME[value] for value in source.initial),
            ),
            _check(
                "feature-isomorphism-goals",
                (target.goal_present, target.goal_absent),
                (
                    frozenset(FEATURE_RENAME[value] for value in source.goal_present),
                    frozenset(FEATURE_RENAME[value] for value in source.goal_absent),
                ),
            ),
        ]
    old, new = mismatches["K3"]
    stale_path = LEVEL_SPECS[3].expected_plan.actions
    return [
        _check("single-broken-action", set(mismatches), {"K3"}),
        _check("single-effect-edit", (old.adds, new.adds), (frozenset({"v"}), frozenset({"p"}))),
        _check("stale-plan-misses-edited-goal", _replay(target, stale_path)[0], False),
    ]


def _verify_certificate_level(case: Case, level: int) -> VerificationResult:
    spec = LEVEL_SPECS[level]
    source = _source_instance()
    parsed_source = _parse_instance(case.source.problem)
    parsed_target = _parse_instance(case.target.problem)
    source_certificate = _planning_certificate(source)
    target_certificate = _planning_certificate(spec.target)
    lure_certificate = _lure_certificate(level, spec.target)
    lure_plan = lure_certificate.best_plans[0]
    assert case.lure and case.lure.solution
    disclosure_markers = ("错误", "真实", "目标题", "新版")
    checks = [
        _check("source-text-instance", parsed_source, source),
        _check("source-unique-optimum", source_certificate.best_plans, (SOURCE_PLAN,)),
        _check(
            "source-certificate-shape",
            _certificate_summary(source_certificate),
            (15, "S1>S2>S3>S4>S5>S6>S7>S8", 0, 1, 16, 3),
        ),
        _check(
            "source-machine-readable-certificate",
            _parse_solution_certificate(case.source.solution),
            _certificate_summary(source_certificate),
        ),
        _check(
            "source-teaches-path-multiplicity",
            "等成本的不同有序路径必须分别保留并计数" in case.source.solution,
            True,
        ),
        _check(
            "source-path-separator-contract",
            "串内部只能用 >，不能用逗号" in case.source.problem,
            True,
        ),
        _check("stored-source", case.source.answer, _format_certificate(source_certificate)),
        _check("target-text-instance", parsed_target, spec.target),
        _check("target-action-count", len(parsed_target.actions), spec.expected_action_count),
        _check(
            "target-path-separator-contract",
            "串内部只能用 >，不能用逗号" in case.target.problem,
            True,
        ),
        _check("target-unique-optimum", target_certificate.best_plans, (spec.expected_plan,)),
        _check(
            "target-certificate-shape",
            (
                target_certificate.lower_goal_count,
                len(target_certificate.best_plans),
                target_certificate.runner_up_cost,
                target_certificate.runner_up_count,
            ),
            (0, 1, spec.expected_runner_up_cost, spec.expected_runner_up_count),
        ),
        _check("lure-kind", case.lure.wrong_schema_id if case.lure else None, spec.lure_kind),
        _check(
            "lure-solution-is-blinded",
            tuple(marker for marker in disclosure_markers if marker in case.lure.solution),
            (),
        ),
        _check("lure-unique-optimum", len(lure_certificate.best_plans), 1),
        _check("lure-plan-fails-true-model", _replay(spec.target, lure_plan.actions)[0], False),
        _check("stored-target", _gold(case), _format_certificate(target_certificate)),
        _check("stored-lure", _lure(case), _format_certificate(lure_certificate)),
        _check("copy-equals-lure", _copy(case), _lure(case)),
        _check("copy-differs-from-target", _copy(case) != _gold(case), True),
    ]
    checks.extend(_structural_checks(level, spec.target))
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


@register("FORMAL-P5-CERT-L0-01")
def verify_formal_p5_cert_l0_01(case: Case) -> VerificationResult:
    return _verify_certificate_level(case, 0)


@register("FORMAL-P5-CERT-L1-01")
def verify_formal_p5_cert_l1_01(case: Case) -> VerificationResult:
    return _verify_certificate_level(case, 1)


@register("FORMAL-P5-CERT-L2-01")
def verify_formal_p5_cert_l2_01(case: Case) -> VerificationResult:
    return _verify_certificate_level(case, 2)


@register("FORMAL-P5-CERT-L3-01")
def verify_formal_p5_cert_l3_01(case: Case) -> VerificationResult:
    return _verify_certificate_level(case, 3)


@register("FORMAL-P5-CERT-L4-01")
def verify_formal_p5_cert_l4_01(case: Case) -> VerificationResult:
    return _verify_certificate_level(case, 4)
