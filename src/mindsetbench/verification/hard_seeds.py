from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations, permutations, product

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.expansion_cases import _minimal_valid_sets
from mindsetbench.verification.registry import register


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


@register("HARD-P2-L3-01")
def verify_hard_p2_l3_01(case: Case) -> VerificationResult:
    marker_names = "ABCDEFGHI"
    pulse_sets = [
        "DI",
        "CEGI",
        "BFGH",
        "AI",
        "BEFGHI",
        "DFG",
        "CDGI",
        "CDEGH",
        "BCEH",
        "ABCDEFGI",
    ]
    masks = [sum(1 << marker_names.index(marker) for marker in markers) for markers in pulse_sets]
    target = sum(1 << marker_names.index(marker) for marker in "ADGH")
    solutions: list[tuple[int, ...]] = []
    for selection in range(1 << len(masks)):
        state = 0
        for index, mask in enumerate(masks):
            if selection & (1 << index):
                state ^= mask
        if state == target:
            solutions.append(tuple(index + 1 for index in range(10) if selection & (1 << index)))
    weight_four = [solution for solution in solutions if len(solution) == 4]
    target_bits = {marker_names.index(marker) for marker in "ADGH"}
    monotone_solutions = []
    for size in range(1, len(masks) + 1):
        monotone_solutions = [
            group
            for group in combinations(range(10), size)
            if target_bits
            <= {
                bit
                for index in group
                for bit in range(len(marker_names))
                if masks[index] & (1 << bit)
            }
        ]
        if monotone_solutions:
            break
    lexical_cover = min(monotone_solutions)
    return _result(
        case,
        [
            _check(
                "all-solutions",
                solutions,
                [(1, 3, 4, 6, 8, 9), (2, 4, 5, 6, 7, 8, 9), (2, 3, 10), (1, 5, 7, 10)],
            ),
            _check("unique-weight-four", weight_four, [(1, 5, 7, 10)]),
            _check("stored-target", _gold(case), "J1;J5;J7;J10"),
            _check(
                "stored-lure",
                _lure(case),
                ";".join(f"J{i + 1}" for i in lexical_cover),
            ),
            _check("copy-equals-lure", _copy(case), _lure(case)),
        ],
    )


@register("HARD-P3-L3-01")
def verify_hard_p3_l3_01(case: Case) -> VerificationResult:
    edges = {
        ("A", "X"),
        ("A", "B"),
        ("B", "Y"),
        ("C", "X"),
        ("C", "Y"),
        ("X", "M"),
        ("M", "Y"),
        ("X", "Y"),
        ("X", "D"),
        ("Y", "D"),
        ("Z", "X"),
    }
    observed = ["B", "C", "M", "D", "Z"]
    candidates = [
        set(group) for size in range(len(observed) + 1) for group in combinations(observed, size)
    ]
    minimal = _minimal_valid_sets(edges, "X", "Y", candidates)
    return _result(
        case,
        [
            _check("unique-minimal-backdoor-set", minimal, [{"B", "C"}]),
            _check("stored-target", _gold(case), "B;C"),
            _check("stored-direct-effect-lure", _lure(case), "B;C;M"),
            _check("copy-equals-lure", _copy(case), _lure(case)),
        ],
    )


