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

L0_CODEBOOK = (("A1", "F1"), ("A2", "F2"), ("A3", "F5"), ("A4", "F3"))
L0_COSTS = (("A1", 1), ("A2", 2), ("A3", 3), ("A4", 4))
L0_LOGS = (
    CalibrationLog("A1", 0b00000001, 0b00000010),
    CalibrationLog("A2", 0b00000010, 0b00000001),
    CalibrationLog("A3", 0b00000000, 0b10110110),
    CalibrationLog("A4", 0b00000010, 0b01000000),
)

L1_CODEBOOK = (("B1", "F2"), ("B2", "F4"), ("B3", "F1"), ("B4", "F3"))
L1_COSTS = (("B1", 2), ("B2", 3), ("B3", 1), ("B4", 4))
L1_LOGS = (
    CalibrationLog("B1", 0b00000001, 0b10000000),
    CalibrationLog("B2", 0b00000010, 0b00000001),
    CalibrationLog("B3", 0b00000001, 0b00000010),
    CalibrationLog("B4", 0b00000010, 0b01000000),
)

L2_CODEBOOK = (
    ("K2", "F8"),
    ("K7", "F4"),
    ("K3", "F2"),
    ("K5", "F6"),
    ("K8", "F1"),
    ("K1", "F5"),
    ("K6", "F3"),
    ("K4", "F7"),
)
L2_LOGS = (
    CalibrationLog("K2", 0b01101010, 0b11011101),
    CalibrationLog("K7", 0b01000001, 0b10000010),
    CalibrationLog("K3", 0b01111100, 0b00111110),
    CalibrationLog("K5", 0b01001110, 0b00100111),
    CalibrationLog("K8", 0b10001000, 0b00010001),
    CalibrationLog("K1", 0b00000000, 0b10110110),
    CalibrationLog("K6", 0b00100011, 0b11000100),
    CalibrationLog("K4", 0b10010000, 0b01100000),
)

SET_CODE_RENAME = {
    "K1": "T4",
    "K2": "T7",
    "K3": "T2",
    "K4": "T8",
    "K5": "T1",
    "K6": "T5",
    "K7": "T3",
    "K8": "T6",
}
L4_CATALOGUE = tuple((name.replace("F", "G"), transform) for name, transform in CATALOGUE)
L4_CODEBOOK = tuple(
    (SET_CODE_RENAME[code], transform.replace("F", "G")) for code, transform in TARGET_CODEBOOK
)
L4_OLD_CODEBOOK = tuple(
    (SET_CODE_RENAME[code], transform.replace("F", "G")) for code, transform in L2_CODEBOOK
)
L4_COSTS = tuple((SET_CODE_RENAME[code], cost) for code, cost in TARGET_COSTS)
L4_LOGS = tuple(
    CalibrationLog(SET_CODE_RENAME[log.code], log.before, log.after) for log in TARGET_LOGS
)
L4_CODEBOOK_BY_CARD = tuple(sorted(L4_CODEBOOK, key=lambda item: int(item[0][1:])))
L4_OLD_CODEBOOK_BY_CARD = tuple(sorted(L4_OLD_CODEBOOK, key=lambda item: int(item[0][1:])))


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


def _target_l0_problem() -> AffineProblem:
    return AffineProblem(
        catalogue=tuple(item for item in CATALOGUE if item[0] in {"F1", "F2", "F3", "F5"}),
        logs=L0_LOGS,
        costs=L0_COSTS,
        queries=((0b00000000, 0b11011010),),
    )


def _target_l1_problem() -> AffineProblem:
    return AffineProblem(
        catalogue=CATALOGUE[:4],
        logs=L1_LOGS,
        costs=L1_COSTS,
        queries=((0b00000001, 0b00100000),),
    )


def _target_l2_problem() -> AffineProblem:
    return AffineProblem(
        catalogue=CATALOGUE[:8],
        logs=L2_LOGS,
        costs=TARGET_COSTS,
        queries=((0b00000001, 0b11100001),),
    )


def _target_l3_problem() -> AffineProblem:
    target = _target_problem()
    return AffineProblem(
        catalogue=target.catalogue,
        logs=target.logs,
        costs=target.costs,
        queries=target.queries[:1],
    )


