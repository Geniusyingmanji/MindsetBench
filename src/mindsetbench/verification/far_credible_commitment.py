"""Executable verifiers for the far-transfer family ``far-credible-commitment-v1``.

Shared mindset: a promise is credible only when, at the moment reneging would pay,
the promiser no longer holds the option to renege (the option is physically gone or
its control sits with an uncontrolled party whose interests oppose reneging) and the
counterparty can verify this in time. Stated penalty size or rhetorical strength is
the domain shortcut and the preregistered decoy.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

VERIFIER = "far_credible_commitment"
SCHEMA_LEAK_TERMS = (
    "可信承诺",
    "删除选项",
    "承诺装置",
    "反悔权",
    "博弈",
    "逆向归纳",
    "子博弈",
    "自缚",
)


def _check(
    name: str, actual: object, expected: object, detail: str | None = None
) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
        detail=detail,
    )


def _contains_all(text: str, phrases: Sequence[str]) -> bool:
    return all(phrase in text for phrase in phrases)


def _leaks(text: str) -> list[str]:
    return [term for term in SCHEMA_LEAK_TERMS if term in text]


def _result(case: Case, checks: list[VerificationCheck]) -> VerificationResult:
    return VerificationResult(case_id=case.id, checks=checks, verifier=VERIFIER)


# ------------------------------------------------------------ attribute-based levels


@dataclass(frozen=True)
class Measure:
    """Structural facts about one proposed commitment measure.

    controller: who can undo the commitment when reneging pays -- "self" (the promiser
    or an agent it controls), "none" (physically/legally irreversible), or "other".
    aligned: an "other" controller that the promiser funds, appoints or otherwise
    steers, which makes it "self" in effect (the L3 broken relation).
    enforcement: any explicit penalty, automation or contract wording -- what the
    shortcut reads as credibility.
    """

    name: str
    controller: str
    observable: bool = True
    aligned: bool = False
    enforcement: bool = False


def credible(measure: Measure, *, check_alignment: bool = True) -> bool:
    if measure.controller == "self":
        return False
    if measure.controller == "other" and check_alignment and measure.aligned:
        return False
    return measure.observable


def shortcut(measure: Measure) -> bool:
    return measure.enforcement


def _label(flag: bool) -> str:
    return "CREDIBLE" if flag else "CHEAP"


def classify(
    measures: Sequence[Measure], rule, **kwargs: object
) -> str:  # rule: Callable[[Measure], bool]
    return ";".join(f"{measure.name}={_label(rule(measure, **kwargs))}" for measure in measures)


SOURCE_MEASURES = (
    Measure("A", "self"),
    Measure("B", "self", enforcement=True),
    Measure("C", "other", enforcement=True),
    Measure("D", "self", enforcement=True),
)
SOURCE_PHRASES = (
    "绝不再延期",
    "去掉该限制的新版本",
    "不可单方解除的托管合同",
    "由服务商自行认定",
)

L0_MEASURES = (
    Measure("M1", "self"),
    Measure("M2", "self", enforcement=True),
    Measure("M3", "other", enforcement=True),
    Measure("M4", "self", enforcement=True),
)
L0_PHRASES = ("运维可随时暂停", "由第三方销毁密钥", "不可单方解除", "内部合规部门认定")

L1_MEASURES = (
    Measure("M1", "self"),
    Measure("M2", "self", enforcement=True),
    Measure("M3", "other", enforcement=True),
    Measure("M4", "self", enforcement=True),
)
L1_PHRASES = ("单方修改条款", "须经协会同意", "协议公开", "由平台自行决定时机")

L2_MEASURES = (
    Measure("M1", "self"),
    Measure("M2", "self", enforcement=True),
    Measure("M3", "self", enforcement=True),
    Measure("M4", "other", enforcement=True),
)
L2_PHRASES = ("店长酌情", "需店长在后台点击确认", "由总部裁定", "门店不能撤回")

L3_MEASURES = (
    Measure("T1", "self"),
    Measure("T2", "other", aligned=True, enforcement=True),
    Measure("T3", "none", enforcement=True),
    Measure("T4", "self", enforcement=True),
)
L3_PHRASES = ("经费与人员由", "雨季结束前无法重建", "由北岸议会裁定", "钥匙交给")


# ----------------------------------------------------------- L4: payoff-based level


@dataclass(frozen=True)
class ThreatMeasure:
    name: str
    strike_payoff: Fraction
    no_strike_payoff: Fraction
    enforcement: bool = False

    def credible(self) -> bool:
        return self.strike_payoff > self.no_strike_payoff


F = Fraction
L4_BASE_STRIKE = F(-2)
L4_BASE_NO_STRIKE = F(0)
L4_MEASURES = (
    ThreatMeasure("M1", L4_BASE_STRIKE, L4_BASE_NO_STRIKE),
    ThreatMeasure("M2", L4_BASE_STRIKE, L4_BASE_NO_STRIKE - 3, enforcement=True),
    ThreatMeasure("M3", L4_BASE_STRIKE, L4_BASE_NO_STRIKE, enforcement=True),
    ThreatMeasure("M4", L4_BASE_STRIKE, L4_BASE_NO_STRIKE, enforcement=True),
)
L4_LURE_MEASURES = (
    ThreatMeasure("M1", L4_BASE_STRIKE, L4_BASE_NO_STRIKE),
    ThreatMeasure("M2", L4_BASE_STRIKE, L4_BASE_NO_STRIKE - 3, enforcement=True),
    ThreatMeasure("M3", L4_BASE_STRIKE + 3, L4_BASE_NO_STRIKE, enforcement=True),
    ThreatMeasure("M4", L4_BASE_STRIKE, L4_BASE_NO_STRIKE - 3, enforcement=True),
)
L4_PHRASES = ("损失 2", "损失 3", "支付 3", "损失 5", "可随时取回")


def threat_answer(measures: Sequence[ThreatMeasure]) -> str:
    return ";".join(f"{m.name}={_label(m.credible())}" for m in measures)


def threat_shortcut(measures: Sequence[ThreatMeasure]) -> str:
    return ";".join(f"{m.name}={_label(m.enforcement)}" for m in measures)


# ------------------------------------------------------------------- verifiers


def _source_checks(case: Case) -> list[VerificationCheck]:
    gold = classify(SOURCE_MEASURES, credible)
    return [
        _check(
            "source-text-states-facts", _contains_all(case.source.problem, SOURCE_PHRASES), True
        ),
        _check("source-gold", gold, "A=CHEAP;B=CHEAP;C=CREDIBLE;D=CHEAP"),
        _check("stored-source-answer", case.source.answer, gold),
    ]


def _common_checks(
    case: Case, gold: str, decoy: str, phrases: Sequence[str]
) -> list[VerificationCheck]:
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None
    return [
        *_source_checks(case),
        _check(
            "target-text-carries-required-facts", _contains_all(case.target.problem, phrases), True
        ),
        _check(
            "target-text-has-no-schema-label",
            _leaks(case.target.problem) if case.level >= 2 else [],
            [],
        ),
        _check("stored-target-answer", case.target.answer.legacy_value(), gold),
        _check("stored-lure-answer", case.lure.answer.legacy_value(), decoy),
        _check("stored-copy-probe", case.copy_probe.answer.legacy_value(), decoy),
        _check("copy-probe-differs-from-gold", gold != decoy, True),
    ]


def _attribute_level(
    case: Case, measures: Sequence[Measure], phrases: Sequence[str]
) -> VerificationResult:
    gold = classify(measures, credible)
    decoy = classify(measures, shortcut)
    checks = _common_checks(case, gold, decoy, phrases)
    checks.append(
        _check(
            "shortcut-differs-on-at-least-two-measures",
            sum(credible(m) != shortcut(m) for m in measures) >= 2,
            True,
        )
    )
    return _result(case, checks)


@register("FAR-COMMIT-L0-01")
def verify_far_commit_l0_01(case: Case) -> VerificationResult:
    return _attribute_level(case, L0_MEASURES, L0_PHRASES)


@register("FAR-COMMIT-L1-01")
def verify_far_commit_l1_01(case: Case) -> VerificationResult:
    return _attribute_level(case, L1_MEASURES, L1_PHRASES)


@register("FAR-COMMIT-L2-01")
def verify_far_commit_l2_01(case: Case) -> VerificationResult:
    return _attribute_level(case, L2_MEASURES, L2_PHRASES)


@register("FAR-COMMIT-L3-01")
def verify_far_commit_l3_01(case: Case) -> VerificationResult:
    gold = classify(L3_MEASURES, credible)
    # copy probe: apply the source rule without auditing who funds/appoints the "third party"
    decoy = classify(L3_MEASURES, credible, check_alignment=False)
    checks = _common_checks(case, gold, decoy, L3_PHRASES)
    checks.append(_check("l3-gold", gold, "T1=CHEAP;T2=CHEAP;T3=CREDIBLE;T4=CHEAP"))
    checks.append(_check("l3-copied-rule", decoy, "T1=CHEAP;T2=CREDIBLE;T3=CREDIBLE;T4=CHEAP"))
    return _result(case, checks)


@register("FAR-COMMIT-L4-01")
def verify_far_commit_l4_01(case: Case) -> VerificationResult:
    gold = threat_answer(L4_MEASURES)
    decoy = threat_shortcut(L4_MEASURES)
    checks = _common_checks(case, gold, decoy, L4_PHRASES)
    checks.append(_check("l4-gold", gold, "M1=CHEAP;M2=CREDIBLE;M3=CHEAP;M4=CHEAP"))
    checks.append(_check("l4-decoy", decoy, "M1=CHEAP;M2=CREDIBLE;M3=CREDIBLE;M4=CREDIBLE"))
    checks.append(
        _check("l4-lure-world-makes-decoy-correct", threat_answer(L4_LURE_MEASURES), decoy)
    )
    return _result(case, checks)
