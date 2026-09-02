from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.formal_p5_certificate import (
    _certificate_summary,
    _format_certificate,
    _parse_solution_certificate,
    _planning_certificate,
)
from mindsetbench.verification.formal_p5_certificate_outage import (
    OUTAGE_SPECS,
    SOURCE_BASELINE,
    SOURCE_EFFECTIVE,
    TARGET_BASELINE,
    _apply_outage,
)
from mindsetbench.verification.formal_p5_chain import (
    Action,
    PlanningInstance,
    _action,
    _parse_instance,
)
from mindsetbench.verification.registry import register

PolicyPredicate = Callable[[Action, PlanningInstance], bool]

SOURCE_POLICY_STATEMENT = "δ:费用=1，需={c}，置=G+，且禁=清=∅"
ORACLE_INSIGHT = (
    "把任务拆成谓词唯一匹配、删除匹配卡、独立重算两个目标成本层三步；三个策略不能累积冻结。"
)
FALSE_INSIGHT = (
    "对每个谓词只报告匹配卡，但仍在完整动作基线上计算证书；三个策略复用同一最优层与次优层。"
)


@dataclass(frozen=True)
class PolicySpec:
    name: str
    statement: str
    predicate: PolicyPredicate
    expected_target_action: str


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


def _alpha(action: Action, instance: PlanningInstance) -> bool:
    positive_goal = instance.goal_present
    return (
        action.cost == 4
        and len(action.requires) == 1
        and action.requires <= positive_goal
        and action.adds == positive_goal - action.requires
        and not action.forbids
        and not action.clears
    )


def _beta(action: Action, instance: PlanningInstance) -> bool:
    return (
        action.cost == 2
        and action.requires == instance.initial & instance.goal_absent
        and len(action.adds) == 1
        and action.adds <= instance.goal_absent
        and len(action.clears) == 1
        and action.clears <= instance.goal_present
    )


def _gamma(action: Action, instance: PlanningInstance) -> bool:
    return (
        action.cost == 1
        and len(action.requires) == 1
        and len(action.adds) == 1
        and action.requires | action.adds <= instance.goal_present
        and not action.forbids
        and not action.clears
    )


TARGET_POLICIES = (
    PolicySpec(
        name="α",
        statement=("α:费用=4，|需|=1，需⊆G+，置=G+\\需，且禁=清=∅"),
        predicate=_alpha,
        expected_target_action="K13",
    ),
    PolicySpec(
        name="β",
        statement=("β:费用=2，需=I∩G-，|置|=1且置⊆G-，|清|=1且清⊆G+"),
        predicate=_beta,
        expected_target_action="K2",
    ),
    PolicySpec(
        name="γ",
        statement=("γ:费用=1，|需|=|置|=1，需∪置⊆G+，且禁=清=∅"),
        predicate=_gamma,
        expected_target_action="K6",
    ),
)


def _unique_match(instance: PlanningInstance, policy: PolicySpec) -> str:
    matches = tuple(
        action.name for action in instance.actions if policy.predicate(action, instance)
    )
    if len(matches) != 1:
        raise ValueError(f"policy {policy.name} expected one match, found {matches}")
    return matches[0]


def _source_match(instance: PlanningInstance) -> str:
    matches = tuple(
        action.name
        for action in instance.actions
        if action.cost == 1
        and action.requires == frozenset({"c"})
        and action.adds == instance.goal_present
        and not action.forbids
        and not action.clears
    )
    if len(matches) != 1:
        raise ValueError(f"source policy expected one match, found {matches}")
    return matches[0]


def _lure_baseline() -> PlanningInstance:
    return PlanningInstance(
        initial=frozenset({"m"}),
        goal_present=frozenset({"o"}),
        goal_absent=frozenset(),
        actions=(
            _action("R4", 3, requires="m", adds="p"),
            _action("R1", 2, requires="m", adds="n"),
            _action("R5", 3, requires="p", adds="o"),
            _action("R3", 5, requires="m", adds="o"),
            _action("R2", 2, requires="n", adds="o"),
        ),
    )


LURE_BASELINE = _lure_baseline()
LURE_MATCHES = ("R5", "R1", "R3")


def _summary_parts(summary: tuple[int, str, int, int, int, int]) -> tuple[str, ...]:
    return tuple(str(value) for value in summary)


def _target_joint_answer() -> str:
    parts: list[str] = []
    for policy in TARGET_POLICIES:
        action_name = _unique_match(TARGET_BASELINE, policy)
        certificate = _planning_certificate(_apply_outage(TARGET_BASELINE, action_name))
        parts.extend((action_name, *_summary_parts(_certificate_summary(certificate))))
    return ";".join(parts)


