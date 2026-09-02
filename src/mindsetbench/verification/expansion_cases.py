from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable, Iterable
from itertools import combinations, permutations

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


def _gold(case: Case) -> str:
    return case.target.answer.legacy_value()


def _lure_gold(case: Case) -> str | None:
    return case.lure.answer.legacy_value() if case.lure and case.lure.answer else None


def _copy_gold(case: Case) -> str | None:
    return case.copy_probe.answer.legacy_value() if case.copy_probe else None


def _unique_order(items: str, predicate: Callable[[dict[str, int]], bool]) -> list[str]:
    solutions = []
    for order in permutations(items):
        positions = {item: index + 1 for index, item in enumerate(order)}
        if predicate(positions):
            solutions.append("".join(order))
    return solutions


@register("V1-P2-L0-01")
def verify_v1_p2_l0_01(case: Case) -> VerificationResult:
    solutions = _unique_order(
        "EFGH",
        lambda p: p["E"] < p["G"] and p["F"] == p["H"] + 1 and p["G"] != 4,
    )
    return _result(
        case,
        [
            _check("unique-solution", solutions, ["EGHF"]),
            _check("stored-target", _gold(case), solutions[0]),
        ],
    )


@register("V1-P2-L1-01")
def verify_v1_p2_l1_01(case: Case) -> VerificationResult:
    solutions = _unique_order(
        "PQRS",
        lambda p: p["P"] < p["R"] and p["Q"] == p["S"] + 1 and p["R"] != 4,
    )
    return _result(
        case,
        [
            _check("unique-solution", solutions, ["PRSQ"]),
            _check("stored-target", _gold(case), solutions[0]),
        ],
    )


@register("V1-P2-L2-01")
def verify_v1_p2_l2_01(case: Case) -> VerificationResult:
    target = _unique_order(
        "WXYZ",
        lambda p: p["W"] < p["Y"] and p["X"] == p["Z"] + 1 and p["Y"] != 4,
    )
    lure = _unique_order(
        "WXYZ",
        lambda p: p["W"] < p["Y"] and p["Z"] == p["X"] + 1 and p["Y"] != 4,
    )
    return _result(
        case,
        [
            _check("target-unique", target, ["WYZX"]),
            _check("lure-unique", lure, ["WYXZ"]),
            _check("stored-target", _gold(case), target[0]),
            _check("stored-lure", _lure_gold(case), lure[0]),
        ],
    )


@register("V1-P2-L3-01")
def verify_v1_p2_l3_01(case: Case) -> VerificationResult:
    target = _unique_order(
        "EFGHX",
        lambda p: (
            p["E"] < p["G"]
            and p["F"] == p["H"] + 1
            and p["G"] != 4
            and p["E"] == p["X"] + 1
            and p["H"] == 1
        ),
    )
    lure = _unique_order(
        "EFGHX",
        lambda p: (
            p["H"] == 1 and p["F"] == p["H"] + 1 and p["E"] < p["G"] and p["G"] != 5 and p["X"] == 5
        ),
    )
    copy = _copy_gold(case)
    return _result(
        case,
        [
            _check("target-unique", target, ["HFXEG"]),
            _check("lure-unique", lure, ["HFEGX"]),
            _check("copy-probe-invalid", copy not in target, True),
            _check("stored-target", _gold(case), target[0]),
            _check("stored-lure", _lure_gold(case), lure[0]),
        ],
    )


def _truth_counts() -> dict[str, int]:
    counts = {}
    for culprit in "ABCD":
        statements = [culprit == "B", culprit != "B", culprit == "D", culprit != "A"]
        counts[culprit] = sum(statements)
    return counts


@register("V1-P2-L4-01")
def verify_v1_p2_l4_01(case: Case) -> VerificationResult:
    counts = _truth_counts()
    target = [culprit for culprit, count in counts.items() if count == 1]
    lure = [culprit for culprit, count in counts.items() if count == 3]
    return _result(
        case,
        [
            _check("truth-counts", counts, {"A": 1, "B": 2, "C": 2, "D": 3}),
            _check("target-unique", target, ["A"]),
            _check("lure-unique", lure, ["D"]),
            _check("copy-is-max-satisfaction", _copy_gold(case), max(counts, key=counts.get)),
            _check("stored-target", _gold(case), target[0]),
            _check("stored-lure", _lure_gold(case), lure[0]),
        ],
    )


Edge = tuple[str, str]