@register("HARD-P4-L3-01")
def verify_hard_p4_l3_01(case: Case) -> VerificationResult:
    records = {
        "Q1": dict(
            ring=True,
            command=True,
            emergency=False,
            medic=False,
            beacon=False,
            kind="inert",
            test=None,
            decon=False,
        ),
        "Q2": dict(
            ring=True,
            command=False,
            emergency=False,
            medic=False,
            beacon=False,
            kind="inert",
            test=None,
            decon=False,
        ),
        "Q3": dict(
            ring=True,
            command=False,
            emergency=True,
            medic=True,
            beacon=True,
            kind="inert",
            test=None,
            decon=False,
        ),
        "Q4": dict(
            ring=True,
            command=False,
            emergency=True,
            medic=True,
            beacon=False,
            kind="inert",
            test=None,
            decon=False,
        ),
        "Q5": dict(
            ring=True,
            command=False,
            emergency=False,
            medic=True,
            beacon=True,
            kind="inert",
            test=None,
            decon=False,
        ),
        "Q6": dict(
            ring=True,
            command=True,
            emergency=False,
            medic=False,
            beacon=False,
            kind="lumen",
            test="failed",
            decon=False,
        ),
        "Q7": dict(
            ring=True,
            command=False,
            emergency=True,
            medic=True,
            beacon=True,
            kind="nox",
            test=None,
            decon=False,
        ),
        "Q8": dict(
            ring=True,
            command=True,
            emergency=False,
            medic=False,
            beacon=False,
            kind="nox",
            test=None,
            decon=True,
        ),
        "Q9": dict(
            ring=False,
            command=False,
            emergency=False,
            medic=False,
            beacon=False,
            kind="nox",
            test=None,
            decon=False,
        ),
        "Q10": dict(
            ring=False,
            command=False,
            emergency=False,
            medic=False,
            beacon=False,
            kind="inert",
            test=None,
            decon=False,
        ),
    }

    def hazardous(facts: dict[str, object]) -> bool:
        return (facts["kind"] == "lumen" and facts["test"] == "failed") or (
            facts["kind"] == "nox" and not facts["decon"]
        )

    def violates(facts: dict[str, object]) -> bool:
        exception = facts["emergency"] and facts["medic"] and facts["beacon"]
        approval_violation = facts["ring"] and not facts["command"] and not exception
        return bool(approval_violation or hazardous(facts))

    target = sorted(
        (record_id for record_id, facts in records.items() if violates(facts)),
        key=lambda value: int(value[1:]),
    )
    flat = sorted(
        (
            record_id
            for record_id, facts in records.items()
            if facts["ring"] and not facts["command"]
        ),
        key=lambda value: int(value[1:]),
    )
    return _result(
        case,
        [
            _check("derived-priority-violations", target, ["Q2", "Q4", "Q5", "Q6", "Q7", "Q9"]),
            _check("flat-rule-violations", flat, ["Q2", "Q3", "Q4", "Q5", "Q7"]),
            _check("stored-target", _gold(case), ";".join(target)),
            _check("stored-lure", _lure(case), ";".join(flat)),
            _check("copy-equals-lure", _copy(case), _lure(case)),
        ],
    )


Relation = tuple[str, str, str]


def _relation_preserved(
    relation: Relation, mapping: dict[str, str], target_relations: set[Relation]
) -> bool:
    source, predicate, target = relation
    mapped_source, mapped_target = mapping[source], mapping[target]
    if (mapped_source, predicate, mapped_target) in target_relations:
        return True
    if predicate != "processed":
        return False
    return any(
        first_source == mapped_source
        and first_predicate == predicate
        and second_source == middle
        and second_predicate == predicate
        and second_target == mapped_target
        for first_source, first_predicate, middle in target_relations
        for second_source, second_predicate, second_target in target_relations
    )


@register("HARD-P6-L3-01")
def verify_hard_p6_l3_01(case: Case) -> VerificationResult:
    source_relations = {
        ("A1", "plans", "A2"),
        ("A2", "raw", "A3"),
        ("A2", "reports", "A6"),
        ("A3", "processed", "A4"),
        ("A3", "checksum", "A6"),
        ("A4", "certifies", "A5"),
        ("A6", "blocks", "A4"),
        ("A2", "monitors", "A7"),
        ("A7", "substitutes", "A6"),
        ("A8", "archives", "A5"),
    }
    target_relations = {
        ("B1", "plans", "B4"),
        ("B4", "raw", "B7"),
        ("B4", "reports", "B2"),
        ("B7", "processed", "B8"),
        ("B8", "processed", "B6"),
        ("B7", "checksum", "B2"),
        ("B6", "certifies", "B3"),
        ("B2", "blocks", "B6"),
        ("B4", "monitors", "B5"),
        ("B5", "substitutes", "B2"),
        ("B9", "archives", "B3"),
    }
    source_free = ["A2", "A3", "A4", "A6", "A7"]
    target_free = ["B2", "B4", "B5", "B6", "B7", "B8"]
    scored: list[tuple[int, tuple[str, ...]]] = []
    for assignment in permutations(target_free, len(source_free)):
        mapping = {"A1": "B1", "A5": "B3", "A8": "B9"}
        mapping.update(dict(zip(source_free, assignment, strict=True)))
        score = sum(
            _relation_preserved(relation, mapping, target_relations)
            for relation in source_relations
        )
        scored.append((score, assignment))
    best_score = max(score for score, _ in scored)
    best = [assignment for score, assignment in scored if score == best_score]
    return _result(
        case,
        [
            _check("best-score", best_score, len(source_relations)),
            _check("unique-best-mapping", best, [("B4", "B7", "B6", "B2", "B5")]),
            _check("stored-target", _gold(case), "B4;B7;B6;B2;B5"),
            _check("stored-lure", _lure(case), "B7"),
            _check("copy-is-not-target", _copy(case) != _gold(case), True),
        ],
    )


