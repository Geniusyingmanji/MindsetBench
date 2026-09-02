from __future__ import annotations

import re
from dataclasses import dataclass, replace

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.formal_p5_certificate import (
    _certificate_summary,
    _format_certificate,
    _parse_solution_certificate,
    _planning_certificate,
)
from mindsetbench.verification.formal_p5_chain import (
    PlanningInstance,
    _action,
    _parse_instance,
    _replay,
    _target_full,
)
from mindsetbench.verification.registry import register


@dataclass(frozen=True)
class OutageSpec:
    frozen_action: str
    expected_summary: tuple[int, str, int, int, int, int]
    changed_parts: tuple[int, ...]
    baseline_plan_remains_executable: bool


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


def _source_baseline() -> PlanningInstance:
    return PlanningInstance(
        initial=frozenset({"a"}),
        goal_present=frozenset({"z"}),
        goal_absent=frozenset(),
        actions=(
            _action("S1", 1, requires="a", adds="b"),
            _action("S2", 1, requires="b", adds="z"),
            _action("S3", 3, requires="a", adds="z"),
            _action("S4", 2, requires="a", adds="c"),
            _action("S5", 1, requires="c", adds="z"),
        ),
    )


_FREEZE_PATTERN = re.compile(r"冻结卡=([A-Z]\d+)")


def _parse_frozen_action(problem: str) -> str:
    matches = _FREEZE_PATTERN.findall(problem)
    if len(matches) != 1:
        raise ValueError(f"expected exactly one frozen action, found {matches}")
    return matches[0]


def _apply_outage(instance: PlanningInstance, frozen_action: str) -> PlanningInstance:
    names = [action.name for action in instance.actions]
    if names.count(frozen_action) != 1:
        raise ValueError(f"frozen action {frozen_action!r} is not uniquely present")
    return replace(
        instance,
        actions=tuple(action for action in instance.actions if action.name != frozen_action),
    )


SOURCE_FROZEN_ACTION = "S5"
SOURCE_BASELINE = _source_baseline()
SOURCE_EFFECTIVE = _apply_outage(SOURCE_BASELINE, SOURCE_FROZEN_ACTION)
TARGET_BASELINE = _target_full(edited=True)
BASELINE_CERTIFICATE = _planning_certificate(TARGET_BASELINE)
BASELINE_PLAN = BASELINE_CERTIFICATE.best_plans[0].actions


OUTAGE_SPECS = {
    "FORMAL-P5-CERT-OUTAGE-K13-01": OutageSpec(
        frozen_action="K13",
        expected_summary=(17, "K8>K10>K4>K9>K1>K6", 0, 1, 18, 2),
        changed_parts=(5,),
        baseline_plan_remains_executable=True,
    ),
    "FORMAL-P5-CERT-OUTAGE-K2-01": OutageSpec(
        frozen_action="K2",
        expected_summary=(17, "K8>K10>K4>K9>K1>K6", 0, 1, 19, 3),
        changed_parts=(4,),
        baseline_plan_remains_executable=True,
    ),
    "FORMAL-P5-CERT-OUTAGE-K6-01": OutageSpec(
        frozen_action="K6",
        expected_summary=(
            18,
            "K7>K2>K10>K4>K9>K16>K1",
            0,
            1,
            19,
            3,
        ),
        changed_parts=(0, 1, 4),
        baseline_plan_remains_executable=False,
    ),
}


def _gold(case: Case) -> str:
    return case.target.answer.legacy_value()


def _lure(case: Case) -> str:
    assert case.lure and case.lure.answer
    return case.lure.answer.legacy_value()


def _copy(case: Case) -> str:
    assert case.copy_probe
    return case.copy_probe.answer.legacy_value()


def _can_replay(instance: PlanningInstance, path: tuple[str, ...]) -> bool:
    if not set(path) <= {action.name for action in instance.actions}:
        return False
    return _replay(instance, path)[0]


