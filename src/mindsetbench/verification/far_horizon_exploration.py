"""Executable verifiers for the far-transfer family ``far-horizon-exploration-v1``.

Shared mindset: trying the uncertain option loses value today and only pays through
the periods that remain afterwards, so whether to try is decided by the remaining
horizon, not by the option's informed value alone. Every level asks for the first
action under a short and a long horizon plus the minimal horizon that justifies the
trial; the decoy is the stationary rule "the informed value is higher, so try now".
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

VERIFIER = "far_horizon_exploration"
SCHEMA_LEAK_TERMS = ("探索", "利用", "信息价值", "地平线", "试探价值", "多臂", "期权价值")


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


def _fmt(value: Fraction) -> str:
    text = f"{float(value):.1f}"
    return text[:-2] if text.endswith(".0") else text


# ------------------------------------------------------- repeated-period trial model


@dataclass(frozen=True)
class TrialWorld:
    """Known option paying ``safe`` per period versus an unknown option revealed by trial.

    ``trial_periods`` periods on the unknown option reveal whether it is ``good`` or
    ``poor``; switching back after a poor trial costs ``washout`` periods paying zero.
    """

    safe: Fraction
    p_good: Fraction
    good: Fraction
    poor: Fraction
    trial_periods: int = 1
    washout: int = 0

    def stay_value(self, horizon: int) -> Fraction:
        return self.safe * horizon

    def try_value(self, horizon: int) -> Fraction:
        if horizon < self.trial_periods:
            # a trial that cannot finish is just the unknown option's blind expectation
            return (self.p_good * self.good + (1 - self.p_good) * self.poor) * horizon
        trial = (self.p_good * self.good + (1 - self.p_good) * self.poor) * self.trial_periods
        remaining = horizon - self.trial_periods
        good_branch = self.good * remaining
        poor_remaining = max(remaining - self.washout, 0)
        poor_branch = max(self.poor * remaining, self.safe * poor_remaining)
        return trial + self.p_good * good_branch + (1 - self.p_good) * poor_branch

    def should_try(self, horizon: int) -> bool:
        return self.try_value(horizon) > self.stay_value(horizon)

    def min_horizon(self, limit: int = 60) -> int | None:
        for horizon in range(1, limit + 1):
            if self.should_try(horizon):
                return horizon
        return None

    def optimal_value(self, horizon: int) -> Fraction:
        return max(self.try_value(horizon), self.stay_value(horizon))


def decision_answer(
    world: TrialWorld,
    *,
    labels: tuple[str, str],
    short: int,
    long: int,
    keys: tuple[str, str, str],
) -> str:
    """``labels`` = (try-label, stay-label)."""

    try_label, stay_label = labels
    first_short = try_label if world.should_try(short) else stay_label
    first_long = try_label if world.should_try(long) else stay_label
    minimum = world.min_horizon()
    return f"{keys[0]}={first_short};{keys[1]}={first_long};{keys[2]}={minimum}"


def stationary_decoy(labels: tuple[str, str], keys: tuple[str, str, str]) -> str:
    """'The informed option is better, so try it now' regardless of horizon."""

    try_label, _ = labels
    return f"{keys[0]}={try_label};{keys[1]}={try_label};{keys[2]}=1"


F = Fraction

SOURCE_WORLD = TrialWorld(safe=F(12), p_good=F(2, 5), good=F(25), poor=F(2))
SOURCE_PHRASES = ("稳定获得 12 单位", "40% 的可能是 25 单位", "去灌丛觅食一天就能确知", "剩余 N 天")

L0_WORLD = TrialWorld(safe=F(16), p_good=F(3, 10), good=F(30), poor=F(1))
L0_LURE = TrialWorld(safe=F(16), p_good=F(3, 10), good=F(30), poor=F(16))
L0_LABELS = ("BUSH", "GRASS")
L0_KEYS = ("DAY1_SHORT", "DAY1_LONG", "MIN_DAYS")
L0_SHORT, L0_LONG = 2, 5
L0_PHRASES = ("16 单位", "30% 的可能是 30 单位", "剩 2 天", "剩 5 天")

L1_WORLD = TrialWorld(safe=F(8), p_good=F(3, 10), good=F(20), poor=F(1))
L1_LURE = TrialWorld(safe=F(8), p_good=F(3, 10), good=F(20), poor=F(8))
L1_LABELS = ("NEW", "OLD")
L1_KEYS = ("DAY1_SHORT", "DAY1_LONG", "MIN_DAYS")
L1_SHORT, L1_LONG = 1, 4
L1_PHRASES = ("8 筐", "三成把握是 20 筐", "只剩 1 天", "还有 4 天")

L2_WORLD = TrialWorld(safe=F(14), p_good=F(2, 5), good=F(30), poor=F(2))
L2_LURE = TrialWorld(safe=F(14), p_good=F(2, 5), good=F(30), poor=F(14))
L2_LABELS = ("NEW", "OLD")
L2_KEYS = ("SITE_A", "SITE_B", "MIN_WEEKS")
L2_SHORT, L2_LONG = 1, 6
L2_PHRASES = (
    "9 月 8 日",
    "9 月 14 日",
    "10 月 19 日",
    "稳定完成 14 个点位",
    "四成机会是每周 30 个",
)

L3_WORLD = TrialWorld(safe=F(12), p_good=F(2, 5), good=F(25), poor=F(2), trial_periods=2, washout=1)
L3_LURE = TrialWorld(safe=F(12), p_good=F(2, 5), good=F(25), poor=F(2))
L3_LABELS = ("B", "A")
L3_KEYS = ("WEEK1_SHORT", "WEEK1_LONG", "MIN_WEEKS")
L3_SHORT, L3_LONG = 3, 8
L3_PHRASES = ("连用两周才能判断", "一周洗脱期", "评分为 0", "还有 3 周", "还有 8 周")


# ------------------------------------------------------ one-shot deadline fallback


@dataclass(frozen=True)
class SubmissionWorld:
    sure_value: Fraction
    sure_months: int
    risky_value: Fraction
    risky_p: Fraction
    risky_months: int
    parallel: bool = False  # lure: the sure venue can run in parallel

    def sure_first(self, months: int) -> Fraction:
        return self.sure_value if months >= self.sure_months else F(0)

    def risky_first(self, months: int) -> Fraction:
        if months < self.risky_months:
            return F(0)
        fallback_ok = self.parallel or months >= self.risky_months + self.sure_months
        return self.risky_p * self.risky_value + (
            (1 - self.risky_p) * self.sure_value if fallback_ok else F(0)
        )

    def first_choice(self, months: int) -> str:
        return "A" if self.risky_first(months) > self.sure_first(months) else "B"

    def min_months_for_risky(self, limit: int = 60) -> int | None:
        for months in range(1, limit + 1):
            if self.first_choice(months) == "A":
                return months
        return None


L4_WORLD = SubmissionWorld(
    sure_value=F(12), sure_months=2, risky_value=F(25), risky_p=F(2, 5), risky_months=3
)
L4_LURE = SubmissionWorld(
    sure_value=F(12),
    sure_months=2,
    risky_value=F(25),
    risky_p=F(2, 5),
    risky_months=3,
    parallel=True,
)
L4_KEYS = ("FIRST_N4", "FIRST_N6", "MIN_MONTHS")
L4_SHORT, L4_LONG = 4, 6
L4_PHRASES = ("审稿 2 个月", "审稿 3 个月", "录用概率 40%", "改投 B", "还有 4 个月", "还有 6 个月")


def submission_answer(world: SubmissionWorld) -> str:
    return (
        f"{L4_KEYS[0]}={world.first_choice(L4_SHORT)};"
        f"{L4_KEYS[1]}={world.first_choice(L4_LONG)};"
        f"{L4_KEYS[2]}={world.min_months_for_risky()}"
    )


# ------------------------------------------------------------------- verifiers


def _source_checks(case: Case) -> list[VerificationCheck]:
    minimum = SOURCE_WORLD.min_horizon()
    value = SOURCE_WORLD.optimal_value(6)
    return [
        _check(
            "source-text-states-facts", _contains_all(case.source.problem, SOURCE_PHRASES), True
        ),
        _check("source-threshold", minimum, 2),
        _check("source-value-n6", _fmt(value), "97.2"),
        _check("stored-source-answer", case.source.answer, f"{minimum};{_fmt(value)}"),
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


def _trial_level(
    case: Case,
    world: TrialWorld,
    lure: TrialWorld,
    labels: tuple[str, str],
    keys: tuple[str, str, str],
    short: int,
    long: int,
    phrases: Sequence[str],
    expected_min: int,
) -> VerificationResult:
    gold = decision_answer(world, labels=labels, short=short, long=long, keys=keys)
    decoy = stationary_decoy(labels, keys)
    lure_answer = decision_answer(lure, labels=labels, short=short, long=long, keys=keys)
    checks = _common_checks(case, gold, decoy, phrases)
    checks.append(_check("lure-world-makes-decoy-correct", lure_answer, decoy))
    checks.append(_check("min-horizon", world.min_horizon(), expected_min))
    checks.append(
        _check(
            "short-horizon-flips-decision",
            (world.should_try(short), world.should_try(long)),
            (False, True),
            detail=(
                f"try/stay at short={_fmt(world.try_value(short))}/{_fmt(world.stay_value(short))}"
            ),
        )
    )
    return _result(case, checks)


@register("FAR-HORIZON-L0-01")
def verify_far_horizon_l0_01(case: Case) -> VerificationResult:
    return _trial_level(
        case, L0_WORLD, L0_LURE, L0_LABELS, L0_KEYS, L0_SHORT, L0_LONG, L0_PHRASES, 3
    )


@register("FAR-HORIZON-L1-01")
def verify_far_horizon_l1_01(case: Case) -> VerificationResult:
    return _trial_level(
        case, L1_WORLD, L1_LURE, L1_LABELS, L1_KEYS, L1_SHORT, L1_LONG, L1_PHRASES, 2
    )


@register("FAR-HORIZON-L2-01")
def verify_far_horizon_l2_01(case: Case) -> VerificationResult:
    return _trial_level(
        case, L2_WORLD, L2_LURE, L2_LABELS, L2_KEYS, L2_SHORT, L2_LONG, L2_PHRASES, 2
    )


@register("FAR-HORIZON-L3-01")
def verify_far_horizon_l3_01(case: Case) -> VerificationResult:
    gold = decision_answer(L3_WORLD, labels=L3_LABELS, short=L3_SHORT, long=L3_LONG, keys=L3_KEYS)
    # copy probe: reuse the source's one-week, free-switch structure -> threshold 2
    decoy = decision_answer(L3_LURE, labels=L3_LABELS, short=L3_SHORT, long=L3_LONG, keys=L3_KEYS)
    checks = _common_checks(case, gold, decoy, L3_PHRASES)
    checks.append(_check("l3-min-weeks", L3_WORLD.min_horizon(), 4))
    checks.append(_check("l3-copied-threshold", L3_LURE.min_horizon(), 2))
    checks.append(
        _check(
            "l3-adaptation-flips-short-horizon",
            (L3_WORLD.should_try(L3_SHORT), L3_LURE.should_try(L3_SHORT)),
            (False, True),
        )
    )
    return _result(case, checks)


@register("FAR-HORIZON-L4-01")
def verify_far_horizon_l4_01(case: Case) -> VerificationResult:
    gold = submission_answer(L4_WORLD)
    decoy = submission_answer(L4_LURE)
    checks = _common_checks(case, gold, decoy, L4_PHRASES)
    checks.append(_check("l4-gold", gold, "FIRST_N4=B;FIRST_N6=A;MIN_MONTHS=5"))
    checks.append(_check("l4-decoy", decoy, "FIRST_N4=A;FIRST_N6=A;MIN_MONTHS=3"))
    checks.append(
        _check(
            "l4-values",
            (
                _fmt(L4_WORLD.risky_first(4)),
                _fmt(L4_WORLD.sure_first(4)),
                _fmt(L4_WORLD.risky_first(6)),
            ),
            ("10", "12", "17.2"),
        )
    )
    return _result(case, checks)


__all__: list[str] = [
    "SubmissionWorld",
    "TrialWorld",
    "decision_answer",
    "stationary_decoy",
    "submission_answer",
]