def _lure_joint_answer() -> str:
    certificate = _planning_certificate(LURE_BASELINE)
    summary = _summary_parts(_certificate_summary(certificate))
    parts: list[str] = []
    for action_name in LURE_MATCHES:
        parts.extend((action_name, *summary))
    return ";".join(parts)


TARGET_JOINT_ANSWER = _target_joint_answer()
LURE_JOINT_ANSWER = _lure_joint_answer()


def _gold(case: Case) -> str:
    return case.target.answer.legacy_value()


def _lure(case: Case) -> str:
    assert case.lure and case.lure.answer
    return case.lure.answer.legacy_value()


def _copy(case: Case) -> str:
    assert case.copy_probe
    return case.copy_probe.answer.legacy_value()


def _verify_policy_joint(case: Case) -> VerificationResult:
    source_parsed = _parse_instance(case.source.problem)
    source_match = _source_match(source_parsed)
    source_effective = _apply_outage(source_parsed, source_match)
    source_certificate = _planning_certificate(source_effective)

    target_parsed = _parse_instance(case.target.problem)
    target_matches = tuple(_unique_match(target_parsed, policy) for policy in TARGET_POLICIES)
    target_summaries = tuple(
        _certificate_summary(_planning_certificate(_apply_outage(target_parsed, action_name)))
        for action_name in target_matches
    )

    assert case.lure and case.lure.solution
    assert case.hints and case.hints.oracle_mindset and case.hints.false_mindset
    lure_parsed = _parse_instance(case.lure.problem)
    lure_certificate = _planning_certificate(lure_parsed)
    disclosure_markers = ("错误", "真实", "目标题", "新版")
    checks = [
        _check("source-visible-baseline", source_parsed, SOURCE_BASELINE),
        _check(
            "source-policy-statement",
            SOURCE_POLICY_STATEMENT in case.source.problem,
            True,
        ),
        _check("source-policy-match", source_match, "S5"),
        _check("source-effective-instance", source_effective, SOURCE_EFFECTIVE),
        _check(
            "source-certificate",
            _certificate_summary(source_certificate),
            (2, "S1>S2", 0, 1, 3, 1),
        ),
        _check(
            "source-machine-readable-certificate",
            _parse_solution_certificate(case.source.solution),
            _certificate_summary(source_certificate),
        ),
        _check(
            "stored-source",
            case.source.answer,
            f"S5;{_format_certificate(source_certificate)}",
        ),
        _check("target-visible-baseline", target_parsed, TARGET_BASELINE),
        _check(
            "target-policy-statements",
            tuple(policy.statement in case.target.problem for policy in TARGET_POLICIES),
            (True, True, True),
        ),
        _check("target-policy-unique-matches", target_matches, ("K13", "K2", "K6")),
        _check(
            "target-certificate-summaries",
            target_summaries,
            tuple(
                OUTAGE_SPECS[f"FORMAL-P5-CERT-OUTAGE-{name}-01"].expected_summary
                for name in target_matches
            ),
        ),
        _check("stored-target", _gold(case), TARGET_JOINT_ANSWER),
        _check("target-answer-parts", len(case.target.answer.parts), 21),
        _check("oracle-mindset", case.hints.oracle_mindset.insight, ORACLE_INSIGHT),
        _check("false-mindset", case.hints.false_mindset.insight, FALSE_INSIGHT),
        _check(
            "mindset-hints-are-path-decoupled",
            any(label in case.hints.model_dump_json() for label in ("K1", "R1")),
            False,
        ),
        _check("lure-visible-baseline", lure_parsed, LURE_BASELINE),
        _check(
            "lure-baseline-certificate",
            _certificate_summary(lure_certificate),
            (4, "R1>R2", 0, 1, 5, 1),
        ),
        _check(
            "lure-solution-is-blinded",
            tuple(marker for marker in disclosure_markers if marker in case.lure.solution),
            (),
        ),
        _check("stored-lure", _lure(case), LURE_JOINT_ANSWER),
        _check("lure-answer-parts", len(case.lure.answer.parts), 21),
        _check("copy-equals-lure", _copy(case), _lure(case)),
        _check("copy-differs-from-target", _copy(case) != _gold(case), True),
        _check("path-labels-decoupled", set(target_matches).isdisjoint(LURE_MATCHES), True),
        _check(
            "baseline-path-not-in-lure",
            "K8>K10>K4>K9>K1>K6" not in case.lure.solution,
            True,
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


@register("FORMAL-P5-CERT-POLICY-JOINT-01")
def verify_formal_p5_cert_policy_joint_01(case: Case) -> VerificationResult:
    return _verify_policy_joint(case)
