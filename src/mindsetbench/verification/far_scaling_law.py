"""Executable verifiers for the far-transfer family ``far-scaling-law-v1``.

Shared mindset: when a shape is scaled by k, surface-like quantities grow by k^2 and
volume-like quantities by k^3, so any process fed through a surface and consumed by
a volume (heat loss vs heat content, load-bearing section vs weight, wall cost vs
storage volume) does not scale proportionally. The decoy is proportional
extrapolation.
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

VERIFIER = "far_scaling_law"
SCHEMA_LEAK_TERMS = (
    "平方立方",
    "尺度律",
    "幂律",
    "面积体积比",
    "比表面积",
    "异速",
    "Kleiber",
    "square-cube",
    "标度",
)

F = Fraction


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


def _num(value: Fraction) -> str:
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return text


# -------------------------------------------------- surface supply / volume demand


def surface_over_volume_ratio(scale: Fraction) -> Fraction:
    """(k^2 / k^3) relative to the small object: quantities per unit volume fall by 1/k."""

    return 1 / scale


SOURCE_SMALL_LENGTH, SOURCE_LARGE_LENGTH, SOURCE_INTAKE = F(10), F(100), F(50)
SOURCE_PHRASES = ("体长 10 厘米", "体长 100 厘米", "50%", "散热")

L0_SMALL, L0_LARGE, L0_INTAKE = F(5), F(40), F(60)
L0_PHRASES = ("体长 5 厘米", "体长 40 厘米", "60%")

L1_SMALL, L1_LARGE, L1_MINUTES = F(4), F(8), F(10)
L1_PHRASES = ("4 厘米", "8 厘米", "10 分钟", "降到危险温度")

L2_SMALL_VOLUME, L2_LARGE_VOLUME, L2_MINUTES = F(2), F(16), F(20)
L2_PHRASES = ("2 升", "16 升", "20 分钟", "同样形状")


def intake_share(small: Fraction, large: Fraction, small_share: Fraction) -> Fraction:
    return small_share * surface_over_volume_ratio(large / small)


def time_scaled_by_length(small: Fraction, large: Fraction, minutes: Fraction) -> Fraction:
    """Heat content ~ k^3, loss rate ~ k^2: time ~ k."""

    return minutes * (large / small)


def cube_root_scale(volume_ratio: Fraction) -> Fraction:
    for k in range(1, 100):
        if F(k) ** 3 == volume_ratio:
            return F(k)
    raise ValueError(f"volume ratio {volume_ratio} is not a perfect cube")


# ------------------------------------------- L3: model bridge, strength vs weight


L3_SCALE, L3_MODEL_FACTOR = F(40), F(30)
L3_PHRASES = ("1 比 40", "30 倍", "同样材料", "承受自身重量")


def safety_factor_at_scale(model_factor: Fraction, scale: Fraction) -> Fraction:
    """Strength ~ k^2, weight ~ k^3: the factor shrinks by 1/k."""

    return model_factor / scale


def l3_answer() -> str:
    holds = safety_factor_at_scale(L3_MODEL_FACTOR, L3_SCALE) >= 1
    max_scale = L3_MODEL_FACTOR  # factor / k >= 1  <=>  k <= factor
    return f"HOLDS={'YES' if holds else 'NO'};MAX_SCALE={_num(max_scale)}"


# ----------------------------------------------- L4: cold store envelope economics


L4_SMALL_EDGE, L4_LARGE_EDGE, L4_COST_PER_M2 = F(10), F(20), F(400)
L4_PHRASES = ("边长 10 米", "边长 20 米", "每平方米 400 元", "每立方米")


def envelope_cost_per_m3(edge: Fraction, cost_per_m2: Fraction) -> Fraction:
    area = 6 * edge * edge
    volume = edge**3
    return area * cost_per_m2 / volume


def l4_answer() -> str:
    return _num(envelope_cost_per_m3(L4_LARGE_EDGE, L4_COST_PER_M2))


def l4_decoy() -> str:
    return _num(envelope_cost_per_m3(L4_SMALL_EDGE, L4_COST_PER_M2))


# ------------------------------------------------------------------- verifiers


def _source_checks(case: Case) -> list[VerificationCheck]:
    gold = _num(intake_share(SOURCE_SMALL_LENGTH, SOURCE_LARGE_LENGTH, SOURCE_INTAKE))
    return [
        _check(
            "source-text-states-facts", _contains_all(case.source.problem, SOURCE_PHRASES), True
        ),
        _check("source-gold", gold, "5"),
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


@register("FAR-SCALE-L0-01")
def verify_far_scale_l0_01(case: Case) -> VerificationResult:
    gold = _num(intake_share(L0_SMALL, L0_LARGE, L0_INTAKE))
    decoy = _num(L0_INTAKE)
    checks = _common_checks(case, gold, decoy, L0_PHRASES)
    checks.append(_check("l0-gold", gold, "7.5"))
    return _result(case, checks)


@register("FAR-SCALE-L1-01")
def verify_far_scale_l1_01(case: Case) -> VerificationResult:
    gold = _num(time_scaled_by_length(L1_SMALL, L1_LARGE, L1_MINUTES))
    decoy = _num(L1_MINUTES * (L1_LARGE / L1_SMALL) ** 3)  # proportional to mass
    checks = _common_checks(case, gold, decoy, L1_PHRASES)
    checks.append(_check("l1-gold", gold, "20"))
    checks.append(_check("l1-decoy", decoy, "80"))
    return _result(case, checks)


@register("FAR-SCALE-L2-01")
def verify_far_scale_l2_01(case: Case) -> VerificationResult:
    scale = cube_root_scale(L2_LARGE_VOLUME / L2_SMALL_VOLUME)
    gold = _num(L2_MINUTES * scale)
    decoy = _num(L2_MINUTES * (L2_LARGE_VOLUME / L2_SMALL_VOLUME))  # proportional to volume
    checks = _common_checks(case, gold, decoy, L2_PHRASES)
    checks.append(_check("l2-gold", gold, "40"))
    checks.append(_check("l2-decoy", decoy, "160"))
    return _result(case, checks)


@register("FAR-SCALE-L3-01")
def verify_far_scale_l3_01(case: Case) -> VerificationResult:
    gold = l3_answer()
    decoy = "HOLDS=YES;MAX_SCALE=UNLIMITED"
    checks = _common_checks(case, gold, decoy, L3_PHRASES)
    checks.append(_check("l3-gold", gold, "HOLDS=NO;MAX_SCALE=30"))
    checks.append(
        _check(
            "l3-factor-at-full-scale",
            _num(safety_factor_at_scale(L3_MODEL_FACTOR, L3_SCALE)),
            "0.75",
        )
    )
    return _result(case, checks)


@register("FAR-SCALE-L4-01")
def verify_far_scale_l4_01(case: Case) -> VerificationResult:
    gold = l4_answer()
    decoy = l4_decoy()
    checks = _common_checks(case, gold, decoy, L4_PHRASES)
    checks.append(_check("l4-gold", gold, "120"))
    checks.append(_check("l4-decoy", decoy, "240"))
    return _result(case, checks)