def _joint_relation_score(
    source_relations: set[Relation],
    target_relations: set[Relation],
    node_mapping: dict[str, str],
    predicate_mapping: dict[str, str],
) -> int:
    score = 0
    for source, predicate, target in source_relations:
        mapped_source = node_mapping[source]
        mapped_target = node_mapping[target]
        mapped_predicate = predicate_mapping[predicate]
        direct = (mapped_source, mapped_predicate, mapped_target) in target_relations
        relayed = any(
            first_source == mapped_source
            and first_predicate == mapped_predicate
            and second_source == middle
            and second_predicate == mapped_predicate
            and second_target == mapped_target
            for first_source, first_predicate, middle in target_relations
            for second_source, second_predicate, second_target in target_relations
        )
        score += direct or relayed
    return score


@register("HARD-P6-L4-02")
def verify_hard_p6_l4_02(case: Case) -> VerificationResult:
    source_relations = {
        ("A1", "nex", "A2"),
        ("A2", "vul", "A3"),
        ("A3", "sor", "A4"),
        ("A4", "tal", "A7"),
        ("A2", "sor", "A5"),
        ("A5", "nex", "A6"),
        ("A6", "vul", "A4"),
        ("A3", "tal", "A6"),
        ("A5", "vul", "A7"),
        ("A1", "tal", "A5"),
        ("A6", "sor", "A7"),
        ("A4", "nex", "A2"),
    }
    target_relations = {
        ("B3", "○", "B7"),
        ("B6", "◇", "B5"),
        ("B6", "△", "B3"),
        ("B7", "□", "B8"),
        ("B8", "□", "B1"),
        ("B1", "◇", "B2"),
        ("B1", "△", "B3"),
        ("B3", "○", "B5"),
        ("B3", "□", "B5"),
        ("B4", "○", "B1"),
        ("B4", "□", "B2"),
        ("B4", "□", "B3"),
        ("B5", "○", "B2"),
        ("B5", "◇", "B1"),
        ("B5", "△", "B4"),
        ("B7", "◇", "B4"),
        ("B7", "△", "B4"),
    }
    source_free = ["A2", "A3", "A4", "A5", "A6"]
    target_free = ["B1", "B3", "B4", "B5", "B7", "B8"]
    source_predicates = ["nex", "vul", "sor", "tal"]
    target_predicates = ["○", "◇", "△", "□"]

    scored: list[tuple[int, tuple[str, ...], tuple[str, ...]]] = []
    for node_assignment in permutations(target_free, len(source_free)):
        node_mapping = {"A1": "B6", "A7": "B2"}
        node_mapping.update(dict(zip(source_free, node_assignment, strict=True)))
        for predicate_assignment in permutations(target_predicates):
            predicate_mapping = dict(zip(source_predicates, predicate_assignment, strict=True))
            score = _joint_relation_score(
                source_relations,
                target_relations,
                node_mapping,
                predicate_mapping,
            )
            scored.append((score, node_assignment, predicate_assignment))

    best_score = max(score for score, _, _ in scored)
    best = [(nodes, predicates) for score, nodes, predicates in scored if score == best_score]
    second_score = max(score for score, _, _ in scored if score < best_score)

    lure_predicates = ("○", "◇", "△", "□")
    lure_scored = [
        (
            _joint_relation_score(
                source_relations,
                target_relations,
                {
                    "A1": "B6",
                    "A7": "B2",
                    **dict(zip(source_free, node_assignment, strict=True)),
                },
                dict(zip(source_predicates, lure_predicates, strict=True)),
            ),
            node_assignment,
        )
        for node_assignment in permutations(target_free, len(source_free))
    ]
    lure_score = max(score for score, _ in lure_scored)
    lure_best = [nodes for score, nodes in lure_scored if score == lure_score]

    return _result(
        case,
        [
            _check("joint-best-score", best_score, 12),
            _check("joint-runner-up-score", second_score, 10),
            _check(
                "unique-joint-mapping",
                best,
                [
                    (
                        ("B3", "B7", "B1", "B5", "B4"),
                        ("△", "○", "□", "◇"),
                    )
                ],
            ),
            _check("stored-target", _gold(case), "B3;B7;B1;B5;B4;△;○;□;◇"),
            _check("fixed-codebook-best-score", lure_score, 6),
            _check(
                "unique-fixed-codebook-mapping",
                lure_best,
                [("B1", "B5", "B4", "B3", "B7")],
            ),
            _check("stored-lure", _lure(case), "B1;B5;B4;B3;B7;○;◇;△;□"),
            _check("copy-equals-lure", _copy(case), _lure(case)),
        ],
    )


