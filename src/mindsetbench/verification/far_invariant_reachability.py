"""Executable verifiers for the far-transfer family ``far-invariant-reachability-v1``.

Shared mindset: every allowed move preserves some class (a parity, a permutation
sign, a linear combination of balances); a target in a different class is
unreachable no matter how many moves are tried, and the best reachable state is
the nearest member of the starting class. The decoy is the constructive instinct:
"it looks reachable, so it is".
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Sequence
from fractions import Fraction
from itertools import combinations

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

VERIFIER = "far_invariant_reachability"
SCHEMA_LEAK_TERMS = (
    "不变量",
    "守恒量",
    "奇偶性",
    "宇称",
    "置换的奇偶",
    "偶置换",
    "奇置换",
    "双射",
    "mod 2",
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


def _yes_no(flag: bool) -> str:
    return "YES" if flag else "NO"


# ------------------------------------------------ blackboard: replace a, b by |a-b|


def blackboard_finals(numbers: Iterable[int]) -> set[int]:
    """All values the last remaining number can take (exhaustive over multisets)."""

    start = tuple(sorted(numbers))
    seen = {start}
    frontier = [start]
    finals: set[int] = set()
    while frontier:
        state = frontier.pop()
        if len(state) == 1:
            finals.add(state[0])
            continue
        for i, j in combinations(range(len(state)), 2):
            rest = [v for k, v in enumerate(state) if k not in (i, j)]
            nxt = tuple(sorted([*rest, abs(state[i] - state[j])]))
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return finals


def blackboard_answer(numbers: Sequence[int]) -> str:
    finals = blackboard_finals(numbers)
    return f"ZERO={_yes_no(0 in finals)};MIN={min(finals)}"


SOURCE_NUMBERS = tuple(range(1, 10))
SOURCE_PHRASES = ("1 到 9", "两个数", "它们之差", "最后剩下一个数")
L0_NUMBERS = tuple(range(1, 11))
L0_PHRASES = ("1 到 10", "两个数", "之差")

# ------------------------------------------------------- cups: flip k of n at once


def cup_reachable_up_counts(cups: int, flip: int) -> set[int]:
    """Numbers of upright cups reachable from all-up when exactly ``flip`` cups flip."""

    seen = {cups}
    queue = deque([cups])
    while queue:
        up = queue.popleft()
        down = cups - up
        for from_up in range(0, flip + 1):
            from_down = flip - from_up
            if from_up <= up and from_down <= down:
                nxt = up - from_up + from_down
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
    return seen


def cups_answer(cups: int, flip: int) -> str:
    reachable = cup_reachable_up_counts(cups, flip)
    return f"ZERO={_yes_no(0 in reachable)};MIN={min(reachable)}"


L1_CUPS, L1_FLIP = 7, 4
L1_PHRASES = ("7 个杯子", "同时翻转其中 4 个", "全部口朝下")

# ------------------------------------------------------------- knight on a board


def knight_distances(start: tuple[int, int], size: int = 8) -> dict[tuple[int, int], int]:
    moves = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
    dist = {start: 0}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in moves:
            nxt = (x + dx, y + dy)
            if 0 <= nxt[0] < size and 0 <= nxt[1] < size and nxt not in dist:
                dist[nxt] = dist[(x, y)] + 1
                queue.append(nxt)
    return dist


def knight_answer(start: tuple[int, int], goal: tuple[int, int], asked_steps: int) -> str:
    """Can the knight reach ``goal`` in exactly ``asked_steps``? Plus the minimum."""

    distances = knight_distances(start)
    minimum = distances[goal]
    same_colour = (start[0] + start[1]) % 2 == (goal[0] + goal[1]) % 2
    exact_possible = (
        asked_steps >= minimum
        and ((asked_steps - minimum) % 2 == 0)
        and (same_colour == (asked_steps % 2 == 0))
    )
    return f"FIVE={_yes_no(exact_possible)};MIN={minimum}"


L2_START, L2_GOAL, L2_ASKED = (0, 0), (7, 7), 5
L2_PHRASES = ("a1", "h8", "恰好 5 步", "最少需要几步")

# ------------------------------------------- dancers: consecutive triple rotations


def rotation_distances(n: int) -> dict[tuple[int, ...], int]:
    """BFS over permutations using cyclic rotations of three consecutive positions."""

    start = tuple(range(1, n + 1))
    dist = {start: 0}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        for i in range(n - 2):
            a, b, c = state[i], state[i + 1], state[i + 2]
            for rotated in ((b, c, a), (c, a, b)):
                nxt = state[:i] + rotated + state[i + 3 :]
                if nxt not in dist:
                    dist[nxt] = dist[state] + 1
                    queue.append(nxt)
    return dist


def dancers_answer(n: int, odd_target: tuple[int, ...], even_target: tuple[int, ...]) -> str:
    dist = rotation_distances(n)
    reachable = odd_target in dist
    return f"SWAP={_yes_no(reachable)};DOUBLE={dist[even_target]}"


L3_N = 8
L3_ODD_TARGET = (2, 1, 3, 4, 5, 6, 7, 8)
L3_EVEN_TARGET = (2, 1, 4, 3, 5, 6, 7, 8)
L3_PHRASES = (
    "8 名舞者",
    "相邻三人",
    "轮转一个位置",
    "只交换 1 号与 2 号",
    "1 号与 2 号互换、3 号与 4 号互换",
)

# ------------------------------------------------- ledger: three balanced entries


def ledger_gap(start: tuple[int, int, int], target: tuple[int, int, int]) -> int:
    """现金 + 库存 - 应付 is preserved by every allowed entry; the gap is what a cash
    injection would have to add."""

    equity = lambda s: s[0] + s[1] - s[2]  # noqa: E731
    return equity(target) - equity(start)


def ledger_brute_force_reachable(
    start: tuple[int, int, int], target: tuple[int, int, int], limit: int = 120
) -> bool:
    """Independent check: search buy b, pay p, sell s in [0, limit]."""

    cash0, stock0, payable0 = start
    cash1, stock1, payable1 = target
    for b in range(limit + 1):
        for p in range(limit + 1):
            s = stock0 + b - stock1
            if s < 0:
                continue
            if cash0 - p + s == cash1 and payable0 + b - p == payable1:
                return True
    return False


L4_START = (50, 30, 20)
L4_TARGET = (40, 60, 35)
L4_PHRASES = ("现金 50", "库存 30", "应付 20", "现金 40", "库存 60", "应付 35")


def ledger_answer(start: tuple[int, int, int], target: tuple[int, int, int]) -> str:
    gap = ledger_gap(start, target)
    return f"REACHABLE={_yes_no(gap == 0)};GAP={abs(gap)}"


# ------------------------------------------------------------------- verifiers


def _source_checks(case: Case) -> list[VerificationCheck]:
    gold = blackboard_answer(SOURCE_NUMBERS)
    return [
        _check(
            "source-text-states-facts", _contains_all(case.source.problem, SOURCE_PHRASES), True
        ),
        _check("source-gold", gold, "ZERO=NO;MIN=1"),
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


@register("FAR-INVAR-L0-01")
def verify_far_invar_l0_01(case: Case) -> VerificationResult:
    gold = blackboard_answer(L0_NUMBERS)
    decoy = "ZERO=YES;MIN=0"
    checks = _common_checks(case, gold, decoy, L0_PHRASES)
    checks.append(_check("l0-gold", gold, "ZERO=NO;MIN=1"))
    return _result(case, checks)


@register("FAR-INVAR-L1-01")
def verify_far_invar_l1_01(case: Case) -> VerificationResult:
    gold = cups_answer(L1_CUPS, L1_FLIP)
    decoy = "ZERO=YES;MIN=0"
    checks = _common_checks(case, gold, decoy, L1_PHRASES)
    checks.append(_check("l1-gold", gold, "ZERO=NO;MIN=1"))
    checks.append(_check("l1-lure-world-flip-three", cups_answer(L1_CUPS, 3), decoy))
    return _result(case, checks)


@register("FAR-INVAR-L2-01")
def verify_far_invar_l2_01(case: Case) -> VerificationResult:
    gold = knight_answer(L2_START, L2_GOAL, L2_ASKED)
    decoy = "FIVE=YES;MIN=5"
    checks = _common_checks(case, gold, decoy, L2_PHRASES)
    checks.append(_check("l2-gold", gold, "FIVE=NO;MIN=6"))
    checks.append(
        _check("l2-lure-world-a1-to-h7", knight_answer(L2_START, (7, 6), L2_ASKED), decoy)
    )
    return _result(case, checks)


@register("FAR-INVAR-L3-01")
def verify_far_invar_l3_01(case: Case) -> VerificationResult:
    gold = dancers_answer(L3_N, L3_ODD_TARGET, L3_EVEN_TARGET)
    decoy = "SWAP=YES;DOUBLE=2"
    checks = _common_checks(case, gold, decoy, L3_PHRASES)
    checks.append(_check("l3-gold", gold, "SWAP=NO;DOUBLE=2"))
    dist = rotation_distances(L3_N)
    checks.append(
        _check(
            "l3-rotations-reach-exactly-half-of-the-formations",
            len(dist),
            20160,
            detail="only even permutations of 8 dancers are reachable",
        )
    )
    return _result(case, checks)


@register("FAR-INVAR-L4-01")
def verify_far_invar_l4_01(case: Case) -> VerificationResult:
    gold = ledger_answer(L4_START, L4_TARGET)
    decoy = "REACHABLE=YES;GAP=0"
    checks = _common_checks(case, gold, decoy, L4_PHRASES)
    checks.append(_check("l4-gold", gold, "REACHABLE=NO;GAP=5"))
    checks.append(
        _check(
            "l4-brute-force-agrees",
            ledger_brute_force_reachable(L4_START, L4_TARGET),
            False,
        )
    )
    checks.append(
        _check(
            "l4-lure-world-target-with-equal-equity",
            ledger_answer(L4_START, (45, 60, 45)),
            decoy,
            detail=f"equity {Fraction(L4_START[0] + L4_START[1] - L4_START[2])} preserved",
        )
    )
    return _result(case, checks)
