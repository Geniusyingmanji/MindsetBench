"""Executable verifiers for the far-transfer family ``far-delayed-feedback-v1``.

Shared mindset: when the effect of a correction (or the reading it is based on)
arrives with a delay, correcting the full observed error every period overshoots
and oscillates; the gentler correction that never crosses the target is the one
that settles. The decoy is the memoryless instinct "close the whole gap now".
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

VERIFIER = "far_delayed_feedback"
SCHEMA_LEAK_TERMS = (
    "过调",
    "振荡",
    "滞后反馈",
    "控制论",
    "PID",
    "牛鞭",
    "串稳定",
    "阻尼",
    "反馈回路",
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


def _num(value: Fraction, places: int = 1) -> str:
    text = f"{float(value):.{places}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


# ------------------------------------------------- delayed proportional correction


def simulate_errors(e0: Fraction, gain: Fraction, delay: int, horizon: int) -> list[Fraction]:
    """e_{t+1} = e_t - gain * e_{t-delay}; readings older than t=0 equal the initial error."""

    errors = [e0]
    for t in range(horizon):
        lagged = errors[t - delay] if t - delay >= 0 else e0
        errors.append(errors[t] - gain * lagged)
    return errors


def settle_step(errors: Sequence[Fraction], band: Fraction) -> int | None:
    """First step from which |e| stays within the band through the horizon."""

    for start in range(1, len(errors)):
        if all(abs(e) <= band for e in errors[start:]):
            return start
    return None


def overshoots(errors: Sequence[Fraction], band: Fraction) -> bool:
    """Starting below target (e0 < 0), crossing above the band counts as overshoot."""

    return any(e > band for e in errors[1:])


def admissible_gain(
    gains: Sequence[Fraction], *, e0: Fraction, delay: int, horizon: int, band: Fraction
) -> tuple[Fraction, int]:
    hits: list[tuple[Fraction, int]] = []
    for gain in gains:
        errors = simulate_errors(e0, gain, delay, horizon)
        settled = settle_step(errors, band)
        if settled is not None and not overshoots(errors, band):
            hits.append((gain, settled))
    if len(hits) != 1:
        raise ValueError(f"expected exactly one admissible gain, got {hits}")
    return hits[0]


def _gain_str(gain: Fraction) -> str:
    text = f"{float(gain):.2f}".rstrip("0")
    return text + "0" if text.endswith(".") else text


def gain_answer(gain: Fraction, settled: int) -> str:
    return f"GAIN={_gain_str(gain)};SETTLE={settled}"


def full_correction_decoy(gains: Sequence[Fraction]) -> str:
    """Memoryless instinct: the largest gain closes the gap in one step."""

    return f"GAIN={_gain_str(max(gains))};SETTLE=1"


SOURCE_GAINS = (F(1), F(1, 2), F(1, 5))
SOURCE_E0, SOURCE_DELAY, SOURCE_HORIZON, SOURCE_BAND = F(-20), 2, 12, F(1)
SOURCE_PHRASES = ("滞后两步", "1.0、0.5、0.2", "39 到 41", "12 步")

L0_GAINS = (F(1), F(3, 5), F(3, 10))
L0_E0, L0_DELAY, L0_HORIZON, L0_BAND = F(-20), 1, 12, F(1)
L0_PHRASES = ("滞后一步", "1.0、0.6、0.3", "39 到 41")

L1_GAINS = (F(1), F(2, 5), F(1, 10))
L1_E0, L1_DELAY, L1_HORIZON, L1_BAND = F(-20), 3, 20, F(1)
L1_PHRASES = ("三个周期前", "1.0、0.4、0.1", "19 到 21", "20 个周期")

L2_GAINS = (F(1), F(1, 2), F(1, 5))
L2_E0, L2_DELAY, L2_HORIZON, L2_BAND = F(-400), 1, 12, F(20)
L2_PHRASES = ("下单两周后", "上一周周一盘点时也是 200", "1.0、0.5、0.2", "580 到 620", "12 周")


# ---------------------------------------------- L3: correction against a decaying level


def simulate_decay(
    *, target: Fraction, decay: Fraction, gain: Fraction, delay: int, steps: int
) -> list[Fraction]:
    """x_{t+1} = (1-decay) x_t + gain * (target - x_{t-delay}); doses before t=0 are zero."""

    levels = [F(0)]
    for t in range(steps):
        lagged = levels[t - delay] if t - delay >= 0 else F(0)
        dose = gain * (target - lagged) if t - delay >= 0 else F(0)
        levels.append((1 - decay) * levels[t] + dose)
    return levels


def steady_level(target: Fraction, decay: Fraction, gain: Fraction) -> Fraction:
    return gain * target / (decay + gain)


L3_TARGET, L3_DECAY, L3_GAIN, L3_DELAY = F(100), F(1, 5), F(3, 10), 1
L3_PHRASES = ("每个周期消散 20%", "0.3 倍", "下一个周期", "目标 100")


# ------------------------------------------- L4: reaction chain (string amplification)


def simulate_platoon(
    *,
    gain: Fraction,
    cars: int,
    steps: int,
    cruise: Fraction,
    dip: Fraction,
    dip_from: int,
    dip_len: int,
) -> list[list[Fraction]]:
    """Car 0 follows a fixed profile; car i changes speed by gain times the speed gap to
    car i-1 as it was one step ago (a one-step reaction delay on both readings)."""

    speeds = [[cruise] * cars]
    for t in range(steps):
        current = speeds[t]
        previous = speeds[t - 1] if t >= 1 else speeds[0]
        leader = cruise - dip if dip_from <= t + 1 < dip_from + dip_len else cruise
        nxt = [leader]
        for i in range(1, cars):
            nxt.append(current[i] + gain * (previous[i - 1] - previous[i]))
        speeds.append(nxt)
    return speeds


def max_dip(speeds: Sequence[Sequence[Fraction]], car: int, cruise: Fraction) -> Fraction:
    return cruise - min(row[car] for row in speeds)


L4_GAINS = (F(1), F(3, 5), F(3, 10))
L4_CARS, L4_STEPS, L4_CRUISE, L4_DIP, L4_DIP_FROM, L4_DIP_LEN = 5, 30, F(60), F(10), 2, 2
L4_PHRASES = ("60 公里", "50 公里", "第 2 秒末", "1.0、0.6、0.3", "第五辆")


def platoon_answer(gain: Fraction) -> tuple[Fraction, Fraction]:
    speeds = simulate_platoon(
        gain=gain,
        cars=L4_CARS,
        steps=L4_STEPS,
        cruise=L4_CRUISE,
        dip=L4_DIP,
        dip_from=L4_DIP_FROM,
        dip_len=L4_DIP_LEN,
    )
    return max_dip(speeds, 0, L4_CRUISE), max_dip(speeds, L4_CARS - 1, L4_CRUISE)


def attenuating_gain() -> tuple[Fraction, Fraction]:
    hits = []
    for gain in L4_GAINS:
        lead, tail = platoon_answer(gain)
        if tail <= lead:
            hits.append((gain, tail))
    if len(hits) != 1:
        raise ValueError(f"expected exactly one attenuating gain, got {hits}")
    return hits[0]


# ------------------------------------------------------------------- verifiers


def _source_checks(case: Case) -> list[VerificationCheck]:
    gain, settled = admissible_gain(
        SOURCE_GAINS, e0=SOURCE_E0, delay=SOURCE_DELAY, horizon=SOURCE_HORIZON, band=SOURCE_BAND
    )
    return [
        _check(
            "source-text-states-facts", _contains_all(case.source.problem, SOURCE_PHRASES), True
        ),
        _check("source-answer", gain_answer(gain, settled), "GAIN=0.2;SETTLE=6"),
        _check("stored-source-answer", case.source.answer, gain_answer(gain, settled)),
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


def _gain_level(
    case: Case,
    gains: Sequence[Fraction],
    *,
    e0: Fraction,
    delay: int,
    horizon: int,
    band: Fraction,
    phrases: Sequence[str],
    expected: str,
) -> VerificationResult:
    gain, settled = admissible_gain(gains, e0=e0, delay=delay, horizon=horizon, band=band)
    gold = gain_answer(gain, settled)
    decoy = full_correction_decoy(gains)
    checks = _common_checks(case, gold, decoy, phrases)
    checks.append(_check("gold-value", gold, expected))
    full = simulate_errors(e0, max(gains), delay, horizon)
    checks.append(
        _check(
            "full-correction-never-settles",
            settle_step(full, band),
            None,
            detail=", ".join(_num(e) for e in full[:8]),
        )
    )
    # without any delay the decoy would be right: the schema is about the lag
    checks.append(
        _check("decoy-correct-without-delay", simulate_errors(e0, max(gains), 0, 3)[1], F(0))
    )
    return _result(case, checks)


@register("FAR-DELAY-L0-01")
def verify_far_delay_l0_01(case: Case) -> VerificationResult:
    return _gain_level(
        case,
        L0_GAINS,
        e0=L0_E0,
        delay=L0_DELAY,
        horizon=L0_HORIZON,
        band=L0_BAND,
        phrases=L0_PHRASES,
        expected="GAIN=0.3;SETTLE=5",
    )


@register("FAR-DELAY-L1-01")
def verify_far_delay_l1_01(case: Case) -> VerificationResult:
    return _gain_level(
        case,
        L1_GAINS,
        e0=L1_E0,
        delay=L1_DELAY,
        horizon=L1_HORIZON,
        band=L1_BAND,
        phrases=L1_PHRASES,
        expected="GAIN=0.1;SETTLE=18",
    )


@register("FAR-DELAY-L2-01")
def verify_far_delay_l2_01(case: Case) -> VerificationResult:
    return _gain_level(
        case,
        L2_GAINS,
        e0=L2_E0,
        delay=L2_DELAY,
        horizon=L2_HORIZON,
        band=L2_BAND,
        phrases=L2_PHRASES,
        expected="GAIN=0.2;SETTLE=10",
    )


@register("FAR-DELAY-L3-01")
def verify_far_delay_l3_01(case: Case) -> VerificationResult:
    steady = steady_level(L3_TARGET, L3_DECAY, L3_GAIN)
    maintenance = L3_DECAY * L3_TARGET
    gold = f"STEADY={_num(steady)};MAINT={_num(maintenance)}"
    decoy = f"STEADY={_num(L3_TARGET)};MAINT=0"
    checks = _common_checks(case, gold, decoy, L3_PHRASES)
    levels = simulate_decay(
        target=L3_TARGET, decay=L3_DECAY, gain=L3_GAIN, delay=L3_DELAY, steps=60
    )
    checks.append(_check("l3-steady-level", _num(steady), "60"))
    checks.append(
        _check(
            "l3-simulation-converges-to-steady",
            abs(levels[-1] - steady) < F(1, 100),
            True,
            detail=f"x_60={_num(levels[-1], 3)}",
        )
    )
    return _result(case, checks)


@register("FAR-DELAY-L4-01")
def verify_far_delay_l4_01(case: Case) -> VerificationResult:
    gain, tail = attenuating_gain()
    gold = f"GAIN={_gain_str(gain)};{float(tail):.1f}"
    full_lead, full_tail = platoon_answer(max(L4_GAINS))
    decoy = f"GAIN={_gain_str(max(L4_GAINS))};{float(L4_DIP):.1f}"
    checks = _common_checks(case, gold, decoy, L4_PHRASES)
    checks.append(_check("l4-gold", gold, "GAIN=0.3;3.1"))
    checks.append(
        _check(
            "l4-full-reaction-amplifies",
            full_tail > full_lead,
            True,
            detail=f"lead dip {_num(full_lead)}, tail dip {_num(full_tail)}",
        )
    )
    return _result(case, checks)
