from __future__ import annotations

from itertools import product

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.hard_seeds import (
    _enumerate_spectrum_successors,
    _polynomial_determinant,
    _spectrum_laplacian_minor,
)
from mindsetbench.verification.registry import register

SpectrumEdge = tuple[str, int, bool]
SpectrumGraph = dict[str, list[SpectrumEdge]]


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


def _unconstrained_coefficients(nodes: list[str], edges: SpectrumGraph) -> list[int]:
    coefficients = [0] * (len(nodes) + 1)
    for choices in product(*(edges[node] for node in nodes)):
        degree = sum(marked for _target, _weight, marked in choices)
        weight = 1
        for _target, edge_weight, _marked in choices:
            weight *= edge_weight
        coefficients[degree] += weight
    return coefficients


def _unweighted_coefficients(nodes: list[str], root: str, edges: SpectrumGraph) -> list[int]:
    unweighted = {
        node: [(target, 1, marked) for target, _weight, marked in node_edges]
        for node, node_edges in edges.items()
    }
    return _enumerate_spectrum_successors(nodes, root, unweighted)


def _verify_spectrum_case(
    case: Case,
    *,
    nodes: list[str],
    root: str,
    edges: SpectrumGraph,
    expected_coefficients: list[int],
    degree: int,
    modulus: int,
    lure_value: int,
) -> VerificationResult:
    exhaustive = _enumerate_spectrum_successors(nodes, root, edges)
    determinant = _polynomial_determinant(_spectrum_laplacian_minor([*nodes, root], root, edges))
    return _result(
        case,
        [
            _check("exhaustive-spectrum", exhaustive, expected_coefficients),
            _check("polynomial-determinant", determinant, exhaustive),
            _check("stored-target", _gold(case), str(exhaustive[degree] % modulus)),
            _check("stored-lure", _lure(case), str(lure_value)),
            _check("copy-equals-lure", _copy(case), _lure(case)),
            _check("copy-differs-from-target", _copy(case) != _gold(case), True),
        ],
    )


@register("FORMAL-P2-SENS-L0-01")
def verify_formal_p2_sens_l0_01(case: Case) -> VerificationResult:
    edges: SpectrumGraph = {
        "X": [("Y", 2, True), ("R", 3, False)],
        "Y": [("X", 1, False), ("R", 4, True)],
    }
    unconstrained = _unconstrained_coefficients(list("XY"), edges)
    return _verify_spectrum_case(
        case,
        nodes=list("XY"),
        root="R",
        edges=edges,
        expected_coefficients=[3, 12, 8],
        degree=1,
        modulus=1000,
        lure_value=unconstrained[1],
    )


@register("FORMAL-P2-SENS-L1-01")
def verify_formal_p2_sens_l1_01(case: Case) -> VerificationResult:
    edges: SpectrumGraph = {
        "A": [("B", 2, True), ("R", 3, False)],
        "B": [("C", 4, False), ("R", 2, True)],
        "C": [("D", 3, True), ("R", 5, False)],
        "D": [("A", 2, False), ("R", 4, True)],
    }
    unconstrained = _unconstrained_coefficients(list("ABCD"), edges)
    return _verify_spectrum_case(
        case,
        nodes=list("ABCD"),
        root="R",
        edges=edges,
        expected_coefficients=[120, 452, 500, 272, 48],
        degree=2,
        modulus=1000,
        lure_value=unconstrained[2],
    )


def _six_node_edges() -> SpectrumGraph:
    return {
        "A": [("C", 5, True), ("D", 2, False), ("B", 4, True)],
        "B": [("C", 5, False), ("D", 5, True), ("E", 5, False)],
        "C": [("G", 1, True), ("F", 3, False), ("A", 2, True)],
        "D": [("E", 3, False), ("G", 2, True), ("F", 4, True)],
        "E": [("D", 2, True), ("B", 2, False), ("G", 4, False)],
        "F": [("G", 4, False), ("A", 4, True), ("E", 2, True)],
    }


@register("FORMAL-P2-SENS-L2-01")
def verify_formal_p2_sens_l2_01(case: Case) -> VerificationResult:
    edges = _six_node_edges()
    unconstrained = _unconstrained_coefficients(list("ABCDEF"), edges)
    return _verify_spectrum_case(
        case,
        nodes=list("ABCDEF"),
        root="G",
        edges=edges,
        expected_coefficients=[3600, 32280, 83520, 107980, 73320, 23440, 2840],
        degree=2,
        modulus=1000,
        lure_value=unconstrained[2] % 1000,
    )


def _eight_node_edges(*, perturbed: bool) -> SpectrumGraph:
    return {
        "F": [("B", 2, True), ("D", 5, False), ("Z", 3, False)],
        "B": [("H", 4, False), ("A", 2, True), ("Z", 6, False)],
        "H": [
            ("D", 3, True),
            ("G", 9 if perturbed else 4, False),
            ("Z", 2, True),
        ],
        "D": [("A", 5, False), ("C", 3, True), ("Z", 4, False)],
        "A": [("G", 2, True), ("E", 6, False), ("Z", 5, True)],
        "G": [("C", 7, False), ("F", 2, True), ("Z", 3, False)],
        "C": [("E", 4, True), ("B", 5, False), ("Z", 2, False)],
        "E": [("F", 3, False), ("H", 7, True), ("Z", 4, True)],
    }


BASE_EIGHT_COEFFICIENTS = [
    1895040,
    20986920,
    57806304,
    78520864,
    56237600,
    22042736,
    4732816,
    493176,
    16320,
]
PERTURBED_EIGHT_COEFFICIENTS = [
    4263840,
    43519320,
    100805184,
    114576744,
    72141200,
    25719216,
    5179336,
    519576,
    16320,
]


@register("FORMAL-P2-SENS-L3-01")
def verify_formal_p2_sens_l3_01(case: Case) -> VerificationResult:
    edges = _eight_node_edges(perturbed=False)
    return _verify_spectrum_case(
        case,
        nodes=list("FBHDAGCE"),
        root="Z",
        edges=edges,
        expected_coefficients=BASE_EIGHT_COEFFICIENTS,
        degree=4,
        modulus=1000,
        lure_value=_unweighted_coefficients(list("FBHDAGCE"), "Z", edges)[4] % 1000,
    )


@register("FORMAL-P2-SENS-L4-01")
def verify_formal_p2_sens_l4_01(case: Case) -> VerificationResult:
    edges = _eight_node_edges(perturbed=True)
    checks = _verify_spectrum_case(
        case,
        nodes=list("FBHDAGCE"),
        root="Z",
        edges=edges,
        expected_coefficients=PERTURBED_EIGHT_COEFFICIENTS,
        degree=4,
        modulus=1000,
        lure_value=_unweighted_coefficients(list("FBHDAGCE"), "Z", edges)[4] % 1000,
    ).checks
    sensitivity = [
        (perturbed - base) // 5
        for base, perturbed in zip(
            BASE_EIGHT_COEFFICIENTS,
            PERTURBED_EIGHT_COEFFICIENTS,
            strict=True,
        )
    ]
    checks.append(
        _check(
            "local-sensitivity-update",
            BASE_EIGHT_COEFFICIENTS[4] + 5 * sensitivity[4],
            PERTURBED_EIGHT_COEFFICIENTS[4],
        )
    )
    return _result(case, checks)