@register("HARD-P2-L4-02")
def verify_hard_p2_l4_02(case: Case) -> VerificationResult:
    symbols = "abcdef"
    subsets = [
        "".join(group) for size in range(len(symbols) + 1) for group in combinations(symbols, size)
    ]
    reading_values = [
        65,
        52,
        24,
        32,
        90,
        50,
        22,
        48,
        17,
        75,
        43,
        89,
        93,
        88,
        66,
        45,
        19,
        43,
        88,
        44,
        65,
        23,
        86,
        47,
        11,
        82,
        34,
        12,
        42,
        24,
        25,
        89,
        43,
        3,
        14,
        34,
        31,
        53,
        31,
        80,
        67,
        38,
        51,
        47,
        75,
        36,
        66,
        40,
        8,
        96,
        14,
        4,
        93,
        88,
        15,
        11,
        37,
        72,
        56,
        83,
        29,
        95,
        76,
        56,
    ]
    readings = dict(zip(subsets, reading_values, strict=True))
    modulus = 97

    recursive: dict[str, int] = {}
    for subset in subsets:
        proper_total = sum(
            recursive[lower]
            for lower in subsets
            if len(lower) < len(subset) and set(lower) <= set(subset)
        )
        recursive[subset] = (readings[subset] - proper_total) % modulus

    closed_form = {
        subset: sum(
            (-1) ** (len(subset) - len(lower)) * readings[lower]
            for lower in subsets
            if set(lower) <= set(subset)
        )
        % modulus
        for subset in subsets
    }
    reconstructed = {
        subset: sum(recursive[lower] for lower in subsets if set(lower) <= set(subset)) % modulus
        for subset in subsets
    }

    reverse: dict[str, int] = {}
    for subset in reversed(subsets):
        strict_upper_total = sum(
            reverse[upper]
            for upper in subsets
            if len(upper) > len(subset) and set(subset) <= set(upper)
        )
        reverse[subset] = (readings[subset] - strict_upper_total) % modulus

    queries = ["abcf", "acdef", "bcdef", "abcdef"]
    target_values = [recursive[query] for query in queries]
    reverse_values = [reverse[query] for query in queries]
    source_observed = {1: 11, 2: 48, 3: 20, 6: 12, 7: 35, 14: 56, 21: 89, 42: 31}
    source_answer = (
        source_observed[42]
        - source_observed[21]
        - source_observed[14]
        - source_observed[6]
        + source_observed[7]
        + source_observed[3]
        + source_observed[2]
        - source_observed[1]
    ) % modulus

    return _result(
        case,
        [
            _check("all-64-inversions-agree", recursive, closed_form),
            _check("forward-reconstruction", reconstructed, readings),
            _check("source-divisor-inversion", source_answer, 63),
            _check("query-values", target_values, [69, 53, 96, 24]),
            _check("stored-target", _gold(case), ";".join(map(str, target_values))),
            _check("reverse-query-values", reverse_values, [89, 39, 20, 56]),
            _check("stored-lure", _lure(case), ";".join(map(str, reverse_values))),
            _check("copy-equals-lure", _copy(case), _lure(case)),
        ],
    )


