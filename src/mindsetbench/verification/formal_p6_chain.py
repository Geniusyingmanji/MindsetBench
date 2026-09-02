from __future__ import annotations

import re
from itertools import permutations

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

Relation = tuple[str, str, str]


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


def _alignment_score(
    source_relations: set[Relation],
    target_relations: set[Relation],
    node_mapping: dict[str, str],
    predicate_mapping: dict[str, str],
) -> int:
    return sum(
        (node_mapping[source], predicate_mapping[predicate], node_mapping[target])
        in target_relations
        for source, predicate, target in source_relations
    )


def _rank_alignments(
    source_relations: set[Relation],
    target_relations: set[Relation],
    *,
    anchors: dict[str, str],
    source_free: list[str],
    target_free: list[str],
    source_predicates: list[str],
    target_predicates: list[str],
) -> list[tuple[int, tuple[str, ...], tuple[str, ...]]]:
    scored: list[tuple[int, tuple[str, ...], tuple[str, ...]]] = []
    for node_assignment in permutations(target_free, len(source_free)):
        node_mapping = {**anchors, **dict(zip(source_free, node_assignment, strict=True))}
        for predicate_assignment in permutations(target_predicates, len(source_predicates)):
            predicate_mapping = dict(zip(source_predicates, predicate_assignment, strict=True))
            score = _alignment_score(
                source_relations,
                target_relations,
                node_mapping,
                predicate_mapping,
            )
            scored.append((score, node_assignment, predicate_assignment))
    return sorted(scored, reverse=True)


def _best_with_fixed_codebook(
    source_relations: set[Relation],
    target_relations: set[Relation],
    *,
    anchors: dict[str, str],
    source_free: list[str],
    target_free: list[str],
    predicate_mapping: dict[str, str],
) -> tuple[int, list[tuple[str, ...]]]:
    scored = []
    for node_assignment in permutations(target_free, len(source_free)):
        node_mapping = {**anchors, **dict(zip(source_free, node_assignment, strict=True))}
        score = _alignment_score(
            source_relations,
            target_relations,
            node_mapping,
            predicate_mapping,
        )
        scored.append((score, node_assignment))
    best_score = max(score for score, _ in scored)
    return best_score, [assignment for score, assignment in scored if score == best_score]


def _verify_alignment_case(
    case: Case,
    *,
    source_relations: set[Relation],
    target_relations: set[Relation],
    anchors: dict[str, str],
    source_free: list[str],
    target_free: list[str],
    source_predicates: list[str],
    target_predicates: list[str],
    expected_nodes: tuple[str, ...],
    expected_predicates: tuple[str, ...],
    lure_nodes: tuple[str, ...],
    lure_predicates: tuple[str, ...],
    expected_best_score: int,
    expected_lure_score: int,
) -> VerificationResult:
    ranked = _rank_alignments(
        source_relations,
        target_relations,
        anchors=anchors,
        source_free=source_free,
        target_free=target_free,
        source_predicates=source_predicates,
        target_predicates=target_predicates,
    )
    best_score = ranked[0][0]
    best = [(nodes, predicates) for score, nodes, predicates in ranked if score == best_score]
    fixed_mapping = dict(zip(source_predicates, lure_predicates, strict=True))
    lure_score, fixed_best = _best_with_fixed_codebook(
        source_relations,
        target_relations,
        anchors=anchors,
        source_free=source_free,
        target_free=target_free,
        predicate_mapping=fixed_mapping,
    )
    expected_text = ";".join((*expected_nodes, *expected_predicates))
    lure_text = ";".join((*lure_nodes, *lure_predicates))
    return _result(
        case,
        [
            _check("joint-best-score", best_score, expected_best_score),
            _check("unique-joint-best", best, [(expected_nodes, expected_predicates)]),
            _check("fixed-codebook-best-score", lure_score, expected_lure_score),
            _check("unique-fixed-codebook-best", fixed_best, [lure_nodes]),
            _check("stored-target", _gold(case), expected_text),
            _check("stored-lure", _lure(case), lure_text),
            _check("copy-equals-lure", _copy(case), _lure(case)),
            _check("copy-differs-from-target", _copy(case) != _gold(case), True),
        ],
    )


