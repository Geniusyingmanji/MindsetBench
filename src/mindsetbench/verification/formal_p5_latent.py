from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from heapq import heappop, heappush

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register


@dataclass(frozen=True)
class AffineTransform:
    order: tuple[int, ...]
    xor_mask: int

    def apply(self, state: int) -> int:
        raw = f"{state:08b}"
        permuted = int("".join(raw[index - 1] for index in self.order), 2)
        return permuted ^ self.xor_mask


@dataclass(frozen=True)
class CalibrationLog:
    code: str
    before: int
    after: int


@dataclass(frozen=True)
class AffineProblem:
    catalogue: tuple[tuple[str, AffineTransform], ...]
    logs: tuple[CalibrationLog, ...]
    costs: tuple[tuple[str, int], ...]
    queries: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class Plan:
    cost: int
    codes: tuple[str, ...]
    final_state: int


def _transform(order: str, xor_mask: str = "00000000") -> AffineTransform:
    return AffineTransform(
        order=tuple(int(index) for index in order.split(",")),
        xor_mask=int(xor_mask, 2),
    )


CATALOGUE = (
    ("F1", _transform("2,3,4,5,6,7,8,1")),
    ("F2", _transform("8,1,2,3,4,5,6,7")),
    ("F3", _transform("8,7,6,5,4,3,2,1")),
    ("F4", _transform("2,1,4,3,6,5,8,7")),
    ("F5", _transform("1,2,3,4,5,6,7,8", "10110110")),
    ("F6", _transform("1,2,3,4,5,6,7,8", "01101001")),
    ("F7", _transform("2,4,1,3,6,8,5,7")),
    ("F8", _transform("4,1,6,2,8,3,7,5", "11001010")),
    ("F9", _transform("2,1,4,3,6,5,8,7", "00110101")),
)

SOURCE_CODEBOOK = (
    ("S1", "F3"),
    ("S2", "F2"),
    ("S3", "F1"),
    ("S4", "F5"),
    ("S5", "F4"),
    ("S6", "F7"),
    ("S7", "F8"),
    ("S8", "F6"),
)
SOURCE_COSTS = (
    ("S1", 2),
    ("S2", 1),
    ("S3", 2),
    ("S4", 2),
    ("S5", 2),
    ("S6", 4),
    ("S7", 5),
    ("S8", 6),
)
SOURCE_LOGS = (
    CalibrationLog("S1", 0b00100011, 0b11000100),
    CalibrationLog("S2", 0b01111100, 0b00111110),
    CalibrationLog("S3", 0b10001000, 0b00010001),
    CalibrationLog("S4", 0b00000000, 0b10110110),
    CalibrationLog("S5", 0b01000001, 0b10000010),
    CalibrationLog("S6", 0b10010000, 0b01100000),
    CalibrationLog("S7", 0b01101010, 0b11011101),
    CalibrationLog("S8", 0b01001110, 0b00100111),
)

CODE_RENAME = {
    "S1": "K6",
    "S2": "K3",
    "S3": "K8",
    "S4": "K1",
    "S5": "K7",
    "S6": "K4",
    "S7": "K2",
    "S8": "K5",
}
TARGET_CODEBOOK = (
    ("K2", "F8"),
    ("K7", "F9"),
    ("K3", "F2"),
    ("K5", "F6"),
    ("K8", "F1"),
    ("K1", "F5"),
    ("K6", "F3"),
    ("K4", "F7"),
)
TARGET_OLD_CODEBOOK = tuple(
    (CODE_RENAME[source_code], transform_name) for source_code, transform_name in SOURCE_CODEBOOK
)
TARGET_COSTS = tuple((CODE_RENAME[source_code], cost) for source_code, cost in SOURCE_COSTS)
TARGET_LOGS = (
    CalibrationLog("K2", 0b00100011, 0b11000100),
    CalibrationLog("K7", 0b10010111, 0b01011110),
    CalibrationLog("K3", 0b01101100, 0b00110110),
    CalibrationLog("K5", 0b00110100, 0b01011101),
    CalibrationLog("K8", 0b11001001, 0b10010011),
    CalibrationLog("K1", 0b11111110, 0b01001000),
    CalibrationLog("K6", 0b00010111, 0b11101000),
    CalibrationLog("K4", 0b11000101, 0b10101100),
)


def _source_problem() -> AffineProblem:
    return AffineProblem(
        catalogue=CATALOGUE[:8],
        logs=SOURCE_LOGS,
        costs=SOURCE_COSTS,
        queries=((0b00000001, 0b11100001),),
    )


def _target_problem() -> AffineProblem:
    return AffineProblem(
        catalogue=CATALOGUE,
        logs=TARGET_LOGS,
        costs=TARGET_COSTS,
        queries=(
            (0b00000001, 0b11100001),
            (0b01100011, 0b10110111),
            (0b01100101, 0b01101010),
        ),
    )


