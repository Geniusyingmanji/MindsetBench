"""Executable verifiers for the far-transfer family ``far-selection-extreme-v1``.

Shared mindset: the most extreme of many noisy units looks alarming even when every
unit is ordinary; whether the extreme is evidence depends on how many units were
ranked, and a value picked because it was the maximum overstates the unit's true
level. The decoy is the single-unit reading: judge the worst unit as if it had been
chosen in advance.
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction
from math import ceil, comb

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

VERIFIER = "far_selection_extreme"
SCHEMA_LEAK_TERMS = (
    "选择效应",
    "多重比较",
    "族误差",
    "均值回归",
    "赢者诅咒",
    "极值统计",
    "Bonferroni",
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


# ------------------------------------------------------------ exact binomial tails


def tail(n: int, p: Fraction, k: int) -> Fraction:
    """P(X >= k) for X ~ Binomial(n, p), exact."""

    if k <= 0:
        return F(1)
    if k > n:
        return F(0)
    return sum(comb(n, x) * p**x * (1 - p) ** (n - x) for x in range(k, n + 1))


def any_unit_tail(units: Sequence[tuple[int, int]], p: Fraction) -> Fraction:
    """P(at least one unit reaches its own count) for independent units (n_j, k_j)."""

    none = F(1)
    for n, k in units:
        none *= 1 - tail(n, p, k)
    return 1 - none


def min_alarming_count(units: int, n: int, p: Fraction, alpha: Fraction) -> int:
    for k in range(n + 1):
        if any_unit_tail([(n, k)] * units, p) < alpha:
            return k
    raise ValueError("no count is alarming")


def min_single_count(n: int, p: Fraction, alpha: Fraction) -> int:
    for k in range(n + 1):
        if tail(n, p, k) < alpha:
            return k
    raise ValueError("no count is alarming")


def _yes_no(flag: bool) -> str:
    return "YES" if flag else "NO"


def equal_units_answers(
    *, units: int, n: int, p: Fraction, top: int, alpha: Fraction
) -> tuple[str, str]:
    """(gold, decoy) for equally sized units."""

    family = any_unit_tail([(n, top)] * units, p)
    single = tail(n, p, top)
    gold = f"ACT={_yes_no(family < alpha)};MIN_COUNT={min_alarming_count(units, n, p, alpha)}"
    decoy = f"ACT={_yes_no(single < alpha)};MIN_COUNT={min_single_count(n, p, alpha)}"
    return gold, decoy


ALPHA = F(1, 20)

SOURCE = dict(units=25, n=200, p=F(3, 20), top=43)
SOURCE_PHRASES = ("25 家门店", "200 单", "15%", "43 单", "低于 5%")

L0 = dict(units=30, n=150, p=F(3, 25), top=29)
L0_PHRASES = ("30 家", "150 单", "12%", "29 单")

L1 = dict(units=40, n=120, p=F(2, 25), top=18)
L1_PHRASES = ("40 名坐席", "120 通", "8%", "18 通")

L2 = dict(units=32, n=120, p=F(1, 10), top=21)
L2_PHRASES = ("32 所学校", "120 名", "10%", "21 名")

# L3: unequal school sizes ranked by rate; the top rate comes from a small school.
L3_SIZES = (40,) * 5 + (120,) * 10 + (300,) * 5
L3_P = F(1, 10)
L3_TOP_SIZE, L3_TOP_COUNT = 40, 10  # 25% at the smallest size
L3_PHRASES = ("5 所 40 人", "10 所 120 人", "5 所 300 人", "10 名", "10%", "40 人的学校")


def _units_at_rate(rate: Fraction) -> list[tuple[int, int]]:
    return [(n, ceil(rate * n)) for n in L3_SIZES]


def family_at_rate(rate: Fraction) -> Fraction:
    """P(some school reaches the observed rate) with each school at its own size."""

    return any_unit_tail(_units_at_rate(rate), L3_P)


def copied_family_at_rate(rate: Fraction) -> Fraction:
    """Copy probe: every school treated as if it had the top school's size."""

    return any_unit_tail([(L3_TOP_SIZE, ceil(rate * L3_TOP_SIZE))] * len(L3_SIZES), L3_P)


def min_count_for_size(size: int, family) -> int:
    for k in range(size + 1):
        if family(F(k, size)) < ALPHA:
            return k
    raise ValueError("no count is alarming")


