"""Executable verifiers for the far-transfer family ``far-threshold-cascade-v1``.

Shared mindset: a cascade spreads through the *gaps* in the distribution of
thresholds (or margins), not through its average; two populations with almost the
same mean stop at completely different sizes, and the same seeds placed differently
on a network either take everything or nothing. The decoy is the aggregate reading:
compare averages or totals and predict "about the same".
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

VERIFIER = "far_threshold_cascade"
SCHEMA_LEAK_TERMS = ("级联", "临界质量", "阈值模型", "门槛分布", "连锁反应", "引爆点", "多米诺")

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


# ------------------------------------------------------- well-mixed threshold cascade


def expand(groups: Sequence[tuple[int, int]]) -> list[int]:
    """[(count, threshold), ...] -> flat threshold list."""

    return [threshold for count, threshold in groups for _ in range(count)]


def cascade_size(thresholds: Sequence[int]) -> int:
    """Fixed point of 'join once at least t others have joined'."""

    joined = sum(1 for t in thresholds if t == 0)
    while True:
        reached = sum(1 for t in thresholds if t <= joined)
        if reached == joined:
            return joined
        joined = reached


def mean_threshold_rule(thresholds: Sequence[int]) -> int:
    """Aggregate shortcut: everyone whose threshold is at or below the average joins."""

    mean = F(sum(thresholds), len(thresholds))
    return sum(1 for t in thresholds if t <= mean)


SOURCE_A = ((5, 0), (10, 5), (15, 12), (20, 30), (50, 40))
SOURCE_B = ((5, 0), (10, 5), (15, 16), (20, 30), (50, 40))
SOURCE_PHRASES = ("15 人要看到 12 人", "15 人要看到 16 人", "100 人", "已经参加")

L0_C = ((4, 0), (6, 4), (10, 10), (30, 20), (50, 45))
L0_D = ((4, 0), (6, 4), (10, 10), (30, 20), (50, 51))
L0_PHRASES = ("50 人要看到 45 人", "50 人要看到 51 人", "100 人")

L1_A = ((3, 0), (7, 3), (10, 10), (20, 21), (20, 41))
L1_B = ((3, 0), (7, 3), (10, 10), (20, 20), (20, 40))
L1_PHRASES = ("60 户", "20 户要看到 21 户", "20 户要看到 20 户", "已签名")

L2_X = ((10, 0), (20, 10), (30, 30), (60, 60), (80, 110))
L2_Y = ((10, 0), (20, 10), (30, 30), (60, 61), (80, 121))
L2_PHRASES = (
    "200 名储户",
    "心理线是 60 人",
    "心理线是 61 人",
    "心理线是 110 人",
    "心理线是 121 人",
)


def pair_answer(
    label_a: str, a: Sequence[tuple[int, int]], label_b: str, b: Sequence[tuple[int, int]]
) -> str:
    return f"{label_a}={cascade_size(expand(a))};{label_b}={cascade_size(expand(b))}"


def pair_decoy(
    label_a: str, a: Sequence[tuple[int, int]], label_b: str, b: Sequence[tuple[int, int]]
) -> str:
    return f"{label_a}={mean_threshold_rule(expand(a))};{label_b}={mean_threshold_rule(expand(b))}"


# ---------------------------------------------- L3: local thresholds on a ring network


L3_FARMS = 12
L3_NEIGHBOUR_REACH = 2  # two farms on each side
L3_NEEDED = 2  # adopt once two of the four nearest neighbours have adopted
L3_ADJACENT_SEEDS = (1, 2)
L3_OPPOSITE_SEEDS = (1, 7)
L3_PHRASES = ("12 户", "两侧各两户", "至少两户", "1 号和 2 号", "1 号和 7 号")


def ring_cascade(seeds: Sequence[int], farms: int, reach: int, needed: int) -> int:
    adopted = set(seeds)
    while True:
        new = {
            farm
            for farm in range(1, farms + 1)
            if farm not in adopted
            and sum(
                1
                for offset in range(-reach, reach + 1)
                if offset != 0 and ((farm - 1 + offset) % farms) + 1 in adopted
            )
            >= needed
        }
        if not new:
            return len(adopted)
        adopted |= new


def l3_answers() -> tuple[str, str]:
    adjacent = ring_cascade(L3_ADJACENT_SEEDS, L3_FARMS, L3_NEIGHBOUR_REACH, L3_NEEDED)
    opposite = ring_cascade(L3_OPPOSITE_SEEDS, L3_FARMS, L3_NEIGHBOUR_REACH, L3_NEEDED)
    gold = f"ADJ={adjacent};OPP={opposite}"
    # copy probe: treat 'two adopters' as a village-wide count -> both placements saturate
    global_size = cascade_size([0, 0] + [L3_NEEDED] * (L3_FARMS - 2))
    decoy = f"ADJ={global_size};OPP={global_size}"
    return gold, decoy


# -------------------------------------- L4: progressive collapse with load shedding


def collapse(loads: Sequence[Fraction], capacities: Sequence[Fraction], struck: int) -> int:
    """Columns lost after ``struck`` is removed; shed load goes to the nearest standing
    neighbours on each side (all to one side if the other side has none)."""

    current = list(loads)
    failed = {struck}
    to_shed = {struck: current[struck]}
    while to_shed:
        for column, load in to_shed.items():
            left = next((i for i in range(column - 1, -1, -1) if i not in failed), None)
            right = next((i for i in range(column + 1, len(current)) if i not in failed), None)
            if left is None and right is None:
                continue
            if left is None:
                current[right] += load
            elif right is None:
                current[left] += load
            else:
                current[left] += load / 2
                current[right] += load / 2
        newly = {i for i in range(len(current)) if i not in failed and current[i] > capacities[i]}
        failed |= newly
        to_shed = {i: current[i] for i in newly}
    return len(failed)


L4_LOADS = tuple(F(10) for _ in range(8))
L4_P = tuple(F(14) for _ in range(8))
L4_Q = (F(10), F(25), F(10), F(25), F(10), F(10), F(10), F(12))
L4_LURE_P = tuple(F(16) for _ in range(8))
L4_STRUCK = 2  # third column, zero-based
L4_PHRASES = (
    "每根柱承担 10",
    "承载力都是 14",
    "10、25、10、25、10、10、10、12",
    "第 3 根",
    "最近的仍完好的柱",
)


def l4_answers() -> tuple[str, str]:
    gold = f"P={collapse(L4_LOADS, L4_P, L4_STRUCK)};Q={collapse(L4_LOADS, L4_Q, L4_STRUCK)}"
    decoy = "P=1;Q=1"  # totals compare fine, so "only the struck column is lost" in both
    return gold, decoy


# ------------------------------------------------------------------- verifiers


def _source_checks(case: Case) -> list[VerificationCheck]:
    gold = pair_answer("A", SOURCE_A, "B", SOURCE_B)
    return [
        _check(
            "source-text-states-facts", _contains_all(case.source.problem, SOURCE_PHRASES), True
        ),
        _check("source-gold", gold, "A=100;B=15"),
        _check("source-mean-rule-misses", pair_decoy("A", SOURCE_A, "B", SOURCE_B), "A=30;B=30"),
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


def _pair_level(
    case: Case,
    label_a: str,
    a: Sequence[tuple[int, int]],
    label_b: str,
    b: Sequence[tuple[int, int]],
    phrases: Sequence[str],
    expected: str,
) -> VerificationResult:
    gold = pair_answer(label_a, a, label_b, b)
    decoy = pair_decoy(label_a, a, label_b, b)
    checks = _common_checks(case, gold, decoy, phrases)
    checks.append(_check("gold-value", gold, expected))
    mean_a = F(sum(expand(a)), len(expand(a)))
    mean_b = F(sum(expand(b)), len(expand(b)))
    checks.append(
        _check(
            "means-nearly-equal-outcomes-differ",
            abs(mean_a - mean_b) < F(5) and cascade_size(expand(a)) != cascade_size(expand(b)),
            True,
            detail=f"mean_a={float(mean_a):.2f} mean_b={float(mean_b):.2f}",
        )
    )
    return _result(case, checks)


@register("FAR-CASCADE-L0-01")
def verify_far_cascade_l0_01(case: Case) -> VerificationResult:
    return _pair_level(case, "C", L0_C, "D", L0_D, L0_PHRASES, "C=100;D=50")


@register("FAR-CASCADE-L1-01")
def verify_far_cascade_l1_01(case: Case) -> VerificationResult:
    return _pair_level(case, "A", L1_A, "B", L1_B, L1_PHRASES, "A=20;B=60")


@register("FAR-CASCADE-L2-01")
def verify_far_cascade_l2_01(case: Case) -> VerificationResult:
    return _pair_level(case, "X", L2_X, "Y", L2_Y, L2_PHRASES, "X=200;Y=60")


@register("FAR-CASCADE-L3-01")
def verify_far_cascade_l3_01(case: Case) -> VerificationResult:
    gold, decoy = l3_answers()
    checks = _common_checks(case, gold, decoy, L3_PHRASES)
    checks.append(_check("l3-gold", gold, "ADJ=12;OPP=2"))
    checks.append(_check("l3-decoy", decoy, "ADJ=12;OPP=12"))
    return _result(case, checks)


@register("FAR-CASCADE-L4-01")
def verify_far_cascade_l4_01(case: Case) -> VerificationResult:
    gold, decoy = l4_answers()
    checks = _common_checks(case, gold, decoy, L4_PHRASES)
    checks.append(_check("l4-gold", gold, "P=8;Q=1"))
    checks.append(
        _check(
            "l4-lure-margin-arrests-collapse",
            collapse(L4_LOADS, L4_LURE_P, L4_STRUCK),
            1,
        )
    )
    checks.append(
        _check(
            "l4-equal-totals",
            (sum(L4_P), sum(L4_Q), sum(L4_LOADS)),
            (F(112), F(112), F(80)),
        )
    )
    return _result(case, checks)
