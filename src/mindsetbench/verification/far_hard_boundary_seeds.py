"""Executable worlds for the far-domain boundary and active-diagnosis seeds.

These cases deliberately mix positive transfer with boundary recognition.  The
stored gold is checked against a small world model; narrative surface details do
not determine the answer merely by sharing vocabulary with the source.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from fractions import Fraction

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

VERIFIER = "far_hard_boundary_seeds"
SCHEMA_LEAK_TERMS = (
    "信息增益",
    "决策树",
    "瓶颈迁移",
    "可信承诺",
    "阴性证据",
    "剩余地平线",
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


def _stored_checks(
    case: Case,
    *,
    source_answer: str,
    gold: str,
    lure: str,
    copy: str,
    phrases: Sequence[str],
) -> list[VerificationCheck]:
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None
    leaks = [term for term in SCHEMA_LEAK_TERMS if term in case.target.problem]
    return [
        _check("stored-source-answer", case.source.answer, source_answer),
        _check(
            "target-text-carries-required-facts",
            _contains_all(case.target.problem, phrases),
            True,
        ),
        _check("target-text-has-no-schema-label", leaks, []),
        _check("stored-target-answer", case.target.answer.legacy_value(), gold),
        _check("stored-lure-answer", case.lure.answer.legacy_value(), lure),
        _check("stored-copy-probe", case.copy_probe.answer.legacy_value(), copy),
        _check("copy-probe-differs-from-gold", copy != gold, True),
    ]


def _result(case: Case, checks: list[VerificationCheck]) -> VerificationResult:
    return VerificationResult(case_id=case.id, checks=checks, verifier=VERIFIER)


# ------------------------------------------------------ unusable information boundary


@register("FAR-HARD-BOUNDARY-INFO-L4-01")
def verify_boundary_info(case: Case) -> VerificationResult:
    safe = Fraction(74)
    high, low, p_high = Fraction(92), Fraction(40), Fraction(2, 5)
    blind = p_high * high + (1 - p_high) * low
    usable = p_high * high + (1 - p_high) * safe
    gold = f"PLAN={'A' if safe > blind else 'B'};EXPECTED={float(max(safe, blind)):.1f}"
    lure = f"PLAN={'B' if usable > safe else 'A'};EXPECTED={float(max(safe, usable)):.1f}"
    checks = _stored_checks(
        case,
        source_answer="TRY;50",
        gold=gold,
        lure=lure,
        copy=lure,
        phrases=("星期四 18:00", "星期一上午", "74", "92", "40", "四成"),
    )
    checks.extend(
        [
            _check("blind-experimental-value", blind, Fraction(304, 5)),
            _check("usable-report-value", usable, Fraction(406, 5)),
            _check("report-arrives-after-lock", safe > blind and usable > safe, True),
        ]
    )
    return _result(case, checks)


# ----------------------------------------------------------- control of reversal option


@register("FAR-HARD-BOUNDARY-COMMIT-L4-01")
def verify_boundary_commit(case: Case) -> VerificationResult:
    # Credible iff reversal requires another party's assent at the relevant time.
    unilateral_reversal = {"A": False, "B": True, "C": True, "D": False}
    gold = ";".join(
        f"{name}={'NO' if reversible else 'YES'}"
        for name, reversible in unilateral_reversal.items()
    )
    appearance_rule = {name: True for name in unilateral_reversal}
    decoy = ";".join(f"{name}={'YES' if flag else 'NO'}" for name, flag in appearance_rule.items())
    checks = _stored_checks(
        case,
        source_answer="C",
        gold=gold,
        lure=decoy,
        copy=decoy,
        phrases=("两人共同签字", "可单方向选举机关撤回", "已经支付且不退", "对方党团签字"),
    )
    checks.append(
        _check(
            "credible-packages",
            [key for key, reversible in unilateral_reversal.items() if not reversible],
            ["A", "D"],
        )
    )
    return _result(case, checks)


# ----------------------------------------------------------- adaptive archive diagnosis


ARCHIVE_PAPER: Mapping[str, str] = {"A": "RAG", "B": "RAG", "C": "PULP", "D": "PULP"}
ARCHIVE_LEDGER: Mapping[str, str] = {"A": "A", "B": "B", "C": "NONE", "D": "NONE"}
ARCHIVE_STOCK: Mapping[str, str] = {"A": "NONE", "B": "NONE", "C": "C", "D": "D"}


def _pair_partition(
    first: Mapping[str, str], branches: Mapping[str, Mapping[str, str]]
) -> set[tuple[str, str]]:
    return {
        (first[hypothesis], branches[first[hypothesis]][hypothesis])
        for hypothesis in first
    }


@register("FAR-HARD-DIAG-ARCHIVE-L3-01")
def verify_archive_policy(case: Case) -> VerificationResult:
    branches = {"RAG": ARCHIVE_LEDGER, "PULP": ARCHIVE_STOCK}
    observations = _pair_partition(ARCHIVE_PAPER, branches)
    gold = "FIRST=PAPER;IF_RAG=LEDGER;IF_PULP=STOCK"
    decoy = "FIRST=STYLE;IF_RAG=NONE;IF_PULP=NONE"
    checks = _stored_checks(
        case,
        source_answer="FIRST=SCREEN;IF_RED=A;IF_BLUE=B",
        gold=gold,
        lure=decoy,
        copy=decoy,
        phrases=("只剩两个整天", "棉料纸", "木浆纸", "隔夜列车", "要用掉两个整天"),
    )
    checks.extend(
        [
            _check("adaptive-policy-signatures", len(observations), 4),
            _check("adaptive-policy-covers-hypotheses", len(ARCHIVE_PAPER), 4),
        ]
    )
    return _result(case, checks)


# ------------------------------------------------------------- moving bottleneck plan


BASE_CAPACITY = {"INTAKE": 18, "VERIFY": 9, "HEARING": 12}
HIRE_GAIN = {"INTAKE": 8, "VERIFY": 5, "HEARING": 6}


def _capacity(hire_sequence: Sequence[str]) -> int:
    capacities = dict(BASE_CAPACITY)
    for hire in hire_sequence:
        capacities[hire] += HIRE_GAIN[hire]
    return min(capacities.values())


def _two_quarter_total(first: str, second: str) -> int:
    return _capacity((first,)) + _capacity((first, second))


@register("FAR-HARD-BOTTLENECK-L4-01")
def verify_bottleneck_plan(case: Case) -> VerificationResult:
    roles = tuple(BASE_CAPACITY)
    totals = {
        (first, second): _two_quarter_total(first, second)
        for first in roles
        for second in roles
    }
    best = max(totals.values())
    winners = [plan for plan, total in totals.items() if total == best]
    gold = f"FIRST={winners[0][0]};SECOND={winners[0][1]};TOTAL={best}"
    decoy_total = totals[("VERIFY", "VERIFY")]
    decoy = f"FIRST=VERIFY;SECOND=VERIFY;TOTAL={decoy_total}"
    checks = _stored_checks(
        case,
        source_answer="PACK;OVEN;39",
        gold=gold,
        lure=decoy,
        copy=decoy,
        phrases=("18 件", "9 件", "12 件", "第一笔", "第二笔"),
    )
    checks.extend(
        [
            _check("unique-two-quarter-plan", winners, [("VERIFY", "HEARING")]),
            _check("optimal-two-quarter-total", best, 26),
            _check("repeat-current-constraint-total", decoy_total, 24),
        ]
    )
    return _result(case, checks)


# ---------------------------------------------------- absence outside recording scope


@register("FAR-HARD-BOUNDARY-ABSENCE-L4-01")
def verify_absence_boundary(case: Case) -> VerificationResult:
    permit_records_cast = False
    absence_changes_odds = permit_records_cast
    gold = f"EFFECT={'AGAINST' if absence_changes_odds else 'NONE'};NEXT=PAYROLL"
    decoy = "EFFECT=AGAINST;NEXT=MORE_PERMITS"
    checks = _stored_checks(
        case,
        source_answer="EXCLUDE=B",
        gold=gold,
        lure=decoy,
        copy=decoy,
        phrases=("86 份", "只填“许可证持有人”", "拥有产业且为男性", "5 份都记有女性演员"),
    )
    checks.append(_check("permit-form-could-record-cast", permit_records_cast, False))
    return _result(case, checks)


# ------------------------------------------------ strategic-response diagnostic policy


COALITION_RESPONSES: Mapping[str, Mapping[str, str]] = {
    "POLICY": {"P": "ACCEPT", "O": "REJECT", "S": "REJECT"},
    "OFFICE": {"P": "REJECT", "O": "ACCEPT", "S": "REJECT"},
    "GRAND": {"P": "ACCEPT", "O": "ACCEPT", "S": "REJECT"},
}


@register("FAR-HARD-DIAG-COALITION-L4-01")
def verify_coalition_policy(case: Case) -> VerificationResult:
    # OFFICE is procedurally available only after POLICY has been rejected.
    signatures = {
        hypothesis: (
            COALITION_RESPONSES["POLICY"][hypothesis],
            COALITION_RESPONSES["OFFICE"][hypothesis]
            if COALITION_RESPONSES["POLICY"][hypothesis] == "REJECT"
            else "STOP",
        )
        for hypothesis in ("P", "O", "S")
    }
    gold = "FIRST=POLICY;IF_REJECT=OFFICE"
    decoy = "FIRST=GRAND;IF_REJECT=NONE"
    checks = _stored_checks(
        case,
        source_answer="FIRST=SCREEN;IF_RED=A;IF_BLUE=B",
        gold=gold,
        lure=decoy,
        copy=decoy,
        phrases=("政策型", "职位型", "搅局型", "第二次也是最后一次", "才允许谈职位"),
    )
    checks.extend(
        [
            _check("policy-signatures-distinct", len(set(signatures.values())), 3),
            _check(
                "grand-bargain-confounds-types",
                COALITION_RESPONSES["GRAND"]["P"],
                COALITION_RESPONSES["GRAND"]["O"],
            ),
        ]
    )
    return _result(case, checks)