def _changed_parts(
    left: tuple[int, str, int, int, int, int],
    right: tuple[int, str, int, int, int, int],
) -> tuple[int, ...]:
    return tuple(
        index
        for index, values in enumerate(zip(left, right, strict=True))
        if values[0] != values[1]
    )


def _verify_outage(case: Case) -> VerificationResult:
    spec = OUTAGE_SPECS[case.id]
    source_parsed = _parse_instance(case.source.problem)
    source_frozen = _parse_frozen_action(case.source.problem)
    source_effective = _apply_outage(source_parsed, source_frozen)
    source_baseline_certificate = _planning_certificate(SOURCE_BASELINE)
    source_certificate = _planning_certificate(SOURCE_EFFECTIVE)

    target_parsed = _parse_instance(case.target.problem)
    target_frozen = _parse_frozen_action(case.target.problem)
    target_effective = _apply_outage(target_parsed, target_frozen)
    target_certificate = _planning_certificate(target_effective)
    target_summary = _certificate_summary(target_certificate)
    baseline_summary = _certificate_summary(BASELINE_CERTIFICATE)

    assert case.lure and case.lure.solution
    lure_parsed = _parse_instance(case.lure.problem)
    disclosure_markers = ("错误", "真实", "目标题", "新版")
    checks = [
        _check("source-text-baseline", source_parsed, SOURCE_BASELINE),
        _check("source-freeze-marker", source_frozen, SOURCE_FROZEN_ACTION),
        _check("source-effective-instance", source_effective, SOURCE_EFFECTIVE),
        _check(
            "source-baseline-runner-count",
            source_baseline_certificate.runner_up_count,
            2,
        ),
        _check(
            "source-outage-certificate",
            _certificate_summary(source_certificate),
            (2, "S1>S2", 0, 1, 3, 1),
        ),
        _check(
            "source-machine-readable-certificate",
            _parse_solution_certificate(case.source.solution),
            _certificate_summary(source_certificate),
        ),
        _check("stored-source", case.source.answer, _format_certificate(source_certificate)),
        _check("target-visible-baseline", target_parsed, TARGET_BASELINE),
        _check("target-freeze-marker", target_frozen, spec.frozen_action),
        _check("target-effective-action-count", len(target_effective.actions), 15),
        _check("target-certificate", target_summary, spec.expected_summary),
        _check("stored-target", _gold(case), _format_certificate(target_certificate)),
        _check("lure-visible-baseline", lure_parsed, TARGET_BASELINE),
        _check(
            "lure-solution-is-blinded",
            tuple(marker for marker in disclosure_markers if marker in case.lure.solution),
            (),
        ),
        _check("stored-lure", _lure(case), _format_certificate(BASELINE_CERTIFICATE)),
        _check("copy-equals-lure", _copy(case), _lure(case)),
        _check("copy-differs-from-target", _copy(case) != _gold(case), True),
        _check("outage-changes-certificate", target_summary != baseline_summary, True),
        _check(
            "outage-changed-parts",
            _changed_parts(baseline_summary, target_summary),
            spec.changed_parts,
        ),
        _check(
            "baseline-plan-remains-executable",
            _can_replay(target_effective, BASELINE_PLAN),
            spec.baseline_plan_remains_executable,
        ),
        _check(
            "source-path-separator-contract",
            "串内部只能用 >，不能用逗号" in case.source.problem,
            True,
        ),
        _check(
            "target-path-separator-contract",
            "串内部只能用 >，不能用逗号" in case.target.problem,
            True,
        ),
    ]
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


@register("FORMAL-P5-CERT-OUTAGE-K13-01")
def verify_formal_p5_cert_outage_k13_01(case: Case) -> VerificationResult:
    return _verify_outage(case)


@register("FORMAL-P5-CERT-OUTAGE-K2-01")
def verify_formal_p5_cert_outage_k2_01(case: Case) -> VerificationResult:
    return _verify_outage(case)


@register("FORMAL-P5-CERT-OUTAGE-K6-01")
def verify_formal_p5_cert_outage_k6_01(case: Case) -> VerificationResult:
    return _verify_outage(case)
