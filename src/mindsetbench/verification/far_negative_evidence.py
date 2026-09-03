"""Executable verifiers for the far-transfer family ``far-negative-evidence-v1``.

Shared mindset: an observation that *fails* to show the expected signal cuts the
hypothesis space exactly as hard as one that shows it. Levels move from supply-chain
tracing (source, L0) through ward infection tracing (L1), deterministic-crash fault
localisation from a coverage matrix (L2), dating a chronicle by informative silence
(L3), to route reconstruction from camera traps with time windows (L4).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

VERIFIER = "far_negative_evidence"
SCHEMA_LEAK_TERMS = ("阴性证据", "可行集", "排除法", "假设空间", "沉默论证", "反证")


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


# --------------------------------------------------------------- set-cover tracing


def downstream(edges: Mapping[str, Iterable[str]], node: str) -> set[str]:
    """Everything reachable from ``node`` through the (acyclic) flow graph."""

    reached: set[str] = set()
    frontier = [node]
    while frontier:
        current = frontier.pop()
        for child in edges.get(current, ()):
            if child not in reached:
                reached.add(child)
                frontier.append(child)
    return reached


def consistent_sources(
    edges: Mapping[str, Iterable[str]],
    sources: Sequence[str],
    positives: Iterable[str],
    negatives: Iterable[str],
) -> list[str]:
    """Sources whose downstream covers every positive and touches no negative."""

    positive_set, negative_set = set(positives), set(negatives)
    return [
        source
        for source in sources
        if positive_set <= downstream(edges, source)
        and not (negative_set & downstream(edges, source))
    ]


def positives_only_candidates(
    edges: Mapping[str, Iterable[str]], sources: Sequence[str], positives: Iterable[str]
) -> list[str]:
    positive_set = set(positives)
    return [source for source in sources if positive_set <= downstream(edges, source)]


def most_tested_candidate(
    edges: Mapping[str, Iterable[str]],
    candidates: Sequence[str],
    tested: Iterable[str],
) -> str:
    """The domain shortcut: blame the candidate touching the most sampled items."""

    tested_set = set(tested)
    ranked = sorted(
        candidates,
        key=lambda source: (-len(downstream(edges, source) & tested_set), source),
    )
    top = [
        c
        for c in ranked
        if len(downstream(edges, c) & tested_set) == len(downstream(edges, ranked[0]) & tested_set)
    ]
    if len(top) != 1:
        raise ValueError(f"shortcut is not deterministic: {top}")
    return ranked[0]


@dataclass(frozen=True)
class TracingWorld:
    edges: dict[str, tuple[str, ...]]
    sources: tuple[str, ...]
    positives: tuple[str, ...]
    negatives: tuple[str, ...]

    def gold(self) -> str:
        consistent = consistent_sources(self.edges, self.sources, self.positives, self.negatives)
        if len(consistent) != 1:
            raise ValueError(f"tracing world is not uniquely solvable: {consistent}")
        return consistent[0]

    def decoy(self) -> str:
        candidates = positives_only_candidates(self.edges, self.sources, self.positives)
        if len(candidates) != 2:
            raise ValueError(f"positives alone must leave exactly two candidates: {candidates}")
        return most_tested_candidate(self.edges, candidates, (*self.positives, *self.negatives))


SOURCE_WORLD = TracingWorld(
    edges={
        "S1": ("M1",),
        "S2": ("M1", "M2"),
        "S3": ("M2", "M3"),
        "S4": ("M3", "M4"),
        "S5": ("M4",),
        "M1": ("P1", "P3"),
        "M2": ("P2", "P6"),
        "M3": ("P3", "P4"),
        "M4": ("P5", "P6"),
    },
    sources=("S1", "S2", "S3", "S4", "S5"),
    positives=("P2", "P6"),
    negatives=("P4", "P5"),
)
SOURCE_PHRASES = ("恰好一家供应商", "P4、P5 阴性", "P1、P3 未抽检")

L0_WORLD = TracingWorld(
    edges={
        "T1": ("M1",),
        "T2": ("M1", "M2"),
        "T3": ("M2", "M3"),
        "T4": ("M3",),
        "M1": ("Q1", "Q3"),
        "M2": ("Q2", "Q3", "Q5"),
        "M3": ("Q4", "Q5"),
    },
    sources=("T1", "T2", "T3", "T4"),
    positives=("Q3", "Q5"),
    negatives=("Q1",),
)
L0_PHRASES = ("Q3、Q5 阳性", "Q1 阴性", "Q2、Q4 未抽检")

L1_WORLD = TracingWorld(
    edges={
        "N1": ("W1",),
        "N2": ("W1", "W2"),
        "N3": ("W2", "W3"),
        "N4": ("W3",),
        "W1": ("p1", "p3", "p6"),
        "W2": ("p2", "p3", "p5"),
        "W3": ("p4", "p5"),
    },
    sources=("N1", "N2", "N3", "N4"),
    positives=("p3", "p5"),
    negatives=("p6",),
)
L1_PHRASES = ("p3、p5 检出", "p6 检测阴性", "只有一名护理人员")

# Fault localisation: tests are the observations, functions are the hypotheses.
L2_COVERAGE: dict[str, tuple[str, ...]] = {
    "T1": ("parse_header", "normalize_row"),
    "T2": ("parse_header", "normalize_row", "merge_batches"),
    "T3": ("render_report", "cache_lookup"),
    "T4": ("parse_header", "cache_lookup", "check_auth"),
    "T5": ("normalize_row", "merge_batches", "render_report"),
    "T6": ("merge_batches", "check_auth"),
    "T7": ("cache_lookup", "check_auth"),
}
L2_FAILED = ("T2", "T5")
L2_PASSED = ("T1", "T4")
L2_FUNCTIONS = (
    "parse_header",
    "normalize_row",
    "merge_batches",
    "render_report",
    "cache_lookup",
    "check_auth",
)
L2_PHRASES = ("确定性崩溃", "T2、T5 失败", "T1、T4 通过", "T3、T6、T7 未运行")


def _l2_world() -> TracingWorld:
    # function -> tests that execute it (the "downstream" of a hypothesis)
    edges = {
        function: tuple(test for test, covered in L2_COVERAGE.items() if function in covered)
        for function in L2_FUNCTIONS
    }
    return TracingWorld(edges=edges, sources=L2_FUNCTIONS, positives=L2_FAILED, negatives=L2_PASSED)


# ------------------------------------------------------------ L3: dating by silence


@dataclass(frozen=True)
class Event:
    name: str
    year: int
    mentioned: bool
    knowable: bool = True  # news reached the author in time
    in_scope: bool = True  # the chronicle's remit covers this kind of event


L3_EVENTS: tuple[Event, ...] = (
    Event("E1", 1462, mentioned=True),
    Event("E2", 1466, mentioned=True),
    Event("E3", 1471, mentioned=False),
    Event("E4", 1468, mentioned=False, knowable=False),
    Event("E5", 1469, mentioned=False, in_scope=False),
)
L3_PHRASES = ("1466", "1471", "1475 年才传至", "只记教会与主教座堂事务", "1469")


def dating_interval(
    events: Sequence[Event], *, informative_silence_only: bool
) -> tuple[int, int | None]:
    earliest = max(event.year for event in events if event.mentioned)
    upper_bounds = [
        event.year - 1
        for event in events
        if not event.mentioned
        and (not informative_silence_only or (event.knowable and event.in_scope))
    ]
    latest = min(upper_bounds) if upper_bounds else None
    return earliest, latest


# --------------------------------------------------------- L4: camera-trap routing


L4_EDGES: dict[frozenset[str], int] = {
    frozenset({"A", "B"}): 20,
    frozenset({"B", "F"}): 30,
    frozenset({"A", "C"}): 50,
    frozenset({"C", "F"}): 40,
    frozenset({"C", "D"}): 15,
    frozenset({"D", "F"}): 20,
    frozenset({"C", "E"}): 30,
    frozenset({"E", "F"}): 45,
    frozenset({"B", "C"}): 35,
}
L4_RECORDED: dict[str, int] = {"A": 6 * 60, "C": 6 * 60 + 50, "F": 8 * 60}
L4_SILENT_WORKING: tuple[str, ...] = ("B", "D")
L4_PHRASES = (
    "06:00",
    "06:50",
    "08:00",
    "B、D 两处相机整晨正常工作但没有任何记录",
    "E 处相机故障",
    "不会比标注时间更快",
)


def _neighbours(node: str) -> list[str]:
    return sorted(next(iter(edge - {node})) for edge in L4_EDGES if node in edge)


def simple_paths(start: str, goal: str) -> list[tuple[str, ...]]:
    paths: list[tuple[str, ...]] = []

    def walk(path: tuple[str, ...]) -> None:
        if path[-1] == goal:
            paths.append(path)
            return
        for nxt in _neighbours(path[-1]):
            if nxt not in path:
                walk((*path, nxt))

    walk((start,))
    return paths


def path_length(path: Sequence[str]) -> int:
    return sum(L4_EDGES[frozenset({a, b})] for a, b in pairwise(path))


def feasible(path: Sequence[str], *, use_silence: bool) -> bool:
    """Recorded cameras pin times (resting allowed); silent working cameras forbid passage."""

    if use_silence and any(node in L4_SILENT_WORKING for node in path):
        return False
    if not all(node in path for node in L4_RECORDED):
        return False
    clock = L4_RECORDED[path[0]]
    for previous, current in pairwise(path):
        clock += L4_EDGES[frozenset({previous, current})]
        if current in L4_RECORDED:
            if clock > L4_RECORDED[current]:
                return False
            clock = L4_RECORDED[current]
    return True


def route_answer(*, use_silence: bool, shortest: bool) -> str:
    candidates = [
        path for path in simple_paths("A", "F") if feasible(path, use_silence=use_silence)
    ]
    if shortest:
        candidates.sort(key=lambda path: (path_length(path), path))
        candidates = candidates[:1]
    if len(candidates) != 1:
        raise ValueError(f"route is not unique: {candidates}")
    return ">".join(candidates[0])


# ------------------------------------------------------------------- verifiers


def _source_checks(case: Case) -> list[VerificationCheck]:
    return [
        _check(
            "source-text-states-facts", _contains_all(case.source.problem, SOURCE_PHRASES), True
        ),
        _check("source-unique-supplier", SOURCE_WORLD.gold(), "S2"),
        _check("source-positives-only-alternative", SOURCE_WORLD.decoy(), "S3"),
        _check("stored-source-answer", case.source.answer, SOURCE_WORLD.gold()),
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


@register("FAR-NEG-L0-01")
def verify_far_neg_l0_01(case: Case) -> VerificationResult:
    checks = _common_checks(case, L0_WORLD.gold(), L0_WORLD.decoy(), L0_PHRASES)
    checks.append(_check("l0-gold", L0_WORLD.gold(), "T3"))
    return _result(case, checks)


@register("FAR-NEG-L1-01")
def verify_far_neg_l1_01(case: Case) -> VerificationResult:
    checks = _common_checks(case, L1_WORLD.gold(), L1_WORLD.decoy(), L1_PHRASES)
    checks.append(_check("l1-gold", L1_WORLD.gold(), "N3"))
    return _result(case, checks)


@register("FAR-NEG-L2-01")
def verify_far_neg_l2_01(case: Case) -> VerificationResult:
    world = _l2_world()
    gold = f"FAULT={world.gold()}"
    decoy = f"FAULT={world.decoy()}"
    checks = _common_checks(case, gold, decoy, L2_PHRASES)
    checks.append(_check("l2-gold", world.gold(), "merge_batches"))
    checks.append(_check("l2-decoy", world.decoy(), "normalize_row"))
    return _result(case, checks)


@register("FAR-NEG-L3-01")
def verify_far_neg_l3_01(case: Case) -> VerificationResult:
    earliest, latest = dating_interval(L3_EVENTS, informative_silence_only=True)
    naive_earliest, naive_latest = dating_interval(L3_EVENTS, informative_silence_only=False)
    gold = f"{earliest};{latest}"
    decoy = f"{naive_earliest};{naive_latest}"
    checks = _common_checks(case, gold, decoy, L3_PHRASES)
    checks.append(_check("l3-interval", (earliest, latest), (1466, 1470)))
    checks.append(_check("l3-naive-interval", (naive_earliest, naive_latest), (1466, 1467)))
    return _result(case, checks)


@register("FAR-NEG-L4-01")
def verify_far_neg_l4_01(case: Case) -> VerificationResult:
    gold = f"ROUTE={route_answer(use_silence=True, shortest=False)}"
    decoy = f"ROUTE={route_answer(use_silence=False, shortest=True)}"
    checks = _common_checks(case, gold, decoy, L4_PHRASES)
    checks.append(_check("l4-gold-route", gold, "ROUTE=A>C>F"))
    checks.append(_check("l4-decoy-route", decoy, "ROUTE=A>C>D>F"))
    timing_only = [p for p in simple_paths("A", "F") if feasible(p, use_silence=False)]
    checks.append(
        _check(
            "l4-silence-is-load-bearing",
            len(timing_only) > 1,
            True,
            detail=f"without the silent cameras {len(timing_only)} routes remain feasible",
        )
    )
    return _result(case, checks)