def _bareiss_determinant(matrix: list[list[int]]) -> int:
    work = [row[:] for row in matrix]
    if not work:
        return 1
    sign = 1
    previous_pivot = 1
    for pivot_index in range(len(work) - 1):
        if work[pivot_index][pivot_index] == 0:
            swap_index = next(
                (
                    row_index
                    for row_index in range(pivot_index + 1, len(work))
                    if work[row_index][pivot_index] != 0
                ),
                None,
            )
            if swap_index is None:
                return 0
            work[pivot_index], work[swap_index] = (
                work[swap_index],
                work[pivot_index],
            )
            sign *= -1
        pivot = work[pivot_index][pivot_index]
        for row_index in range(pivot_index + 1, len(work)):
            for column_index in range(pivot_index + 1, len(work)):
                numerator = (
                    work[row_index][column_index] * pivot
                    - work[row_index][pivot_index] * work[pivot_index][column_index]
                )
                work[row_index][column_index] = numerator // previous_pivot
        previous_pivot = pivot
    return sign * work[-1][-1]


def _directed_laplacians(
    nodes: list[str], edges: list[tuple[str, str, int]]
) -> tuple[list[list[int]], list[list[int]]]:
    index = {node: node_index for node_index, node in enumerate(nodes)}
    outgoing = [[0] * len(nodes) for _ in nodes]
    incoming = [[0] * len(nodes) for _ in nodes]
    for source, target, weight in edges:
        source_index = index[source]
        target_index = index[target]
        outgoing[source_index][source_index] += weight
        outgoing[source_index][target_index] -= weight
        incoming[target_index][target_index] += weight
        incoming[target_index][source_index] -= weight
    return outgoing, incoming


def _principal_minor(matrix: list[list[int]], deleted: int) -> list[list[int]]:
    return [
        [value for column_index, value in enumerate(row) if column_index != deleted]
        for row_index, row in enumerate(matrix)
        if row_index != deleted
    ]


@register("HARD-P2-L4-03")
def verify_hard_p2_l4_03(case: Case) -> VerificationResult:
    source_nodes = list("UVWR")
    source_edges = [
        ("U", "V", 2),
        ("U", "R", 1),
        ("V", "W", 3),
        ("V", "R", 2),
        ("W", "U", 1),
        ("W", "R", 4),
    ]
    source_laplacian, _ = _directed_laplacians(source_nodes, source_edges)
    source_tree_count = _bareiss_determinant(
        _principal_minor(source_laplacian, source_nodes.index("R"))
    )

    source_choices = {
        node: [(target, weight) for source, target, weight in source_edges if source == node]
        for node in "UVW"
    }
    source_exhaustive = 0
    for choices in product(*(source_choices[node] for node in "UVW")):
        successors = {node: target for node, (target, _weight) in zip("UVW", choices, strict=True)}
        valid = True
        for start in "UVW":
            visited: set[str] = set()
            current = start
            while current != "R":
                if current in visited:
                    valid = False
                    break
                visited.add(current)
                current = successors[current]
            if not valid:
                break
        if valid:
            source_exhaustive += product_weight(choices)

    target_nodes = list("ABCDEFG")
    target_edges = [
        ("A", "C", 5),
        ("A", "D", 2),
        ("A", "B", 4),
        ("B", "C", 5),
        ("B", "D", 5),
        ("B", "E", 5),
        ("C", "G", 1),
        ("C", "F", 3),
        ("C", "A", 2),
        ("D", "E", 3),
        ("D", "G", 2),
        ("D", "F", 4),
        ("E", "D", 2),
        ("E", "B", 2),
        ("E", "G", 4),
        ("F", "G", 4),
        ("F", "A", 4),
        ("F", "E", 2),
        ("G", "D", 3),
        ("G", "F", 2),
        ("G", "B", 4),
    ]
    outgoing, incoming = _directed_laplacians(target_nodes, target_edges)
    root_index = target_nodes.index("G")
    toward_root = _bareiss_determinant(_principal_minor(outgoing, root_index))
    away_from_root = _bareiss_determinant(_principal_minor(incoming, root_index))

    return _result(
        case,
        [
            _check("source-matrix-tree-count", source_tree_count, 69),
            _check("source-exhaustive-count", source_exhaustive, source_tree_count),
            _check("target-toward-root-count", toward_root, 326980),
            _check("target-modulo", toward_root % 1009, 64),
            _check("stored-target", _gold(case), str(toward_root % 1009)),
            _check("lure-away-from-root-count", away_from_root, 232700),
            _check("lure-modulo", away_from_root % 1009, 630),
            _check("stored-lure", _lure(case), str(away_from_root % 1009)),
            _check("copy-equals-lure", _copy(case), _lure(case)),
        ],
    )


def product_weight(choices: tuple[tuple[str, int], ...]) -> int:
    result = 1
    for _target, weight in choices:
        result *= weight
    return result