def _target_l4_problem() -> AffineProblem:
    target = _target_problem()
    return AffineProblem(
        catalogue=L4_CATALOGUE,
        logs=L4_LOGS,
        costs=L4_COSTS,
        queries=target.queries,
    )


def _source_three_query_problem() -> AffineProblem:
    return AffineProblem(
        catalogue=CATALOGUE[:8],
        logs=(),
        costs=SOURCE_COSTS,
        queries=(
            (0b00000001, 0b11100001),
            (0b01100011, 0b10110111),
            (0b01100101, 0b01101010),
        ),
    )


_TRANSFORM_PATTERN = re.compile(r"(F\d+)=P\(([1-8](?:,[1-8]){7})\)⊕([01]{8})")
_LOG_PATTERN = re.compile(r"([A-Z]\d+):([01]{8})→([01]{8})")
_COST_PATTERN = re.compile(r"([A-Z]\d+)\[(\d+)\]")
_SET_PATTERN = r"\{(?:[a-h](?:,[a-h])*)?\}|∅"
_SET_TRANSFORM_PATTERN = re.compile(rf"(G\d+)=取\(([a-h](?:,[a-h]){{7}})\)△({_SET_PATTERN})")
_SET_LOG_PATTERN = re.compile(rf"([A-Z]\d+):({_SET_PATTERN})→({_SET_PATTERN})")


def _set_to_int(raw: str) -> int:
    if raw in {"∅", "{}"}:
        return 0
    labels = raw.removeprefix("{").removesuffix("}").split(",")
    if len(set(labels)) != len(labels):
        raise ValueError("set state contains duplicate labels")
    return sum(1 << (7 - (ord(label) - ord("a"))) for label in labels)


def _parse_set_problem(problem: str) -> AffineProblem:
    catalogue = tuple(
        (
            name,
            AffineTransform(
                order=tuple(ord(label) - ord("a") + 1 for label in order.split(",")),
                xor_mask=_set_to_int(toggle),
            ),
        )
        for name, order, toggle in _SET_TRANSFORM_PATTERN.findall(problem)
    )
    try:
        log_section = problem.split("观测记录：", 1)[1].split("卡成本：", 1)[0]
        cost_and_query = problem.split("卡成本：", 1)[1]
        cost_section = cost_and_query.split("初集=", 1)[0]
    except IndexError as exc:
        raise ValueError("set-affine problem is missing a required section") from exc
    logs = tuple(
        CalibrationLog(code, _set_to_int(before), _set_to_int(after))
        for code, before, after in _SET_LOG_PATTERN.findall(log_section)
    )
    costs = tuple((code, int(cost)) for code, cost in _COST_PATTERN.findall(cost_section))
    raw_queries = re.findall(
        rf"Q(\d+):初集=({_SET_PATTERN});目标集=({_SET_PATTERN})",
        cost_and_query,
    )
    if not catalogue or not logs or not costs or not raw_queries:
        raise ValueError("set-affine problem contains an empty required section")
    if len({name for name, _ in catalogue}) != len(catalogue):
        raise ValueError("set-affine problem contains duplicate transformation names")
    if len({log.code for log in logs}) != len(logs):
        raise ValueError("set-affine problem contains duplicate observation codes")
    if len({code for code, _ in costs}) != len(costs):
        raise ValueError("set-affine problem contains duplicate cost codes")
    query_indexes = [int(index) for index, _, _ in raw_queries]
    if query_indexes != list(range(1, len(raw_queries) + 1)):
        raise ValueError("set-affine problem query indexes must be contiguous and ordered")
    return AffineProblem(
        catalogue=catalogue,
        logs=logs,
        costs=costs,
        queries=tuple(
            (_set_to_int(initial), _set_to_int(goal)) for _, initial, goal in raw_queries
        ),
    )


_CODEBOOK_PATTERN = re.compile(r"([A-Z]\d+)=(F\d+|G\d+)")