@register("FORMAL-P6-ALIGN-L0-01")
def verify_formal_p6_align_l0_01(case: Case) -> VerificationResult:
    return _verify_alignment_case(
        case,
        source_relations={("X1", "a", "X2"), ("X2", "b", "X3")},
        target_relations={("Y1", "○", "Y3"), ("Y2", "◇", "Y1")},
        anchors={"X1": "Y2", "X3": "Y3"},
        source_free=["X2"],
        target_free=["Y1"],
        source_predicates=["a", "b"],
        target_predicates=["○", "◇"],
        expected_nodes=("Y1",),
        expected_predicates=("◇", "○"),
        lure_nodes=("Y1",),
        lure_predicates=("○", "◇"),
        expected_best_score=2,
        expected_lure_score=0,
    )


@register("FORMAL-P6-ALIGN-L1-01")
def verify_formal_p6_align_l1_01(case: Case) -> VerificationResult:
    return _verify_alignment_case(
        case,
        source_relations={
            ("A1", "nex", "A2"),
            ("A2", "vul", "A3"),
            ("A2", "nex", "A4"),
            ("A4", "vul", "A3"),
        },
        target_relations={
            ("B3", "%", "B1"),
            ("B1", "@", "B4"),
            ("B1", "%", "B2"),
            ("B2", "@", "B4"),
            ("B3", "@", "B2"),
        },
        anchors={"A1": "B3", "A3": "B4"},
        source_free=["A2", "A4"],
        target_free=["B1", "B2"],
        source_predicates=["nex", "vul"],
        target_predicates=["%", "@"],
        expected_nodes=("B1", "B2"),
        expected_predicates=("%", "@"),
        lure_nodes=("B2", "B1"),
        lure_predicates=("@", "%"),
        expected_best_score=4,
        expected_lure_score=1,
    )


@register("FORMAL-P6-ALIGN-L2-01")
def verify_formal_p6_align_l2_01(case: Case) -> VerificationResult:
    return _verify_alignment_case(
        case,
        source_relations={
            ("A1", "n", "A2"),
            ("A2", "v", "A3"),
            ("A3", "s", "A5"),
            ("A2", "s", "A4"),
            ("A4", "n", "A5"),
            ("A3", "n", "A4"),
        },
        target_relations={
            ("B4", "@", "B2"),
            ("B2", "#", "B5"),
            ("B5", "%", "B1"),
            ("B2", "%", "B3"),
            ("B3", "@", "B1"),
            ("B5", "@", "B3"),
            ("B4", "%", "B3"),
            ("B2", "@", "B1"),
            ("B3", "#", "B5"),
        },
        anchors={"A1": "B4", "A5": "B1"},
        source_free=["A2", "A3", "A4"],
        target_free=["B2", "B3", "B5"],
        source_predicates=["n", "v", "s"],
        target_predicates=["@", "#", "%"],
        expected_nodes=("B2", "B5", "B3"),
        expected_predicates=("@", "#", "%"),
        lure_nodes=("B3", "B2", "B5"),
        lure_predicates=("%", "@", "#"),
        expected_best_score=6,
        expected_lure_score=3,
    )


def _full_source_relations() -> set[Relation]:
    return {
        ("A1", "nex", "A2"),
        ("A1", "vul", "A5"),
        ("A3", "sor", "A1"),
        ("A4", "nex", "A1"),
        ("A4", "nex", "A5"),
        ("A4", "sor", "A7"),
        ("A5", "sor", "A7"),
        ("A5", "vul", "A1"),
        ("A6", "sor", "A1"),
        ("A6", "vul", "A5"),
        ("A7", "nex", "A1"),
        ("A7", "nex", "A6"),
        ("A7", "sor", "A3"),
        ("A7", "sor", "A6"),
    }


def _full_target_relations(*, edited: bool) -> set[Relation]:
    relations = {
        ("B1", "#", "B2"),
        ("B1", "#", "B4"),
        ("B2", "#", "B1"),
        ("B2", "#", "B3"),
        ("B2", "#", "B5"),
        ("B2", "%", "B4"),
        ("B2", "%", "B5"),
        ("B3", "#", "B2"),
        ("B3", "#", "B4"),
        ("B3", "@", "B4"),
        ("B4", "%", "B7"),
        ("B4", "@", "B1"),
        ("B4", "@", "B3"),
        ("B5", "#", "B4"),
        ("B5", "@", "B1"),
        ("B5", "@", "B3"),
        ("B6", "#", "B2"),
        ("B6", "%", "B1"),
        ("B6", "%", "B3"),
        ("B6", "%", "B4"),
        ("B2", "@", "B7"),
        ("B3", "#", "B1"),
        ("B7", "@", "B4"),
    }
    if edited:
        relations.remove(("B6", "%", "B3"))
        relations.add(("B1", "@", "B4"))
    return relations


