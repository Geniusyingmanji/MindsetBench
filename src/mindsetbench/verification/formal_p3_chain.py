from __future__ import annotations

import re
from collections import defaultdict

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

CausalEdge = tuple[str, str, int]


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


def _result(case: Case, checks: list[VerificationCheck]) -> VerificationResult:
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


def _gold(case: Case) -> str:
    return case.target.answer.legacy_value()


def _lure(case: Case) -> str:
    assert case.lure and case.lure.answer
    return case.lure.answer.legacy_value()


def _copy(case: Case) -> str:
    assert case.copy_probe
    return case.copy_probe.answer.legacy_value()


def _dynamic_responses(nodes: list[str], treatment: str, edges: list[CausalEdge]) -> dict[str, int]:
    position = {node: index for index, node in enumerate(nodes)}
    if len(position) != len(nodes):
        raise ValueError("nodes must be unique")
    if treatment not in position:
        raise ValueError("treatment must be present in nodes")
    incoming: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for source, target, coefficient in edges:
        if source not in position or target not in position:
            raise ValueError(f"edge uses unknown node: {(source, target)}")
        if position[source] >= position[target]:
            raise ValueError(f"edge violates supplied topological order: {(source, target)}")
        incoming[target].append((source, coefficient))
    responses = {node: 0 for node in nodes}
    responses[treatment] = 1
    for node in nodes[position[treatment] + 1 :]:
        responses[node] = sum(responses[parent] * weight for parent, weight in incoming[node])
    return responses


def _enumerate_path_products(
    treatment: str,
    outcome: str,
    edges: list[CausalEdge],
) -> list[int]:
    outgoing: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for source, target, coefficient in edges:
        outgoing[source].append((target, coefficient))
    products: list[int] = []

    def visit(node: str, product: int, seen: frozenset[str]) -> None:
        if node == outcome:
            products.append(product)
            return
        for child, coefficient in outgoing[node]:
            if child in seen:
                raise ValueError("causal graph must be acyclic")
            visit(child, product * coefficient, seen | {child})

    visit(treatment, 1, frozenset({treatment}))
    return products


def _verify_effect_case(
    case: Case,
    *,
    nodes: list[str],
    treatment: str,
    outcome: str,
    edges: list[CausalEdge],
    expected_effect: int,
    expected_path_count: int,
) -> VerificationResult:
    responses = _dynamic_responses(nodes, treatment, edges)
    products = _enumerate_path_products(treatment, outcome, edges)
    checks = [
        _check("dynamic-total-effect", responses[outcome], expected_effect),
        _check("explicit-path-product-sum", sum(products), expected_effect),
        _check("explicit-path-count", len(products), expected_path_count),
        _check("stored-target", _gold(case), str(expected_effect)),
        _check("stored-lure", _lure(case), str(expected_path_count)),
        _check("copy-equals-lure", _copy(case), _lure(case)),
        _check("copy-differs-from-target", _copy(case) != _gold(case), True),
    ]
    return _result(case, checks)


@register("FORMAL-P3-CAUSAL-L0-01")
def verify_formal_p3_causal_l0_01(case: Case) -> VerificationResult:
    return _verify_effect_case(
        case,
        nodes=["T", "M", "Y"],
        treatment="T",
        outcome="Y",
        edges=[("T", "M", 2), ("T", "Y", 3), ("M", "Y", 4)],
        expected_effect=11,
        expected_path_count=2,
    )


@register("FORMAL-P3-CAUSAL-L1-01")
def verify_formal_p3_causal_l1_01(case: Case) -> VerificationResult:
    return _verify_effect_case(
        case,
        nodes=["T", "A", "B", "Y"],
        treatment="T",
        outcome="Y",
        edges=[
            ("T", "A", 2),
            ("T", "B", -1),
            ("A", "B", 3),
            ("T", "Y", -2),
            ("A", "Y", 4),
            ("B", "Y", 5),
        ],
        expected_effect=31,
        expected_path_count=4,
    )


def _medium_edges() -> list[CausalEdge]:
    return [
        ("T", "A", 2),
        ("T", "B", -1),
        ("T", "C", 3),
        ("A", "B", 2),
        ("A", "D", 4),
        ("A", "E", -2),
        ("B", "D", 5),
        ("B", "E", 1),
        ("B", "F", 3),
        ("C", "D", -2),
        ("C", "E", 2),
        ("C", "F", -4),
        ("D", "Y", 2),
        ("E", "Y", -1),
        ("F", "Y", 5),
    ]