def _parse_observation_problem(problem: str) -> AffineProblem:
    """Parse catalogue and logs for a codebook-only diagnostic task."""

    if "观测记录：" in problem:
        catalogue = tuple(
            (
                name,
                AffineTransform(
                    order=tuple(ord(label) - ord("a") + 1 for label in order.split(",")),
                    xor_mask=_set_to_int(toggle),
                ),
            )
            for name, order, toggle in _SET_TRANSFORM_PATTERN.findall(problem)
        )
        log_section = problem.split("观测记录：", 1)[1].split("求唯一", 1)[0]
        logs = tuple(
            CalibrationLog(code, _set_to_int(before), _set_to_int(after))
            for code, before, after in _SET_LOG_PATTERN.findall(log_section)
        )
    else:
        catalogue = tuple(
            (name, _transform(order, xor_mask))
            for name, order, xor_mask in _TRANSFORM_PATTERN.findall(problem)
        )
        try:
            log_section = problem.split("校准日志：", 1)[1].split("求唯一", 1)[0]
        except IndexError as exc:
            raise ValueError("observation problem is missing its calibration logs") from exc
        logs = tuple(
            CalibrationLog(code, int(before, 2), int(after, 2))
            for code, before, after in _LOG_PATTERN.findall(log_section)
        )
    if not catalogue or not logs:
        raise ValueError("observation problem contains an empty catalogue or log section")
    if len({name for name, _ in catalogue}) != len(catalogue):
        raise ValueError("observation problem contains duplicate transformation names")
    if len({log.code for log in logs}) != len(logs):
        raise ValueError("observation problem contains duplicate observation codes")
    return AffineProblem(catalogue=catalogue, logs=logs, costs=(), queries=())


def _parse_explicit_planning_problem(
    problem: str,
) -> tuple[AffineProblem, tuple[tuple[str, str], ...]]:
    """Parse a planning probe whose latent codebook is supplied explicitly."""

    if "初集=" in problem:
        catalogue = tuple(
            (
                name,
                AffineTransform(
                    order=tuple(ord(label) - ord("a") + 1 for label in order.split(",")),
                    xor_mask=_set_to_int(toggle),
                ),
            )
            for name, order, toggle in _SET_TRANSFORM_PATTERN.findall(problem)
        )
        raw_queries = re.findall(
            rf"Q(\d+):初集=({_SET_PATTERN});目标集=({_SET_PATTERN})",
            problem,
        )
        queries = tuple(
            (_set_to_int(initial), _set_to_int(goal)) for _, initial, goal in raw_queries
        )
    else:
        catalogue = tuple(
            (name, _transform(order, xor_mask))
            for name, order, xor_mask in _TRANSFORM_PATTERN.findall(problem)
        )
        raw_queries = re.findall(
            r"Q(\d+):初态=([01]{8});目标=([01]{8})",
            problem,
        )
        queries = tuple((int(initial, 2), int(goal, 2)) for _, initial, goal in raw_queries)
    try:
        codebook_section = problem.split("代码本：", 1)[1].split("卡成本：", 1)[0]
        cost_section = problem.split("卡成本：", 1)[1].split("Q1:", 1)[0]
    except IndexError as exc:
        raise ValueError("explicit planning problem is missing codebook or costs") from exc
    codebook = tuple(_CODEBOOK_PATTERN.findall(codebook_section))
    costs = tuple((code, int(cost)) for code, cost in _COST_PATTERN.findall(cost_section))
    if not catalogue or not codebook or not costs or not queries:
        raise ValueError("explicit planning problem contains an empty required section")
    if len({name for name, _ in catalogue}) != len(catalogue):
        raise ValueError("explicit planning problem contains duplicate transformation names")
    if len({code for code, _ in codebook}) != len(codebook):
        raise ValueError("explicit planning problem contains duplicate codebook entries")
    if len({code for code, _ in costs}) != len(costs):
        raise ValueError("explicit planning problem contains duplicate cost codes")
    query_indexes = [int(index) for index, _, _ in raw_queries]
    if query_indexes != list(range(1, len(raw_queries) + 1)):
        raise ValueError("explicit planning query indexes must be contiguous and ordered")
    return (
        AffineProblem(catalogue=catalogue, logs=(), costs=costs, queries=queries),
        codebook,
    )


def _parse_problem(problem: str) -> AffineProblem:
    if "初集=" in problem:
        return _parse_set_problem(problem)
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


@dataclass(frozen=True)
class ChainLevelSpec:
    target: AffineProblem
    codebook: tuple[tuple[str, str], ...]
    expected_plans: tuple[Plan, ...]
    lure_plans: tuple[Plan, ...]
    candidate_sizes: tuple[int, ...]
    near_costs: tuple[tuple[int, ...], ...]
    lure_actual_states: tuple[int, ...]
    lure_kind: str