LEFT_NODE_RENAME = {
    "A1": "C5",
    "A2": "C2",
    "A3": "C7",
    "A4": "C1",
    "A5": "C6",
    "A6": "C3",
    "A7": "C4",
}
RIGHT_NODE_RENAME = {
    "B1": "D6",
    "B2": "D2",
    "B3": "D7",
    "B4": "D4",
    "B5": "D1",
    "B6": "D5",
    "B7": "D3",
}
LEFT_PREDICATE_RENAME = {"nex": "tor", "vul": "mek", "sor": "zul"}
RIGHT_PREDICATE_RENAME = {"%": "△", "@": "○", "#": "□"}


def _rename_relations(
    relations: set[Relation],
    nodes: dict[str, str],
    predicates: dict[str, str],
) -> set[Relation]:
    return {
        (nodes[source], predicates[predicate], nodes[target])
        for source, predicate, target in relations
    }


def _parse_full_target_relations(problem: str) -> tuple[set[Relation], set[Relation]]:
    left_section = problem.split("记录为：", 1)[1].split("档案右", 1)[0]
    right_section = problem.split("记录按归档顺序为：", 1)[1]
    right_section = right_section.split("与旧档案相比", 1)[0].split("已知", 1)[0]
    left = set(re.findall(r"(C\d+)-(tor|mek|zul)-(C\d+)", left_section))
    right = set(re.findall(r"(D\d+)-(△|○|□)-(D\d+)", right_section))
    return left, right


def _verify_full(case: Case, *, edited: bool) -> VerificationResult:
    left = _rename_relations(_full_source_relations(), LEFT_NODE_RENAME, LEFT_PREDICATE_RENAME)
    right = _rename_relations(
        _full_target_relations(edited=edited),
        RIGHT_NODE_RENAME,
        RIGHT_PREDICATE_RENAME,
    )
    expected_nodes = ("D3", "D7", "D5", "D6", "D1") if edited else ("D3", "D6", "D5", "D7", "D1")
    parsed_left, parsed_right = _parse_full_target_relations(case.target.problem)
    result = _verify_alignment_case(
        case,
        source_relations=left,
        target_relations=right,
        anchors={"C5": "D4", "C4": "D2"},
        source_free=["C2", "C7", "C1", "C6", "C3"],
        target_free=["D1", "D3", "D5", "D6", "D7"],
        source_predicates=["tor", "mek", "zul"],
        target_predicates=["△", "○", "□"],
        expected_nodes=expected_nodes,
        expected_predicates=("△", "○", "□"),
        lure_nodes=("D1", "D3", "D5", "D6", "D7"),
        lure_predicates=("△", "□", "○"),
        expected_best_score=14,
        expected_lure_score=8,
    )
    ranked = _rank_alignments(
        left,
        right,
        anchors={"C5": "D4", "C4": "D2"},
        source_free=["C2", "C7", "C1", "C6", "C3"],
        target_free=["D1", "D3", "D5", "D6", "D7"],
        source_predicates=["tor", "mek", "zul"],
        target_predicates=["△", "○", "□"],
    )
    scores = sorted({score for score, _, _ in ranked}, reverse=True)
    lure_nodes = ("D1", "D3", "D5", "D6", "D7")
    lure_node_overlap = sum(
        expected == lure for expected, lure in zip(expected_nodes, lure_nodes, strict=True)
    )
    result.checks.extend(
        [
            _check("target-text-left-relations", parsed_left, left),
            _check("target-text-right-relations", parsed_right, right),
            _check("joint-best-score", scores[0], 14),
            _check("joint-runner-up-score", scores[1], 13),
            _check("lure-node-overlap", lure_node_overlap, 2 if edited else 1),
        ]
    )
    return result


@register("FORMAL-P6-ALIGN-L3-01")
def verify_formal_p6_align_l3_01(case: Case) -> VerificationResult:
    return _verify_full(case, edited=False)


@register("FORMAL-P6-ALIGN-L4-01")
def verify_formal_p6_align_l4_01(case: Case) -> VerificationResult:
    result = _verify_full(case, edited=True)
    baseline_right = _rename_relations(
        _full_target_relations(edited=False),
        RIGHT_NODE_RENAME,
        RIGHT_PREDICATE_RENAME,
    )
    edited_right = _rename_relations(
        _full_target_relations(edited=True),
        RIGHT_NODE_RENAME,
        RIGHT_PREDICATE_RENAME,
    )
    result.checks.extend(
        [
            _check("single-deletion", baseline_right - edited_right, {("D5", "△", "D7")}),
            _check("single-addition", edited_right - baseline_right, {("D6", "○", "D4")}),
        ]
    )
    return result