def _polynomial_multiply(left: list[int], right: list[int]) -> list[int]:
    result = [0] * (len(left) + len(right) - 1)
    for left_degree, left_value in enumerate(left):
        for right_degree, right_value in enumerate(right):
            result[left_degree + right_degree] += left_value * right_value
    return result


def _polynomial_determinant(matrix: list[list[list[int]]]) -> list[int]:
    size = len(matrix)
    determinant = [0] * (size + 1)
    for column_assignment in permutations(range(size)):
        inversions = sum(
            column_assignment[left] > column_assignment[right]
            for left in range(size)
            for right in range(left + 1, size)
        )
        term = [1]
        for row, column in enumerate(column_assignment):
            term = _polynomial_multiply(term, matrix[row][column])
        sign = -1 if inversions % 2 else 1
        for degree, coefficient in enumerate(term):
            determinant[degree] += sign * coefficient
    return determinant


def _spectrum_laplacian_minor(
    nodes: Sequence[str],
    root: str,
    edges: dict[str, list[tuple[str, int, bool]]],
) -> list[list[list[int]]]:
    non_root = [node for node in nodes if node != root]
    index = {node: node_index for node_index, node in enumerate(non_root)}
    matrix = [[[0, 0] for _ in non_root] for _ in non_root]
    for source in non_root:
        source_index = index[source]
        for target, weight, marked in edges[source]:
            degree = int(marked)
            matrix[source_index][source_index][degree] += weight
            if target != root:
                matrix[source_index][index[target]][degree] -= weight
    return matrix


def _enumerate_spectrum_successors(
    non_root: Sequence[str],
    root: str,
    edges: dict[str, list[tuple[str, int, bool]]],
) -> list[int]:
    coefficients = [0] * (len(non_root) + 1)
    for choices in product(*(edges[node] for node in non_root)):
        successors = {
            node: target for node, (target, _weight, _marked) in zip(non_root, choices, strict=True)
        }
        valid = True
        for start in non_root:
            visited: set[str] = set()
            current = start
            while current != root:
                if current in visited:
                    valid = False
                    break
                visited.add(current)
                current = successors[current]
            if not valid:
                break
        if not valid:
            continue
        marked_count = sum(marked for _target, _weight, marked in choices)
        weight_product = 1
        for _target, weight, _marked in choices:
            weight_product *= weight
        coefficients[marked_count] += weight_product
    return coefficients


@register("HARD-P2-L4-04")
def verify_hard_p2_l4_04(case: Case) -> VerificationResult:
    source_edges = {
        "U": [("V", 2, True), ("R", 1, False)],
        "V": [("W", 3, False), ("R", 2, True)],
        "W": [("U", 1, True), ("R", 4, False)],
    }
    source_exhaustive = _enumerate_spectrum_successors("UVW", "R", source_edges)
    source_determinant = _polynomial_determinant(
        _spectrum_laplacian_minor("UVWR", "R", source_edges)
    )

    target_edges = {
        "A": [("C", 5, True), ("D", 2, False), ("B", 4, True)],
        "B": [("C", 5, False), ("D", 5, True), ("E", 5, False)],
        "C": [("G", 1, True), ("F", 3, False), ("A", 2, True)],
        "D": [("E", 3, False), ("G", 2, True), ("F", 4, True)],
        "E": [("D", 2, True), ("B", 2, False), ("G", 4, False)],
        "F": [("G", 4, False), ("A", 4, True), ("E", 2, True)],
    }
    target_exhaustive = _enumerate_spectrum_successors("ABCDEF", "G", target_edges)
    target_determinant = _polynomial_determinant(
        _spectrum_laplacian_minor("ABCDEFG", "G", target_edges)
    )
    expected_coefficients = [3600, 32280, 83520, 107980, 73320, 23440, 2840]

    return _result(
        case,
        [
            _check("source-spectrum-enumeration", source_exhaustive, [12, 35, 18, 4]),
            _check("source-polynomial-determinant", source_determinant, source_exhaustive),
            _check("target-spectrum-enumeration", target_exhaustive, expected_coefficients),
            _check("target-polynomial-determinant", target_determinant, target_exhaustive),
            _check("all-spectrum-total", sum(target_exhaustive), 326980),
            _check("exactly-three-v-count", target_exhaustive[3], 107980),
            _check("target-modulo", target_exhaustive[3] % 1009, 17),
            _check("stored-target", _gold(case), str(target_exhaustive[3] % 1009)),
            _check("unfiltered-modulo", sum(target_exhaustive) % 1009, 64),
            _check("stored-lure", _lure(case), str(sum(target_exhaustive) % 1009)),
            _check("copy-equals-lure", _copy(case), _lure(case)),
        ],
    )