CHAIN_LEVEL_SPECS = {
    0: ChainLevelSpec(
        target=_target_l0_problem(),
        codebook=L0_CODEBOOK,
        expected_plans=(Plan(8, ("A3", "A4", "A1"), 0b11011010),),
        lure_plans=(Plan(8, ("A1", "A4", "A3"), 0b11011010),),
        candidate_sizes=(1, 1, 1, 1),
        near_costs=((8, 9, 10),),
        lure_actual_states=(0b10110110,),
        lure_kind="reverse-composition",
    ),
    1: ChainLevelSpec(
        target=_target_l1_problem(),
        codebook=L1_CODEBOOK,
        expected_plans=(Plan(7, ("B3", "B4", "B1"), 0b00100000),),
        lure_plans=(Plan(7, ("B1", "B4", "B3"), 0b00100000),),
        candidate_sizes=(1, 2, 2, 2),
        near_costs=((7, 8, 9),),
        lure_actual_states=(0b00000010,),
        lure_kind="reverse-composition",
    ),
    2: ChainLevelSpec(
        target=_target_l2_problem(),
        codebook=L2_CODEBOOK,
        expected_plans=(Plan(12, ("K8", "K2", "K3", "K1", "K7"), 0b11100001),),
        lure_plans=(Plan(12, ("K7", "K1", "K3", "K2", "K8"), 0b11100001),),
        candidate_sizes=(1, 1, 2, 2, 2, 2, 2, 3),
        near_costs=((12, 13, 14),),
        lure_actual_states=(0b10110010,),
        lure_kind="reverse-composition",
    ),
    3: ChainLevelSpec(
        target=_target_l3_problem(),
        codebook=TARGET_CODEBOOK,
        expected_plans=(Plan(7, ("K6", "K7", "K1", "K3"), 0b11100001),),
        lure_plans=(Plan(12, ("K8", "K2", "K3", "K1", "K7"), 0b11100001),),
        candidate_sizes=(1, 1, 1, 1, 2, 2, 2, 3),
        near_costs=((7, 9),),
        lure_actual_states=(0b11010100,),
        lure_kind="stale-codebook",
    ),
    4: ChainLevelSpec(
        target=_target_l4_problem(),
        codebook=L4_CODEBOOK,
        expected_plans=(
            Plan(7, ("T5", "T3", "T4", "T2"), 0b11100001),
            Plan(11, ("T5", "T3", "T2", "T8", "T6"), 0b10110111),
            Plan(11, ("T8", "T3", "T2", "T5", "T6"), 0b01101010),
        ),
        lure_plans=(
            Plan(12, ("T6", "T7", "T2", "T4", "T3"), 0b11100001),
            Plan(14, ("T3", "T8", "T7", "T5", "T2"), 0b10110111),
            Plan(10, ("T2", "T3", "T7", "T5"), 0b01101010),
        ),
        candidate_sizes=(1, 1, 1, 1, 2, 2, 2, 3),
        near_costs=((7, 9), (11, 12, 13), (11, 12, 13)),
        lure_actual_states=(0b11010100, 0b01110001, 0b01011111),
        lure_kind="stale-codebook",
    ),
}


