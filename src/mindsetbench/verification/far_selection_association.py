"""Executable verifiers for the far-transfer family ``far-selection-association-v1``.

Shared mindset: when the units you get to observe were selected on either of two
traits (or on their sum, or on a threshold that mixes them), the selected subset
shows an association between the traits that the whole population does not have,
and the association says nothing about what changing one trait would do. The decoy
reads the association in the observed subset as a fact about everyone.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from fractions import Fraction

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

VERIFIER = "far_selection_association"
SCHEMA_LEAK_TERMS = (
    "伯克森",
    "选择偏差",
    "对撞",
    "碰撞偏差",
    "幸存者偏差",
    "选择效应",
    "Berkson",
    "collider",
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


# ------------------------------------------------------------- 2x2 finite tables


class Table:
    """Counts of a finite population over two binary traits A and B."""

    def __init__(self, yy: int, yn: int, ny: int, nn: int) -> None:
        self.yy, self.yn, self.ny, self.nn = yy, yn, ny, nn

    def association(self) -> str:
        """Sign of P(B | A) - P(B | not A); 'NONE' when equal."""

        with_a = self.yy + self.yn
        without_a = self.ny + self.nn
        if with_a == 0 or without_a == 0:
            return "NONE"
        left = F(self.yy, with_a)
        right = F(self.ny, without_a)
        if left == right:
            return "NONE"
        return "POS" if left > right else "NEG"

    def select(self, keep: Callable[[bool, bool], bool]) -> Table:
        return Table(
            self.yy if keep(True, True) else 0,
            self.yn if keep(True, False) else 0,
            self.ny if keep(False, True) else 0,
            self.nn if keep(False, False) else 0,
        )

    def total(self) -> int:
        return self.yy + self.yn + self.ny + self.nn


def either(a: bool, b: bool) -> bool:
    return a or b


def answer(population: Table, keep: Callable[[bool, bool], bool]) -> str:
    selected = population.select(keep)
    return f"POP={population.association()};SEL={selected.association()};CAUSAL=NO"


def decoy(population: Table, keep: Callable[[bool, bool], bool]) -> str:
    """Take the selected subset's association as the population's and as causal."""

    selected = population.select(keep)
    sel = selected.association()
    return f"POP={sel};SEL={sel};CAUSAL={'YES' if sel != 'NONE' else 'NO'}"


SOURCE = Table(yy=20, yn=20, ny=30, nn=30)  # A independent of B in the population
SOURCE_PHRASES = ("糖尿病", "胆囊炎", "20 人", "30 人", "只要患有其中任何一种")

L0 = Table(yy=12, yn=28, ny=18, nn=42)
L0_PHRASES = ("12 人", "28 人", "18 人", "42 人", "只要出现其中任何一种")

L1 = Table(yy=15, yn=35, ny=15, nn=35)
L1_PHRASES = ("15 人", "35 人", "任一项指标异常")

L2 = Table(yy=16, yn=24, ny=24, nn=36)
L2_PHRASES = ("16 人", "24 人", "36 人", "任一项达到优秀即进入面试")

# L3: a genuinely positive association in the population that selection reverses.
L3 = Table(yy=30, yn=10, ny=20, nn=40)
L3_PHRASES = ("30 人", "10 人", "20 人", "40 人", "任一项满意的学员才会留下评论")


def l3_copy_probe() -> str:
    """Copying the source conclusion: 'the subset's association is an artefact, so the
    population has none'."""

    selected = L3.select(either)
    return f"POP=NONE;SEL={selected.association()};CAUSAL=NO"


# ---------------------------------------------- L4: flux-limited catalogue (grid)


L4_DISTANCES = (1, 2, 3, 4)
L4_LUMINOSITIES = (1, 4, 9, 16)
L4_LIMIT = F(1)
L4_PHRASES = ("1、4、9、16", "1、2、3、4", "亮度除以距离的平方", "不低于 1", "每种组合各有 5 颗")


def grid_association(pairs: Sequence[tuple[int, int]]) -> str:
    """Sign of the covariance between distance and luminosity over the pairs."""

    n = len(pairs)
    mean_d = F(sum(d for d, _ in pairs), n)
    mean_l = F(sum(lum for _, lum in pairs), n)
    cov = sum((d - mean_d) * (lum - mean_l) for d, lum in pairs)
    if cov == 0:
        return "NONE"
    return "POS" if cov > 0 else "NEG"


def catalogue_pairs() -> list[tuple[int, int]]:
    return [(d, lum) for d in L4_DISTANCES for lum in L4_LUMINOSITIES if F(lum, d * d) >= L4_LIMIT]


def l4_answer() -> str:
    population = [(d, lum) for d in L4_DISTANCES for lum in L4_LUMINOSITIES]
    return f"POP={grid_association(population)};CAT={grid_association(catalogue_pairs())};INFER=NO"


def l4_decoy() -> str:
    cat = grid_association(catalogue_pairs())
    return f"POP={cat};CAT={cat};INFER=YES"


# ------------------------------------------------------------------- verifiers


def _source_checks(case: Case) -> list[VerificationCheck]:
    gold = answer(SOURCE, either)
    return [
        _check(
            "source-text-states-facts", _contains_all(case.source.problem, SOURCE_PHRASES), True
        ),
        _check("source-gold", gold, "POP=NONE;SEL=NEG;CAUSAL=NO"),
        _check("stored-source-answer", case.source.answer, gold),
    ]


def _common_checks(
    case: Case, gold: str, decoy_value: str, phrases: Sequence[str]
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
        _check("stored-lure-answer", case.lure.answer.legacy_value(), decoy_value),
        _check("stored-copy-probe", case.copy_probe.answer.legacy_value(), decoy_value),
        _check("copy-probe-differs-from-gold", gold != decoy_value, True),
    ]


def _table_level(case: Case, table: Table, phrases: Sequence[str]) -> VerificationResult:
    gold = answer(table, either)
    checks = _common_checks(case, gold, decoy(table, either), phrases)
    checks.append(_check("population-independent", table.association(), "NONE"))
    checks.append(_check("selected-negative", table.select(either).association(), "NEG"))
    return _result(case, checks)


@register("FAR-BERK-L0-01")
def verify_far_berk_l0_01(case: Case) -> VerificationResult:
    return _table_level(case, L0, L0_PHRASES)


@register("FAR-BERK-L1-01")
def verify_far_berk_l1_01(case: Case) -> VerificationResult:
    return _table_level(case, L1, L1_PHRASES)


@register("FAR-BERK-L2-01")
def verify_far_berk_l2_01(case: Case) -> VerificationResult:
    return _table_level(case, L2, L2_PHRASES)


@register("FAR-BERK-L3-01")
def verify_far_berk_l3_01(case: Case) -> VerificationResult:
    gold = answer(L3, either)
    checks = _common_checks(case, gold, l3_copy_probe(), L3_PHRASES)
    checks.append(_check("l3-gold", gold, "POP=POS;SEL=NEG;CAUSAL=NO"))
    checks.append(_check("l3-copy", l3_copy_probe(), "POP=NONE;SEL=NEG;CAUSAL=NO"))
    return _result(case, checks)


@register("FAR-BERK-L4-01")
def verify_far_berk_l4_01(case: Case) -> VerificationResult:
    gold = l4_answer()
    checks = _common_checks(case, gold, l4_decoy(), L4_PHRASES)
    checks.append(_check("l4-gold", gold, "POP=NONE;CAT=POS;INFER=NO"))
    checks.append(_check("l4-catalogue-size", len(catalogue_pairs()), 10))
    return _result(case, checks)