def _descendants(edges: set[Edge], start: str) -> set[str]:
    children: dict[str, set[str]] = defaultdict(set)
    for parent, child in edges:
        children[parent].add(child)
    found: set[str] = set()
    queue = deque(children[start])
    while queue:
        node = queue.popleft()
        if node in found:
            continue
        found.add(node)
        queue.extend(children[node] - found)
    return found


def _ancestors(edges: set[Edge], starts: set[str]) -> set[str]:
    parents: dict[str, set[str]] = defaultdict(set)
    for parent, child in edges:
        parents[child].add(parent)
    found = set(starts)
    queue = deque(starts)
    while queue:
        node = queue.popleft()
        for parent in parents[node] - found:
            found.add(parent)
            queue.append(parent)
    return found


def _d_separated(edges: set[Edge], x: str, y: str, conditioned: set[str]) -> bool:
    relevant = _ancestors(edges, {x, y, *conditioned})
    parents: dict[str, set[str]] = defaultdict(set)
    undirected: dict[str, set[str]] = defaultdict(set)
    for parent, child in edges:
        if parent in relevant and child in relevant:
            parents[child].add(parent)
            undirected[parent].add(child)
            undirected[child].add(parent)
    for child_parents in parents.values():
        for left, right in combinations(child_parents, 2):
            undirected[left].add(right)
            undirected[right].add(left)

    queue = deque([x])
    visited = set(conditioned)
    while queue:
        node = queue.popleft()
        if node == y:
            return False
        if node in visited:
            continue
        visited.add(node)
        queue.extend(undirected[node] - visited)
    return True


def _valid_backdoor_set(edges: set[Edge], x: str, y: str, adjustment: set[str]) -> bool:
    if adjustment & _descendants(edges, x):
        return False
    backdoor_graph = {edge for edge in edges if edge[0] != x}
    return _d_separated(backdoor_graph, x, y, adjustment)


def _minimal_valid_sets(
    edges: set[Edge], x: str, y: str, candidates: Iterable[set[str]]
) -> list[set[str]]:
    valid = [candidate for candidate in candidates if _valid_backdoor_set(edges, x, y, candidate)]
    return [candidate for candidate in valid if not any(other < candidate for other in valid)]


def _verify_single_confounder(
    case: Case, *, confounder: str, treatment: str, outcome: str
) -> VerificationResult:
    edges = {(confounder, treatment), (confounder, outcome), (treatment, outcome)}
    minimal = _minimal_valid_sets(edges, treatment, outcome, [set(), {confounder}])
    expected = [{confounder}]
    return _result(
        case,
        [
            _check("minimal-backdoor-set", minimal, expected),
            _check("stored-target", _gold(case), confounder),
        ],
    )


@register("V1-P3-L0-01")
def verify_v1_p3_l0_01(case: Case) -> VerificationResult:
    return _verify_single_confounder(case, confounder="S", treatment="M", outcome="R")


@register("V1-P3-L1-01")
def verify_v1_p3_l1_01(case: Case) -> VerificationResult:
    return _verify_single_confounder(case, confounder="G", treatment="X", outcome="D")


@register("V1-P3-L2-01")
def verify_v1_p3_l2_01(case: Case) -> VerificationResult:
    result = _verify_single_confounder(case, confounder="C", treatment="X", outcome="Y")
    lure_edges = {("X", "C"), ("C", "Y"), ("X", "Y")}
    lure_minimal = _minimal_valid_sets(lure_edges, "X", "Y", [set(), {"C"}])
    result.checks.extend(
        [
            _check("lure-minimal-set", lure_minimal, [set()]),
            _check("stored-lure", _lure_gold(case), "NONE"),
        ]
    )
    return result


@register("V1-P3-L3-01")
def verify_v1_p3_l3_01(case: Case) -> VerificationResult:
    edges = {("C", "X"), ("C", "Y"), ("X", "M"), ("M", "Y"), ("X", "Y")}
    candidates = [set(), {"C"}, {"M"}, {"C", "M"}]
    minimal = _minimal_valid_sets(edges, "X", "Y", candidates)
    return _result(
        case,
        [
            _check("minimal-total-effect-set", minimal, [{"C"}]),
            _check("mediator-is-descendant", "M" in _descendants(edges, "X"), True),
            _check("copy-controls-mediator", _copy_gold(case), "C+M"),
            _check("stored-target", _gold(case), "C"),
            _check("stored-lure", _lure_gold(case), "C+M"),
        ],
    )