def _verify_chain_level(case: Case, level: int) -> VerificationResult:
    spec = CHAIN_LEVEL_SPECS[level]
    source = _source_problem()
    parsed_source = _parse_problem(case.source.problem)
    parsed_target = _parse_problem(case.target.problem)
    source_assignments = _candidate_codebook(source)
    target_assignments = _candidate_codebook(spec.target)
    target_best = tuple(
        _plans(spec.target, spec.codebook, query_index)
        for query_index in range(len(spec.target.queries))
    )
    target_near = tuple(
        _plans(spec.target, spec.codebook, query_index, max_extra_cost=2)
        for query_index in range(len(spec.target.queries))
    )
    lure_actual = tuple(
        _replay(spec.target, spec.codebook, plan.codes, query_index)
        for query_index, plan in enumerate(spec.lure_plans)
    )
    if spec.lure_kind == "reverse-composition":
        lure_relation: object = tuple(
            plan.codes == tuple(reversed(gold.codes))
            for plan, gold in zip(spec.lure_plans, spec.expected_plans, strict=True)
        )
        expected_lure_relation: object = tuple(True for _ in spec.lure_plans)
    else:
        old_codebook = L4_OLD_CODEBOOK if level == 4 else L2_CODEBOOK
        lure_best = tuple(
            _plans(spec.target, old_codebook, query_index)
            for query_index in range(len(spec.target.queries))
        )
        lure_relation = lure_best
        expected_lure_relation = tuple((plan,) for plan in spec.lure_plans)

    target_transform_names = dict(spec.codebook)
    if level < 3:
        adaptation_check: object = len(set(target_transform_names.values()))
        expected_adaptation: object = len(target_transform_names)
    elif level == 3:
        old = dict(L2_CODEBOOK)
        adaptation_check = {
            code: (old[code], target_transform_names[code])
            for code in old
            if old[code] != target_transform_names[code]
        }
        expected_adaptation = {"K7": ("F4", "F9")}
    else:
        old = dict(L4_OLD_CODEBOOK)
        adaptation_check = {
            code: (old[code], target_transform_names[code])
            for code in old
            if old[code] != target_transform_names[code]
        }
        expected_adaptation = {"T3": ("G4", "G9")}

    checks = [
        _check("source-text-problem", parsed_source, source),
        _check("target-text-problem", parsed_target, spec.target),
        _check(
            "source-unique-global-codebook",
            source_assignments,
            (SOURCE_CODEBOOK,),
        ),
        _check(
            "target-individual-candidate-sizes",
            tuple(_candidate_set_sizes(spec.target)),
            spec.candidate_sizes,
        ),
        _check(
            "target-unique-global-codebook",
            target_assignments,
            (spec.codebook,),
        ),
        _check(
            "target-unique-optima",
            target_best,
            tuple((plan,) for plan in spec.expected_plans),
        ),
        _check(
            "target-runner-up-costs",
            tuple(tuple(sorted({plan.cost for plan in plans})) for plans in target_near),
            spec.near_costs,
        ),
        _check("lure-model-solution", lure_relation, expected_lure_relation),
        _check("level-adaptation-structure", adaptation_check, expected_adaptation),
        _check("lure-plans-actual-states", lure_actual, spec.lure_actual_states),
        _check(
            "lure-plans-miss-goals",
            tuple(
                state != spec.target.queries[index][1] for index, state in enumerate(lure_actual)
            ),
            tuple(True for _ in lure_actual),
        ),
        _check("stored-source-answer", case.source.answer, "12;S3>S7>S2>S4>S5"),
        _check("stored-target", _gold(case), _format_plans(spec.expected_plans)),
        _check("stored-lure", _lure(case), _format_plans(spec.lure_plans)),
        _check("copy-equals-lure", _copy(case), _lure(case)),
        _check("copy-differs-from-target", _copy(case) != _gold(case), True),
    ]
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


@register("FORMAL-P5-LATENT-L0-01")
def verify_formal_p5_latent_l0_01(case: Case) -> VerificationResult:
    return _verify_chain_level(case, 0)


@register("FORMAL-P5-LATENT-L1-01")
def verify_formal_p5_latent_l1_01(case: Case) -> VerificationResult:
    return _verify_chain_level(case, 1)


@register("FORMAL-P5-LATENT-L2-01")
def verify_formal_p5_latent_l2_01(case: Case) -> VerificationResult:
    return _verify_chain_level(case, 2)


@register("FORMAL-P5-LATENT-L3-01")
def verify_formal_p5_latent_l3_01(case: Case) -> VerificationResult:
    return _verify_chain_level(case, 3)


@register("FORMAL-P5-LATENT-L4-01")
def verify_formal_p5_latent_l4_01(case: Case) -> VerificationResult:
    return _verify_chain_level(case, 4)


def _format_codebook(codebook: tuple[tuple[str, str], ...], unused: str) -> str:
    ordered = sorted(codebook, key=lambda item: int(item[0][1:]))
    return ";".join([*(f"{code}={name}" for code, name in ordered), f"UNUSED={unused}"])