_TRANSFORM_PATTERN = re.compile(r"(F\d+)=P\(([1-8](?:,[1-8]){7})\)⊕([01]{8})")
_LOG_PATTERN = re.compile(r"([SK]\d+):([01]{8})→([01]{8})")
_COST_PATTERN = re.compile(r"([SK]\d+)\[(\d+)\]")


def _parse_problem(problem: str) -> AffineProblem:
    catalogue = tuple(
        (name, _transform(order, xor_mask))
        for name, order, xor_mask in _TRANSFORM_PATTERN.findall(problem)
    )
    try:
        log_section = problem.split("校准日志：", 1)[1].split("卡成本：", 1)[0]
        cost_and_query = problem.split("卡成本：", 1)[1]
        cost_section = cost_and_query.split("初态=", 1)[0]
    except IndexError as exc:
        raise ValueError("affine problem is missing a required section") from exc
    logs = tuple(
        CalibrationLog(code, int(before, 2), int(after, 2))
        for code, before, after in _LOG_PATTERN.findall(log_section)
    )
    costs = tuple((code, int(cost)) for code, cost in _COST_PATTERN.findall(cost_section))
    raw_queries = re.findall(
        r"Q(\d+):初态=([01]{8});目标=([01]{8})",
        cost_and_query,
    )
    if not catalogue or not logs or not costs or not raw_queries:
        raise ValueError("affine problem contains no parseable catalogue, logs, costs, or query")
    if len({name for name, _ in catalogue}) != len(catalogue):
        raise ValueError("affine problem contains duplicate transformation names")
    if len({log.code for log in logs}) != len(logs):
        raise ValueError("affine problem contains duplicate calibration codes")
    if len({code for code, _ in costs}) != len(costs):
        raise ValueError("affine problem contains duplicate cost codes")
    query_indexes = [int(index) for index, _, _ in raw_queries]
    if query_indexes != list(range(1, len(raw_queries) + 1)):
        raise ValueError("affine problem query indexes must be contiguous and ordered")
    return AffineProblem(
        catalogue=catalogue,
        logs=logs,
        costs=costs,
        queries=tuple((int(initial, 2), int(goal, 2)) for _, initial, goal in raw_queries),
    )


def _candidate_codebook(
    problem: AffineProblem,
) -> tuple[tuple[tuple[str, str], ...], ...]:
    catalogue = dict(problem.catalogue)
    candidate_names = {
        log.code: tuple(
            name
            for name, transform in catalogue.items()
            if transform.apply(log.before) == log.after
        )
        for log in problem.logs
    }
    assignments: list[tuple[tuple[str, str], ...]] = []

    def visit(index: int, used: frozenset[str], chosen: tuple[tuple[str, str], ...]) -> None:
        if index == len(problem.logs):
            assignments.append(chosen)
            return
        code = problem.logs[index].code
        for name in candidate_names[code]:
            if name not in used:
                visit(index + 1, used | {name}, (*chosen, (code, name)))

    visit(0, frozenset(), ())
    return tuple(assignments)


def _candidate_set_sizes(problem: AffineProblem) -> list[int]:
    catalogue = dict(problem.catalogue)
    return sorted(
        sum(transform.apply(log.before) == log.after for transform in catalogue.values())
        for log in problem.logs
    )


@cache
def _plans(
    problem: AffineProblem,
    codebook: tuple[tuple[str, str], ...],
    query_index: int,
    max_extra_cost: int = 0,
) -> tuple[Plan, ...]:
    transforms = dict(problem.catalogue)
    code_to_transform = dict(codebook)
    costs = problem.costs
    initial, goal = problem.queries[query_index]
    queue: list[tuple[int, tuple[str, ...], int, int]] = [(0, (), initial, 0)]
    best_by_state_and_used = {(initial, 0): 0}
    best_goal_cost: int | None = None
    plans: list[Plan] = []
    while queue:
        cost, path, state, used = heappop(queue)
        if cost != best_by_state_and_used.get((state, used)):
            continue
        if best_goal_cost is not None and cost > best_goal_cost + max_extra_cost:
            break
        if state == goal:
            best_goal_cost = cost if best_goal_cost is None else best_goal_cost
            plans.append(Plan(cost, path, state))
            continue
        for index, (code, action_cost) in enumerate(costs):
            if used & (1 << index):
                continue
            transform = transforms[code_to_transform[code]]
            next_state = transform.apply(state)
            next_used = used | (1 << index)
            next_cost = cost + action_cost
            key = (next_state, next_used)
            if next_cost > best_by_state_and_used.get(key, 10**18):
                continue
            best_by_state_and_used[key] = next_cost
            heappush(queue, (next_cost, (*path, code), next_state, next_used))
    return tuple(sorted(plans, key=lambda plan: (plan.cost, plan.codes)))


def _replay(
    problem: AffineProblem,
    codebook: tuple[tuple[str, str], ...],
    path: tuple[str, ...],
    query_index: int,
) -> int:
    transforms = dict(problem.catalogue)
    code_to_transform = dict(codebook)
    state = problem.queries[query_index][0]
    for code in path:
        state = transforms[code_to_transform[code]].apply(state)
    return state


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