@register("FORMAL-P3-CAUSAL-L2-01")
def verify_formal_p3_causal_l2_01(case: Case) -> VerificationResult:
    return _verify_effect_case(
        case,
        nodes=["T", "A", "B", "C", "D", "E", "F", "Y"],
        treatment="T",
        outcome="Y",
        edges=_medium_edges(),
        expected_effect=14,
        expected_path_count=11,
    )


def _full_edges(*, perturbed: bool) -> list[CausalEdge]:
    return [
        ("J", "R", 2),
        ("J", "K", -1),
        ("J", "N", 3),
        ("R", "K", 2),
        ("R", "S", 4),
        ("R", "V", -2),
        ("K", "S", 5),
        ("K", "V", 1),
        ("K", "L", 3),
        ("N", "S", -2),
        ("N", "V", 2),
        ("N", "L", -4),
        ("S", "Q", 3),
        ("S", "P", -1),
        ("S", "W", 2),
        ("V", "Q", 9 if perturbed else 5),
        ("V", "P", 2),
        ("V", "W", -1),
        ("L", "Q", -2),
        ("L", "P", 4),
        ("L", "W", 5),
        ("Q", "P", 1),
        ("Q", "W", 6),
        ("P", "W", -3),
    ]


FULL_NODES = ["J", "R", "K", "N", "S", "V", "L", "Q", "P", "W"]


def _parse_full_edges(problem: str) -> list[CausalEdge]:
    return [
        (source, target, int(coefficient))
        for source, target, coefficient in re.findall(
            r"([JRKNSVLQPW])→([JRKNSVLQPW]):(-?\d+)",
            problem,
        )
    ]


@register("FORMAL-P3-CAUSAL-L3-01")
def verify_formal_p3_causal_l3_01(case: Case) -> VerificationResult:
    result = _verify_effect_case(
        case,
        nodes=FULL_NODES,
        treatment="J",
        outcome="W",
        edges=_full_edges(perturbed=False),
        expected_effect=317,
        expected_path_count=44,
    )
    source_to_target = dict(zip("XABCDEFGHY", FULL_NODES, strict=True))
    source_edges = [
        (source_to_target[source], source_to_target[target], coefficient)
        for source, target, coefficient in _source_full_edges()
    ]
    result.checks.append(
        _check(
            "renamed-edge-multiset",
            sorted(source_edges),
            sorted(_full_edges(perturbed=False)),
        )
    )
    result.checks.append(
        _check(
            "target-text-edge-multiset",
            sorted(_parse_full_edges(case.target.problem)),
            sorted(_full_edges(perturbed=False)),
        )
    )
    return result


def _source_full_edges() -> list[CausalEdge]:
    inverse = dict(zip(FULL_NODES, "XABCDEFGHY", strict=True))
    return [
        (inverse[source], inverse[target], coefficient)
        for source, target, coefficient in _full_edges(perturbed=False)
    ]


@register("FORMAL-P3-CAUSAL-L4-01")
def verify_formal_p3_causal_l4_01(case: Case) -> VerificationResult:
    result = _verify_effect_case(
        case,
        nodes=FULL_NODES,
        treatment="J",
        outcome="W",
        edges=_full_edges(perturbed=True),
        expected_effect=377,
        expected_path_count=44,
    )
    baseline = _dynamic_responses(FULL_NODES, "J", _full_edges(perturbed=False))
    perturbed = _dynamic_responses(FULL_NODES, "J", _full_edges(perturbed=True))
    downstream_q = _dynamic_responses(
        ["Q", "P", "W"],
        "Q",
        [("Q", "P", 1), ("Q", "W", 6), ("P", "W", -3)],
    )["W"]
    sensitivity = baseline["V"] * downstream_q
    result.checks.extend(
        [
            _check(
                "target-text-edge-multiset",
                sorted(_parse_full_edges(case.target.problem)),
                sorted(_full_edges(perturbed=True)),
            ),
            _check("edge-tail-response", baseline["V"], 5),
            _check("edge-head-downstream-effect", downstream_q, 3),
            _check("local-sensitivity", sensitivity, 15),
            _check("finite-difference-update", baseline["W"] + 4 * sensitivity, perturbed["W"]),
        ]
    )
    return result
