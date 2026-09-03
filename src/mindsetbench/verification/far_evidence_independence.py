"""Executable verifiers for the far-transfer family ``far-evidence-independence-v1``.

Shared mindset: agreeing signals that share one upstream source constitute one piece
of evidence. Each level re-derives gold, lure and copy-probe from a small formal
world (provenance roots, time-feasibility provenance, or common-cause probability)
instead of trusting the stored strings, and checks that the target text carries the
facts the derivation needs while naming neither the schema nor the method.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from itertools import product

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

VERIFIER = "far_evidence_independence"

#: Words that would hand the schema to the solver. Domain words such as 独立 alone are
#: allowed because policies naturally use them; the schema-level labels are not.
SCHEMA_LEAK_TERMS = ("独立见证", "共同上游", "共因", "来源链", "同源", "追根")


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


# --------------------------------------------------------------------------- provenance


def independent_roots(parents: Mapping[str, str | None]) -> set[str]:
    """Roots reached by following declared derivation links upward."""

    roots: set[str] = set()
    for node in parents:
        current = node
        hops = 0
        while parents.get(current) is not None:
            current = parents[current]  # type: ignore[assignment]
            hops += 1
            if hops > len(parents):
                raise ValueError(f"cyclic provenance at {node}")
        roots.add(current)
    return roots


def witness_grade(count: int) -> str:
    if count >= 3:
        return "确证"
    if count == 2:
        return "可信"
    return "孤证"


SOURCE_PARENTS: dict[str, str | None] = {
    "甲": None,
    "乙": "甲",
    "丙": "乙",
    "丁": None,
    "戊": None,
    "己": "丙",
}
SOURCE_PHRASES = ("悉据乾隆志", "采道光县志", "摘录光绪府志", "三个及以上独立见证")

L0_PARENTS: dict[str, str | None] = {"甲": "乙", "乙": None, "丙": "甲", "丁": None, "戊": "甲"}
L0_PHRASES = ("据咸丰志", "录自光绪县志", "据县志所载", "嘉庆七年")

L1_PARENTS: dict[str, str | None] = {
    "旧匾": None,
    "匾额": "旧匾",
    "口述": "族谱",
    "族谱": None,
    "林谱": "族谱",
    "文史资料": "族谱",
    "县志": "族谱",
}
L1_RECORD_COUNT = 6
L1_PHRASES = ("照旧匾摹刻", "查了族谱", "据陈氏旧谱", "据陈氏族谱", "采陈、林两谱")


def _source_checks(case: Case) -> list[VerificationCheck]:
    roots = independent_roots(SOURCE_PARENTS)
    gold = f"{len(roots)};{witness_grade(len(roots))}"
    return [
        _check(
            "source-text-states-provenance-rule",
            _contains_all(case.source.problem, SOURCE_PHRASES),
            True,
        ),
        _check("source-roots", sorted(roots), ["丁", "戊", "甲"]),
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
        # Same-domain anchors (L0/L1) legitimately reuse the discipline's own vocabulary;
        # cross-domain targets must not name the schema.
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


def _result(case: Case, checks: list[VerificationCheck]) -> VerificationResult:
    return VerificationResult(case_id=case.id, checks=checks, verifier=VERIFIER)


@register("FAR-INDEP-L0-01")
def verify_far_indep_l0_01(case: Case) -> VerificationResult:
    roots = independent_roots(L0_PARENTS)
    gold = f"{len(roots)};{witness_grade(len(roots))}"
    records = len(L0_PARENTS)
    decoy = f"{records};{witness_grade(records)}"
    checks = _common_checks(case, gold, decoy, L0_PHRASES)
    checks.append(_check("l0-roots", sorted(roots), ["丁", "乙"]))
    return _result(case, checks)


@register("FAR-INDEP-L1-01")
def verify_far_indep_l1_01(case: Case) -> VerificationResult:
    roots = independent_roots(L1_PARENTS)
    gold = f"{len(roots)};{witness_grade(len(roots))}"
    decoy = f"{L1_RECORD_COUNT};{witness_grade(L1_RECORD_COUNT)}"
    checks = _common_checks(case, gold, decoy, L1_PHRASES)
    checks.append(_check("l1-roots", sorted(roots), ["族谱", "旧匾"]))
    return _result(case, checks)


# ----------------------------------------------------------------------- L2: CI gate


L2_THRESHOLD = 4
L2_CHECK_ROOTS: dict[str, str] = {
    "lint": "src",
    "unit-core": "tests-core",
    "snapshot-api": "pr-fixtures",
    "snapshot-cli": "pr-fixtures",
    "snapshot-docs": "pr-fixtures",
    "contract": "pr-fixtures",
}
L2_REMEDIES: dict[str, Callable[[dict[str, str]], dict[str, str]]] = {
    "C1": lambda roots: {**roots, "snapshot-perf": "pr-fixtures"},
    "C2": lambda roots: {**roots, "contract": "main-fixtures"},
    "C3": lambda roots: dict(roots),
    "C4": lambda roots: {**roots, "typecheck": "mypy"},
}
L2_PHRASES = (
    "至少需要 4 个相互独立的绿色检查",
    "make snapshots",
    "expected_api.json 作为 oracle",
    "main 分支上的 expected_api.json",
)


def _independent_check_count(roots: Mapping[str, str]) -> int:
    return len(set(roots.values()))


def _yes_no(flag: bool) -> str:
    return "YES" if flag else "NO"


@register("FAR-INDEP-L2-01")
def verify_far_indep_l2_01(case: Case) -> VerificationResult:
    baseline = _independent_check_count(L2_CHECK_ROOTS)
    merge_ok = baseline >= L2_THRESHOLD
    remedy_flags = {
        name: (not merge_ok) and _independent_check_count(apply(L2_CHECK_ROOTS)) >= L2_THRESHOLD
        for name, apply in L2_REMEDIES.items()
    }
    gold = ";".join(
        [
            f"MERGE={_yes_no(merge_ok)}",
            *(f"{name}={_yes_no(flag)}" for name, flag in remedy_flags.items()),
        ]
    )
    green = len(L2_CHECK_ROOTS)
    decoy = ";".join(
        [f"MERGE={_yes_no(green >= L2_THRESHOLD)}", *(f"{name}=NO" for name in L2_REMEDIES)]
    )
    checks = _common_checks(case, gold, decoy, L2_PHRASES)
    checks.append(_check("l2-independent-checks", baseline, 3))
    checks.append(_check("l2-green-checks", green, 6))
    return _result(case, checks)


# ------------------------------------------------------------ L3: surgical clearance


@dataclass(frozen=True)
class Assessment:
    who: str
    signed: int
    primary: bool = False
    viewed_images: bool = False
    operating_surgeon: bool = False


def _minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


L3_THRESHOLD = 3
L3_IMAGES_AVAILABLE = _minutes("14:00")
L3_WORLD: tuple[Assessment, ...] = (
    Assessment("R", _minutes("10:30"), primary=True),
    Assessment("A", _minutes("11:20")),
    Assessment("B", _minutes("11:40")),
    Assessment("D", _minutes("12:05")),
    Assessment("C", _minutes("15:30"), viewed_images=True),
    Assessment("E", _minutes("16:00"), viewed_images=True, operating_surgeon=True),
)
L3_MEASURES: dict[str, Callable[[list[Assessment]], list[Assessment]]] = {
    "M1": lambda world: [*world, Assessment("F", _minutes("17:00"))],
    "M2": lambda world: [
        replace(item, signed=_minutes("17:00"), viewed_images=True) if item.who == "A" else item
        for item in world
    ],
    "M3": lambda world: list(world),  # pathology arrives tomorrow
    "M4": lambda world: list(world),  # same assessor, same evidence
    "M5": lambda world: list(world),  # a phone call is not primary evidence
    "M6": lambda world: [*world, Assessment("G", _minutes("17:30"), viewed_images=True)],
}
L3_PHRASES = ("14:00 起方可调阅", "拟主刀医师的评估", "11:20", "15:30", "明日 09:00")


def _independent_assessment(item: Assessment) -> bool:
    if item.operating_surgeon:
        return False
    if item.primary:
        return True
    return item.viewed_images and item.signed >= L3_IMAGES_AVAILABLE


def _independent_count(world: Sequence[Assessment]) -> int:
    return sum(1 for item in world if _independent_assessment(item))


@register("FAR-INDEP-L3-01")
def verify_far_indep_l3_01(case: Case) -> VerificationResult:
    baseline = _independent_count(L3_WORLD)
    schedule = baseline >= L3_THRESHOLD
    flags = {
        name: (not schedule) and _independent_count(apply(list(L3_WORLD))) >= L3_THRESHOLD
        for name, apply in L3_MEASURES.items()
    }
    gold = ";".join(
        [
            f"SCHEDULE={_yes_no(schedule)}",
            *(f"{name}={_yes_no(flag)}" for name, flag in flags.items()),
        ]
    )
    concurring = len(L3_WORLD)
    decoy = ";".join(
        [f"SCHEDULE={_yes_no(concurring >= L3_THRESHOLD)}", *(f"{name}=NO" for name in L3_MEASURES)]
    )
    checks = _common_checks(case, gold, decoy, L3_PHRASES)
    checks.append(_check("l3-independent-assessments", baseline, 2))
    checks.append(
        _check(
            "l3-partial-shortcut-also-wrong",
            sum(1 for item in L3_WORLD if not item.operating_surgeon) >= L3_THRESHOLD,
            True,
            detail="excluding only the surgeon still says YES; time feasibility is load-bearing",
        )
    )
    return _result(case, checks)


# ------------------------------------------------------- L4: common-cause reliability


L4_P = Fraction(1, 10)
L4_Q = Fraction(1, 20)


def failure_on_demand(
    per_sensor_miss: Sequence[Fraction],
    shares_reference: Sequence[bool],
    *,
    detections_needed: int,
    reference_fault: Fraction,
) -> Fraction:
    """P(fewer than ``detections_needed`` sensors detect) with a shared calibration fault."""

    def independent_failure(miss: Sequence[Fraction]) -> Fraction:
        total = Fraction(0)
        for outcome in product((True, False), repeat=len(miss)):
            probability = Fraction(1)
            for failed, p in zip(outcome, miss, strict=True):
                probability *= p if failed else 1 - p
            detections = sum(1 for failed in outcome if not failed)
            if detections < detections_needed:
                total += probability
        return total

    healthy_reference = independent_failure(per_sensor_miss)
    faulty_miss = [
        Fraction(1) if shared else p
        for p, shared in zip(per_sensor_miss, shares_reference, strict=True)
    ]
    faulty_reference = independent_failure(faulty_miss)
    return reference_fault * faulty_reference + (1 - reference_fault) * healthy_reference


def _four_places(value: Fraction) -> str:
    exact = Decimal(value.numerator) / Decimal(value.denominator)
    return str(exact.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


L4_OPTIONS: dict[str, tuple[list[Fraction], list[bool], int]] = {
    "A": ([L4_P] * 4, [True, True, False, True], 2),
    "B": ([L4_P] * 3, [True, False, False], 2),
    "C": ([L4_P, L4_P, Fraction(1, 20)], [True, True, False], 2),
}
L4_PHRASES = (
    "任意两只及以上报高液位",
    "同一台便携校准器 PC-7",
    "5% 的概率",
    "读低而漏报",
    "0.05 的高等级开关",
)


def _best_option(reference_fault: Fraction) -> tuple[str, dict[str, Fraction]]:
    values = {
        name: failure_on_demand(miss, shared, detections_needed=k, reference_fault=reference_fault)
        for name, (miss, shared, k) in L4_OPTIONS.items()
    }
    best = min(values, key=values.__getitem__)
    return best, values


@register("FAR-INDEP-L4-01")
def verify_far_indep_l4_01(case: Case) -> VerificationResult:
    current = failure_on_demand(
        [L4_P] * 3, [True, True, False], detections_needed=2, reference_fault=L4_Q
    )
    best, values = _best_option(L4_Q)
    gold = f"{_four_places(current)};{best}"
    naive_current = failure_on_demand(
        [L4_P] * 3, [False] * 3, detections_needed=2, reference_fault=Fraction(0)
    )
    naive_best, naive_values = _best_option(Fraction(0))
    decoy = f"{_four_places(naive_current)};{naive_best}"
    checks = _common_checks(case, gold, decoy, L4_PHRASES)
    checks.append(_check("l4-current-pfd", _four_places(current), "0.0766"))
    checks.append(
        _check(
            "l4-option-ranking",
            [name for name, _ in sorted(values.items(), key=lambda item: item[1])],
            ["B", "A", "C"],
            detail=", ".join(f"{name}={_four_places(value)}" for name, value in values.items()),
        )
    )
    checks.append(
        _check("l4-best-is-unique", len({value for value in values.values()}), len(values))
    )
    checks.append(
        _check(
            "l4-naive-best",
            naive_best,
            "A",
            detail=", ".join(f"{k}={_four_places(v)}" for k, v in naive_values.items()),
        )
    )
    return _result(case, checks)