@register("V1-P3-L4-01")
def verify_v1_p3_l4_01(case: Case) -> VerificationResult:
    selected = [(a, b) for a in (0, 1) for b in (0, 1) if a or b]
    p_a_given_b1 = sum(a for a, b in selected if b == 1) / sum(b == 1 for _, b in selected)
    p_a_given_b0 = sum(a for a, b in selected if b == 0) / sum(b == 0 for _, b in selected)
    return _result(
        case,
        [
            _check("selected-worlds", selected, [(0, 1), (1, 0), (1, 1)]),
            _check("negative-selected-association", p_a_given_b1 < p_a_given_b0, True),
            _check("no-causal-edge", _gold(case), "NONCAUSAL"),
            _check("stored-copy", _copy_gold(case), "B-CAUSES-A"),
            _check("stored-lure", _lure_gold(case), "B-CAUSES-A"),
        ],
    )


def _basic_violations(
    records: dict[str, dict[str, bool]], trigger: str, obligation: str
) -> list[str]:
    return sorted(
        record_id
        for record_id, facts in records.items()
        if facts[trigger] and not facts[obligation]
    )


def _join(values: Iterable[str]) -> str:
    return ";".join(sorted(values))


@register("V1-P4-L0-01")
def verify_v1_p4_l0_01(case: Case) -> VerificationResult:
    records = {
        "S1": {"cold": True, "insulated": True},
        "S2": {"cold": False, "insulated": False},
        "S3": {"cold": True, "insulated": False},
        "S4": {"cold": False, "insulated": True},
    }
    violations = _basic_violations(records, "cold", "insulated")
    return _result(
        case,
        [
            _check("violations", violations, ["S3"]),
            _check("stored-target", _gold(case), _join(violations)),
        ],
    )


@register("V1-P4-L1-01")
def verify_v1_p4_l1_01(case: Case) -> VerificationResult:
    records = {
        "N1": {"downloaded": True, "logged": True},
        "N2": {"downloaded": False, "logged": False},
        "N3": {"downloaded": True, "logged": False},
        "N4": {"downloaded": False, "logged": True},
    }
    violations = _basic_violations(records, "downloaded", "logged")
    return _result(
        case,
        [
            _check("violations", violations, ["N3"]),
            _check("stored-target", _gold(case), _join(violations)),
        ],
    )


@register("V1-P4-L2-01")
def verify_v1_p4_l2_01(case: Case) -> VerificationResult:
    records = {
        "M1": {"bronze": True, "gloves": True},
        "M2": {"bronze": True, "gloves": False},
        "M3": {"bronze": False, "gloves": False},
        "M4": {"bronze": False, "gloves": True},
    }
    target = _basic_violations(records, "bronze", "gloves")
    lure = _basic_violations(records, "gloves", "bronze")
    return _result(
        case,
        [
            _check("target-violations", target, ["M2"]),
            _check("lure-violations", lure, ["M4"]),
            _check("stored-target", _gold(case), _join(target)),
            _check("stored-lure", _lure_gold(case), _join(lure)),
        ],
    )


@register("V1-P4-L3-01")
def verify_v1_p4_l3_01(case: Case) -> VerificationResult:
    records = {
        "V1": {"entered": True, "permit": True, "firefighter": False, "real_alarm": False},
        "V2": {"entered": True, "permit": False, "firefighter": False, "real_alarm": False},
        "V3": {"entered": True, "permit": False, "firefighter": True, "real_alarm": True},
        "V4": {"entered": True, "permit": False, "firefighter": True, "real_alarm": False},
    }
    strict = _basic_violations(records, "entered", "permit")
    target = sorted(
        record_id
        for record_id in strict
        if not (records[record_id]["firefighter"] and records[record_id]["real_alarm"])
    )
    return _result(
        case,
        [
            _check("strict-violations", strict, ["V2", "V3", "V4"]),
            _check("exception-aware", target, ["V2", "V4"]),
            _check("stored-target", _gold(case), _join(target)),
            _check("stored-copy", _copy_gold(case), _join(strict)),
            _check("stored-lure", _lure_gold(case), _join(strict)),
        ],
    )