def l3_answers() -> tuple[str, str]:
    rate = F(L3_TOP_COUNT, L3_TOP_SIZE)
    gold = (
        f"ACT={_yes_no(family_at_rate(rate) < ALPHA)};"
        f"MIN40={min_count_for_size(40, family_at_rate)}"
    )
    decoy = (
        f"ACT={_yes_no(copied_family_at_rate(rate) < ALPHA)};"
        f"MIN40={min_count_for_size(40, copied_family_at_rate)}"
    )
    return gold, decoy


def l3_probabilities() -> tuple[Fraction, Fraction]:
    rate = F(L3_TOP_COUNT, L3_TOP_SIZE)
    return family_at_rate(rate), copied_family_at_rate(rate)


# ---------------------------------------------- L4: shrinkage of the selected top score


L4_ABILITIES = (F(1, 2), F(3, 5), F(7, 10), F(4, 5), F(9, 10))
L4_ITEMS, L4_TOP_SCORE, L4_CANDIDATES = 20, 19, 15
L4_PHRASES = ("15 名", "20 题", "19 题", "0.5、0.6、0.7、0.8、0.9", "同样 20 题")


def posterior_mean_ability(score: int, items: int, abilities: Sequence[Fraction]) -> Fraction:
    weights = [comb(items, score) * a**score * (1 - a) ** (items - score) for a in abilities]
    total = sum(weights)
    return sum(a * w for a, w in zip(abilities, weights, strict=True)) / total


def l4_answers() -> tuple[str, str]:
    expected = posterior_mean_ability(L4_TOP_SCORE, L4_ITEMS, L4_ABILITIES) * L4_ITEMS
    gold = f"{float(expected):.1f}"
    decoy = f"{float(L4_TOP_SCORE):.1f}"
    return gold, decoy


# ------------------------------------------------------------------- verifiers


def _source_checks(case: Case) -> list[VerificationCheck]:
    gold, decoy = equal_units_answers(alpha=ALPHA, **SOURCE)
    return [
        _check(
            "source-text-states-facts", _contains_all(case.source.problem, SOURCE_PHRASES), True
        ),
        _check("source-gold", gold, "ACT=NO;MIN_COUNT=46"),
        _check("source-single-store-would-act", decoy.startswith("ACT=YES"), True),
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


def _equal_level(
    case: Case, spec: dict, phrases: Sequence[str], expected: str
) -> VerificationResult:
    gold, decoy = equal_units_answers(alpha=ALPHA, **spec)
    checks = _common_checks(case, gold, decoy, phrases)
    checks.append(_check("gold-value", gold, expected))
    single = tail(spec["n"], spec["p"], spec["top"])
    family = any_unit_tail([(spec["n"], spec["top"])] * spec["units"], spec["p"])
    checks.append(
        _check(
            "single-below-alpha-but-family-above",
            (single < ALPHA, family < ALPHA),
            (True, False),
            detail=f"single={float(single):.4f} family={float(family):.3f}",
        )
    )
    return _result(case, checks)


@register("FAR-EXTREME-L0-01")
def verify_far_extreme_l0_01(case: Case) -> VerificationResult:
    return _equal_level(case, L0, L0_PHRASES, "ACT=NO;MIN_COUNT=32")


@register("FAR-EXTREME-L1-01")
def verify_far_extreme_l1_01(case: Case) -> VerificationResult:
    return _equal_level(case, L1, L1_PHRASES, "ACT=NO;MIN_COUNT=21")


@register("FAR-EXTREME-L2-01")
def verify_far_extreme_l2_01(case: Case) -> VerificationResult:
    return _equal_level(case, L2, L2_PHRASES, "ACT=NO;MIN_COUNT=24")


@register("FAR-EXTREME-L3-01")
def verify_far_extreme_l3_01(case: Case) -> VerificationResult:
    gold, decoy = l3_answers()
    family, copied = l3_probabilities()
    checks = _common_checks(case, gold, decoy, L3_PHRASES)
    checks.append(
        _check(
            "l3-gold-and-copy",
            (gold, decoy),
            ("ACT=YES;MIN40=10", "ACT=NO;MIN40=11"),
            detail=f"family={float(family):.3f} copied={float(copied):.3f}",
        )
    )
    return _result(case, checks)


@register("FAR-EXTREME-L4-01")
def verify_far_extreme_l4_01(case: Case) -> VerificationResult:
    gold, decoy = l4_answers()
    checks = _common_checks(case, gold, decoy, L4_PHRASES)
    checks.append(_check("l4-gold", gold, "17.6"))
    checks.append(_check("l4-decoy", decoy, "19.0"))
    return _result(case, checks)
