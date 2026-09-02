from __future__ import annotations

import math
from collections import defaultdict
from itertools import product

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register


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


def _result(case: Case, checks: list[VerificationCheck]) -> VerificationResult:
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


def _legacy_gold(case: Case) -> str:
    return case.target.answer.legacy_value()


@register("L0-A-01")
def verify_l0_a_01(case: Case) -> VerificationResult:
    def count(total: int, caps: tuple[int, ...]) -> int:
        return sum(sum(values) == total for values in product(*(range(cap + 1) for cap in caps)))

    source = count(24, (8, 8, 6, 6, 4))
    target = count(30, (10, 9, 8, 7, 5))
    return _result(
        case,
        [
            _check("source-enumeration", source, 450),
            _check("target-enumeration", target, 674),
            _check("stored-target", _legacy_gold(case), str(target)),
        ],
    )


@register("L1-A-C1")
def verify_l1_a_c1(case: Case) -> VerificationResult:
    def count(total: int, *, require_triangle: bool) -> int:
        return sum(
            1
            for a in range(1, total)
            for b in range(a + 1, total)
            for c in range(b + 1, total)
            if a + b + c == total and (not require_triangle or a + b > c)
        )

    source = count(48, require_triangle=True)
    target = count(54, require_triangle=True)
    unconstrained = count(54, require_triangle=False)
    return _result(
        case,
        [
            _check("source-triangles", source, 37),
            _check("target-triangles", target, 48),
            _check("missing-constraint-probe", unconstrained, 217),
            _check("stored-target", _legacy_gold(case), str(target)),
        ],
    )


@register("L2-F-05")
def verify_l2_f_05(case: Case) -> VerificationResult:
    source_rate = math.log(10_368 / 7_200) / 4
    source_time = math.log(7_200 / 5_000) / source_rate
    elimination_rate = math.log(4.8 / 1.5) / 5
    target_time = math.log(15 / 4.8) / elimination_rate
    stored = float(_legacy_gold(case))
    return _result(
        case,
        [
            _check("source-time", round(source_time, 10), 4.0),
            _check("target-rounded", round(target_time, 2), 4.90),
            _check("stored-within-tolerance", abs(stored - target_time) <= 0.02, True),
        ],
    )


@register("L3-A-01")
def verify_l3_a_01(case: Case) -> VerificationResult:
    edges = {
        "S": [("A", 2, 5), ("B", 3, 2)],
        "A": [("C", 2, 5), ("D", 3, 1), ("T", 7, 3)],
        "B": [("C", 4, 2), ("D", 2, 6), ("T", 9, 1)],
        "C": [("T", 2, 4)],
        "D": [("T", 5, 2)],
    }
    paths: list[tuple[int, int, tuple[str, ...]]] = []

    def visit(node: str, time: int, fat: int, path: tuple[str, ...]) -> None:
        if node == "T":
            paths.append((time, fat, path))
            return
        for next_node, edge_time, edge_fat in edges.get(node, []):
            if next_node not in path:
                visit(next_node, time + edge_time, fat + edge_fat, (*path, next_node))

    visit("S", 0, 0, ("S",))
    unconstrained = min(time for time, _, _ in paths)
    constrained = min(time for time, fat, _ in paths if fat <= 9)
    return _result(
        case,
        [
            _check("simple-path-count", len(paths), 6),
            _check("unconstrained-copy-probe", unconstrained, 6),
            _check("resource-constrained", constrained, 9),
            _check("stored-target", _legacy_gold(case), str(constrained)),
        ],
    )


@register("L4-F-01")
def verify_l4_f_01(case: Case) -> VerificationResult:
    suppliers_by_tank = {
        "M1": {"S1", "S2", "S3"},
        "M2": {"S2", "S3"},
        "M3": {"S1", "S4"},
        "M4": {"S4", "S5"},
        "M5": {"S3", "S5"},
    }
    tanks_by_product = {
        "P1": {"M1"},
        "P2": {"M1", "M2"},
        "P3": {"M2"},
        "P4": {"M3"},
        "P5": {"M3", "M4"},
        "P6": {"M4"},
        "P7": {"M5"},
    }
    downstream: dict[str, set[str]] = defaultdict(set)
    for product_name, tanks in tanks_by_product.items():
        for tank in tanks:
            for supplier in suppliers_by_tank[tank]:
                downstream[supplier].add(product_name)

    positive = {"P1", "P2", "P3"}
    negative = {"P4", "P6", "P7"}
    positive_only = sorted(
        supplier for supplier, products in downstream.items() if positive <= products
    )
    consistent = sorted(
        supplier
        for supplier, products in downstream.items()
        if positive <= products and not (negative & products)
    )

    circle_solutions = [
        (x, y)
        for x in range(-100, 101)
        for y in range(-100, 101)
        if x * x + y * y == 60**2
        and (x - 36) ** 2 + y * y == 48**2
        and x * x + (y - 48) ** 2 == 36**2
    ]
    return _result(
        case,
        [
            _check("source-circle-intersection", circle_solutions, [(36, 48)]),
            _check("positive-only-candidates", positive_only, ["S2", "S3"]),
            _check("all-observations", consistent, ["S2"]),
            _check("stored-target", _legacy_gold(case), consistent[0]),
        ],
    )