@register("V1-P4-L4-01")
def verify_v1_p4_l4_01(case: Case) -> VerificationResult:
    records = {
        "E1": {"supervisor": True, "medical": False, "ethics": False, "embargo": False},
        "E2": {"supervisor": False, "medical": False, "ethics": False, "embargo": False},
        "E3": {"supervisor": False, "medical": True, "ethics": True, "embargo": False},
        "E4": {"supervisor": False, "medical": True, "ethics": True, "embargo": True},
    }
    flat = sorted(record_id for record_id, facts in records.items() if not facts["supervisor"])
    target = sorted(
        record_id
        for record_id, facts in records.items()
        if facts["embargo"]
        or (not facts["supervisor"] and not (facts["medical"] and facts["ethics"]))
    )
    return _result(
        case,
        [
            _check("flat-rule", flat, ["E2", "E3", "E4"]),
            _check("prioritized-rules", target, ["E2", "E4"]),
            _check("stored-target", _gold(case), _join(target)),
            _check("stored-copy", _copy_gold(case), _join(flat)),
            _check("stored-lure", _lure_gold(case), _join(flat)),
        ],
    )


Relation = tuple[str, str, str]


def _subjects_with_relation(relations: set[Relation], predicate: str, target: str) -> list[str]:
    return sorted(
        subject for subject, relation, obj in relations if relation == predicate and obj == target
    )


def _verify_gatekeeper(
    case: Case, relations: set[Relation], predicate: str, endpoint: str, expected: str
) -> VerificationResult:
    matches = _subjects_with_relation(relations, predicate, endpoint)
    return _result(
        case,
        [
            _check("unique-gatekeeper", matches, [expected]),
            _check("stored-target", _gold(case), expected),
        ],
    )


@register("V1-P6-L0-01")
def verify_v1_p6_l0_01(case: Case) -> VerificationResult:
    relations = {("W", "orders", "X"), ("X", "hands", "Y"), ("Y", "approves", "Z")}
    return _verify_gatekeeper(case, relations, "approves", "Z", "Y")


@register("V1-P6-L1-01")
def verify_v1_p6_l1_01(case: Case) -> VerificationResult:
    relations = {("Q", "instructs", "H"), ("H", "hands", "S"), ("S", "approves", "R")}
    return _verify_gatekeeper(case, relations, "approves", "R", "S")


@register("V1-P6-L2-01")
def verify_v1_p6_l2_01(case: Case) -> VerificationResult:
    target_relations = {("R", "signals", "M"), ("M", "hands", "K"), ("K", "releases", "G")}
    lure_relations = {("R", "signals", "K"), ("K", "instructs", "M"), ("M", "releases", "G")}
    result = _verify_gatekeeper(case, target_relations, "releases", "G", "K")
    result.checks.extend(
        [
            _check(
                "lure-gatekeeper", _subjects_with_relation(lure_relations, "releases", "G"), ["M"]
            ),
            _check("stored-lure", _lure_gold(case), "M"),
        ]
    )
    return result


@register("V1-P6-L3-01")
def verify_v1_p6_l3_01(case: Case) -> VerificationResult:
    target_relations = {
        ("R", "plans", "A"),
        ("A", "hands", "F"),
        ("F", "hands", "J"),
        ("J", "certifies", "D"),
    }
    lure_relations = {
        ("R", "plans", "A"),
        ("A", "hands", "F"),
        ("F", "certifies", "D"),
        ("J", "archives", "D"),
    }
    result = _verify_gatekeeper(case, target_relations, "certifies", "D", "J")
    result.checks.extend(
        [
            _check(
                "lure-gatekeeper", _subjects_with_relation(lure_relations, "certifies", "D"), ["F"]
            ),
            _check("stored-copy", _copy_gold(case), "F"),
            _check("stored-lure", _lure_gold(case), "F"),
        ]
    )
    return result


@register("V1-P6-L4-01")
def verify_v1_p6_l4_01(case: Case) -> VerificationResult:
    followers = {"F1", "F2", "F3"}
    sufficient = [
        set(group)
        for size in range(1, len(followers) + 1)
        for group in combinations(sorted(followers), size)
        if len(group) >= 2
    ]
    minimal = [group for group in sufficient if not any(other < group for other in sufficient)]
    return _result(
        case,
        [
            _check(
                "minimal-quorums",
                sorted(tuple(sorted(group)) for group in minimal),
                [("F1", "F2"), ("F1", "F3"), ("F2", "F3")],
            ),
            _check("no-individual-sufficient", all(len(group) > 1 for group in minimal), True),
            _check("collective-role", _gold(case), "QUORUM"),
            _check("stored-copy", _copy_gold(case), "F1"),
            _check("stored-lure", _lure_gold(case), "F1"),
        ],
    )