@register("HARD-P2-L4-05")
def verify_hard_p2_l4_05(case: Case) -> VerificationResult:
    source_nodes = [f"U{index}" for index in range(1, 9)]
    source_edges = {
        "U1": [("U2", 2, True), ("U4", 5, False), ("R", 3, False)],
        "U2": [("U3", 4, False), ("U5", 2, True), ("R", 6, False)],
        "U3": [("U4", 3, True), ("U6", 4, False), ("R", 2, True)],
        "U4": [("U5", 5, False), ("U7", 3, True), ("R", 4, False)],
        "U5": [("U6", 2, True), ("U8", 6, False), ("R", 5, True)],
        "U6": [("U7", 7, False), ("U1", 2, True), ("R", 3, False)],
        "U7": [("U8", 4, True), ("U2", 5, False), ("R", 2, False)],
        "U8": [("U1", 3, False), ("U3", 7, True), ("R", 4, True)],
    }
    base_exhaustive = _enumerate_spectrum_successors(source_nodes, "R", source_edges)
    base_determinant = _polynomial_determinant(
        _spectrum_laplacian_minor([*source_nodes, "R"], "R", source_edges)
    )

    target_nodes = list("FBHDAGCE")
    target_edges = {
        "F": [("B", 2, True), ("D", 5, False), ("Z", 3, False)],
        "B": [("H", 4, False), ("A", 2, True), ("Z", 6, False)],
        "H": [("D", 3, True), ("G", 9, False), ("Z", 2, True)],
        "D": [("A", 5, False), ("C", 3, True), ("Z", 4, False)],
        "A": [("G", 2, True), ("E", 6, False), ("Z", 5, True)],
        "G": [("C", 7, False), ("F", 2, True), ("Z", 3, False)],
        "C": [("E", 4, True), ("B", 5, False), ("Z", 2, False)],
        "E": [("F", 3, False), ("H", 7, True), ("Z", 4, True)],
    }
    modified_exhaustive = _enumerate_spectrum_successors(target_nodes, "Z", target_edges)
    modified_determinant = _polynomial_determinant(
        _spectrum_laplacian_minor([*target_nodes, "Z"], "Z", target_edges)
    )
    unweighted_edges = {
        node: [(target, 1, marked) for target, _weight, marked in edges]
        for node, edges in target_edges.items()
    }
    unweighted = _enumerate_spectrum_successors(target_nodes, "Z", unweighted_edges)

    expected_base = [
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
    expected_modified = [
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
    expected_sensitivity = [
        473760,
        4506480,
        8599776,
        7211176,
        3180720,
        735296,
        89304,
        5280,
        0,
    ]
    derived_sensitivity = [
        (modified - base) // 5
        for base, modified in zip(base_exhaustive, modified_exhaustive, strict=True)
    ]

    return _result(
        case,
        [
            _check("baseline-exhaustive", base_exhaustive, expected_base),
            _check("baseline-polynomial-determinant", base_determinant, base_exhaustive),
            _check("modified-exhaustive", modified_exhaustive, expected_modified),
            _check(
                "modified-polynomial-determinant",
                modified_determinant,
                modified_exhaustive,
            ),
            _check("unit-sensitivity", derived_sensitivity, expected_sensitivity),
            _check(
                "coefficient-update",
                base_exhaustive[4] + 5 * expected_sensitivity[4],
                modified_exhaustive[4],
            ),
            _check("source-answer", case.source.answer, "600"),
            _check("target-modulo", modified_exhaustive[4] % 1000, 200),
            _check("stored-target", _gold(case), str(modified_exhaustive[4] % 1000)),
            _check(
                "unweighted-spectrum",
                unweighted,
                [21, 224, 808, 1479, 1545, 963, 343, 59, 3],
            ),
            _check("unweighted-modulo", unweighted[4] % 1000, 545),
            _check("stored-lure", _lure(case), str(unweighted[4] % 1000)),
            _check("copy-equals-lure", _copy(case), _lure(case)),
        ],
    )