@register("DIAG-P5-LATENT-L4-ID-01")
def verify_diag_p5_latent_l4_id_01(case: Case) -> VerificationResult:
    source = AffineProblem(CATALOGUE[:8], SOURCE_LOGS, (), ())
    target = AffineProblem(L4_CATALOGUE, L4_LOGS, (), ())
    parsed_source = _parse_observation_problem(case.source.problem)
    parsed_target = _parse_observation_problem(case.target.problem)
    source_assignments = _candidate_codebook(source)
    target_assignments = _candidate_codebook(target)
    target_used = {name for _, name in L4_CODEBOOK}
    unused = tuple(name for name, _ in L4_CATALOGUE if name not in target_used)
    old = dict(L4_OLD_CODEBOOK_BY_CARD)
    current = dict(L4_CODEBOOK_BY_CARD)
    broken = {code: (old[code], current[code]) for code in old if old[code] != current[code]}
    checks = [
        _check("source-observation-text", parsed_source, source),
        _check("target-observation-text", parsed_target, target),
        _check(
            "source-candidate-sizes",
            tuple(_candidate_set_sizes(source)),
            (1, 1, 2, 2, 2, 2, 2, 3),
        ),
        _check(
            "target-candidate-sizes",
            tuple(_candidate_set_sizes(target)),
            (1, 1, 1, 1, 2, 2, 2, 3),
        ),
        _check("source-unique-codebook", source_assignments, (SOURCE_CODEBOOK,)),
        _check("target-unique-codebook", target_assignments, (L4_CODEBOOK,)),
        _check("target-unused-transform", unused, ("G4",)),
        _check("single-codebook-edit", broken, {"T3": ("G4", "G9")}),
        _check(
            "stored-source-answer",
            case.source.answer,
            _format_codebook(SOURCE_CODEBOOK, "NONE"),
        ),
        _check("stored-target", _gold(case), _format_codebook(L4_CODEBOOK, "G4")),
        _check("stored-lure", _lure(case), _format_codebook(L4_OLD_CODEBOOK, "G9")),
        _check("copy-equals-lure", _copy(case), _lure(case)),
        _check("copy-differs-from-target", _copy(case) != _gold(case), True),
    ]
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


@register("DIAG-P5-LATENT-L4-PLAN-01")
def verify_diag_p5_latent_l4_plan_01(case: Case) -> VerificationResult:
    source = _source_three_query_problem()
    target_base = _target_l4_problem()
    target = AffineProblem(L4_CATALOGUE, (), L4_COSTS, target_base.queries)
    parsed_source, parsed_source_codebook = _parse_explicit_planning_problem(case.source.problem)
    parsed_target, parsed_target_codebook = _parse_explicit_planning_problem(case.target.problem)
    expected_source = (
        Plan(12, ("S3", "S7", "S2", "S4", "S5"), 0b11100001),
        Plan(14, ("S5", "S6", "S7", "S1", "S2"), 0b10110111),
        Plan(10, ("S2", "S5", "S7", "S1"), 0b01101010),
    )
    expected_target = CHAIN_LEVEL_SPECS[4].expected_plans
    expected_lure = CHAIN_LEVEL_SPECS[4].lure_plans
    source_best = tuple(
        _plans(source, SOURCE_CODEBOOK, query_index) for query_index in range(len(source.queries))
    )
    target_best = tuple(
        _plans(target, L4_CODEBOOK, query_index) for query_index in range(len(target.queries))
    )
    lure_best = tuple(
        _plans(target, L4_OLD_CODEBOOK, query_index) for query_index in range(len(target.queries))
    )
    target_near = tuple(
        _plans(target, L4_CODEBOOK, query_index, max_extra_cost=2)
        for query_index in range(len(target.queries))
    )
    lure_actual = tuple(
        _replay(target, L4_CODEBOOK, plan.codes, query_index)
        for query_index, plan in enumerate(expected_lure)
    )
    checks = [
        _check("source-explicit-text", parsed_source, source),
        _check("target-explicit-text", parsed_target, target),
        _check("source-explicit-codebook", parsed_source_codebook, SOURCE_CODEBOOK),
        _check("target-explicit-codebook", parsed_target_codebook, L4_CODEBOOK_BY_CARD),
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
            "target-runner-up-costs",
            tuple(tuple(sorted({plan.cost for plan in plans})) for plans in target_near),
            ((7, 9), (11, 12, 13), (11, 12, 13)),
        ),
        _check(
            "stale-codebook-optima",
            lure_best,
            tuple((plan,) for plan in expected_lure),
        ),
        _check(
            "stale-plans-actual-states",
            lure_actual,
            (0b11010100, 0b01110001, 0b01011111),
        ),
        _check(
            "stale-plans-miss-goals",
            tuple(state != target.queries[index][1] for index, state in enumerate(lure_actual)),
            (True, True, True),
        ),
        _check("stored-source-answer", case.source.answer, _format_plans(expected_source)),
        _check("stored-target", _gold(case), _format_plans(expected_target)),
        _check("stored-lure", _lure(case), _format_plans(expected_lure)),
        _check("copy-equals-lure", _copy(case), _lure(case)),
        _check("copy-differs-from-target", _copy(case) != _gold(case), True),
    ]
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