def _gold(case: Case) -> str:
    return case.target.answer.legacy_value()


def _lure(case: Case) -> str:
    assert case.lure and case.lure.answer
    return case.lure.answer.legacy_value()


def _copy(case: Case) -> str:
    assert case.copy_probe
    return case.copy_probe.answer.legacy_value()


def _format_plans(plans: tuple[Plan, ...]) -> str:
    parts: list[str] = []
    for plan in plans:
        parts.extend((str(plan.cost), ">".join(plan.codes)))
    return ";".join(parts)


@register("HARD-P5-LATENT-L4-01")
def verify_hard_p5_latent_l4_01(case: Case) -> VerificationResult:
    source = _source_problem()
    target = _target_problem()
    parsed_source = _parse_problem(case.source.problem)
    parsed_target = _parse_problem(case.target.problem)
    source_assignments = _candidate_codebook(source)
    target_assignments = _candidate_codebook(target)
    source_best = tuple(
        _plans(source, SOURCE_CODEBOOK, query_index) for query_index in range(len(source.queries))
    )
    target_best = tuple(
        _plans(target, TARGET_CODEBOOK, query_index) for query_index in range(len(target.queries))
    )
    lure_best = tuple(
        _plans(target, TARGET_OLD_CODEBOOK, query_index)
        for query_index in range(len(target.queries))
    )
    target_near = tuple(
        _plans(target, TARGET_CODEBOOK, query_index, max_extra_cost=2)
        for query_index in range(len(target.queries))
    )
    source_near = tuple(
        _plans(source, SOURCE_CODEBOOK, query_index, max_extra_cost=1)
        for query_index in range(len(source.queries))
    )
    expected_source = (Plan(12, ("S3", "S7", "S2", "S4", "S5"), 0b11100001),)
    expected_target = (
        Plan(7, ("K6", "K7", "K1", "K3"), 0b11100001),
        Plan(11, ("K6", "K7", "K3", "K4", "K8"), 0b10110111),
        Plan(11, ("K4", "K7", "K3", "K6", "K8"), 0b01101010),
    )
    expected_lure = (
        Plan(12, ("K8", "K2", "K3", "K1", "K7"), 0b11100001),
        Plan(14, ("K7", "K4", "K2", "K6", "K3"), 0b10110111),
        Plan(10, ("K3", "K7", "K2", "K6"), 0b01101010),
    )
    renamed_source = dict(TARGET_OLD_CODEBOOK)
    target_codebook = dict(TARGET_CODEBOOK)
    broken = {
        code: (renamed_source[code], target_codebook[code])
        for code in renamed_source
        if renamed_source[code] != target_codebook[code]
    }
    old_path_actual = tuple(
        _replay(target, TARGET_CODEBOOK, plan.codes, query_index)
        for query_index, plan in enumerate(expected_lure)
    )
    checks = [
        _check("source-text-problem", parsed_source, source),
        _check("target-text-problem", parsed_target, target),
        _check(
            "source-individual-candidate-sizes",
            _candidate_set_sizes(source),
            [1, 1, 2, 2, 2, 2, 2, 3],
        ),
        _check(
            "target-individual-candidate-sizes",
            _candidate_set_sizes(target),
            [1, 1, 1, 1, 2, 2, 2, 3],
        ),
        _check("source-unique-global-codebook", source_assignments, (SOURCE_CODEBOOK,)),
        _check("target-unique-global-codebook", target_assignments, (TARGET_CODEBOOK,)),
        _check(
            "source-unique-optima",
            source_best,
            tuple((plan,) for plan in expected_source),
        ),
        _check(
            "target-unique-optima",
            target_best,
            tuple((plan,) for plan in expected_target),
        ),
        _check(
            "lure-unique-optima",
            lure_best,
            tuple((plan,) for plan in expected_lure),
        ),
        _check(
            "source-runner-up-margins",
            tuple(sorted({plan.cost for plan in plans}) for plans in source_near),
            ([12, 13],),
        ),
        _check(
            "target-runner-up-margins",
            tuple(sorted({plan.cost for plan in plans}) for plans in target_near),
            ([7, 9], [11, 12, 13], [11, 12, 13]),
        ),
        _check("single-broken-code-relation", broken, {"K7": ("F4", "F9")}),
        _check(
            "copied-source-plans-actual-states",
            tuple(f"{state:08b}" for state in old_path_actual),
            ("11010100", "01110001", "01011111"),
        ),
        _check(
            "copied-source-plans-miss-goals",
            tuple(state != target.queries[index][1] for index, state in enumerate(old_path_actual)),
            (True, True, True),
        ),
        _check("stored-source-answer", case.source.answer, _format_plans(expected_source)),
        _check("stored-target", _gold(case), _format_plans(expected_target)),
        _check("stored-lure", _lure(case), _format_plans(expected_lure)),
        _check("copy-equals-lure", _copy(case), _lure(case)),
        _check("copy-differs-from-target", _copy(case) != _gold(case), True),
    ]
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)