def _verify_single_query_planning_probe(case: Case, query_index: int) -> VerificationResult:
    source = _source_three_query_problem()
    target_base = _target_l4_problem()
    target = AffineProblem(
        L4_CATALOGUE,
        (),
        L4_COSTS,
        (target_base.queries[query_index],),
    )
    parsed_source, parsed_source_codebook = _parse_explicit_planning_problem(case.source.problem)
    parsed_target, parsed_target_codebook = _parse_explicit_planning_problem(case.target.problem)
    source_plans = (
        Plan(12, ("S3", "S7", "S2", "S4", "S5"), 0b11100001),
        Plan(14, ("S5", "S6", "S7", "S1", "S2"), 0b10110111),
        Plan(10, ("S2", "S5", "S7", "S1"), 0b01101010),
    )
    expected = CHAIN_LEVEL_SPECS[4].expected_plans[query_index]
    expected_lure = CHAIN_LEVEL_SPECS[4].lure_plans[query_index]
    source_best = _plans(source, SOURCE_CODEBOOK, query_index)
    target_best = _plans(target, L4_CODEBOOK, 0)
    target_near = _plans(target, L4_CODEBOOK, 0, max_extra_cost=2)
    lure_best = _plans(target, L4_OLD_CODEBOOK, 0)
    lure_actual = _replay(target, L4_CODEBOOK, expected_lure.codes, 0)
    checks = [
        _check("source-explicit-text", parsed_source, source),
        _check("target-explicit-text", parsed_target, target),
        _check("source-explicit-codebook", parsed_source_codebook, SOURCE_CODEBOOK),
        _check("target-explicit-codebook", parsed_target_codebook, L4_CODEBOOK_BY_CARD),
        _check("source-query-optimum", source_best, (source_plans[query_index],)),
        _check("target-query-optimum", target_best, (expected,)),
        _check(
            "target-runner-up-costs",
            tuple(sorted({plan.cost for plan in target_near})),
            ((7, 9), (11, 12, 13), (11, 12, 13))[query_index],
        ),
        _check("stale-codebook-optimum", lure_best, (expected_lure,)),
        _check(
            "stale-plan-actual-state",
            f"{lure_actual:08b}",
            ("11010100", "01110001", "01011111")[query_index],
        ),
        _check("stale-plan-misses-goal", lure_actual != target.queries[0][1], True),
        _check(
            "stored-source-answer",
            case.source.answer,
            _format_plans(source_plans),
        ),
        _check("stored-target", _gold(case), _format_plans((expected,))),
        _check("stored-lure", _lure(case), _format_plans((expected_lure,))),
        _check("copy-equals-lure", _copy(case), _lure(case)),
        _check("copy-differs-from-target", _copy(case) != _gold(case), True),
    ]
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


@register("DIAG-P5-LATENT-L4-PLAN-Q1-01")
def verify_diag_p5_latent_l4_plan_q1_01(case: Case) -> VerificationResult:
    return _verify_single_query_planning_probe(case, 0)


@register("DIAG-P5-LATENT-L4-PLAN-Q2-01")
def verify_diag_p5_latent_l4_plan_q2_01(case: Case) -> VerificationResult:
    return _verify_single_query_planning_probe(case, 1)


@register("DIAG-P5-LATENT-L4-PLAN-Q3-01")
def verify_diag_p5_latent_l4_plan_q3_01(case: Case) -> VerificationResult:
    return _verify_single_query_planning_probe(case, 2)
