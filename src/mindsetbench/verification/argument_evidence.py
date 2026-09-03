from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum


class Stance(StrEnum):
    SUPPORT = "support"
    OPPOSE = "oppose"


class Verdict(StrEnum):
    SUPPORTED = "SUPPORTED"
    REJECTED = "REJECTED"
    CONTESTED = "CONTESTED"
    UNCORROBORATED = "UNCORROBORATED"


@dataclass(frozen=True, slots=True)
class EvidenceNode:
    """A provenance node; only report nodes carry a claim and stance."""

    node_id: str
    parents: tuple[str, ...] = ()
    claim: str | None = None
    stance: Stance | None = None

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("evidence node id must not be empty")
        carries_claim = self.claim is not None or self.stance is not None
        if carries_claim and (not self.claim or self.stance is None):
            raise ValueError("claim and stance must be set together")

    @property
    def is_report(self) -> bool:
        return self.claim is not None


@dataclass(frozen=True, slots=True)
class ClaimAssessment:
    verdict: Verdict
    supporting_groups: frozenset[str]
    opposing_groups: frozenset[str]


def validate_evidence_graph(nodes: Mapping[str, EvidenceNode]) -> None:
    for key, node in nodes.items():
        if key != node.node_id:
            raise ValueError(f"node key {key!r} does not match id {node.node_id!r}")
        missing = [parent for parent in node.parents if parent not in nodes]
        if missing:
            raise ValueError(f"node {node.node_id!r} has missing parents {missing}")

    state: dict[str, int] = {}

    def visit(node_id: str) -> None:
        marker = state.get(node_id, 0)
        if marker == 1:
            raise ValueError(f"evidence graph contains a cycle at {node_id!r}")
        if marker == 2:
            return
        state[node_id] = 1
        for parent in nodes[node_id].parents:
            visit(parent)
        state[node_id] = 2

    for node_id in nodes:
        visit(node_id)


def ultimate_roots(node_id: str, nodes: Mapping[str, EvidenceNode]) -> frozenset[str]:
    validate_evidence_graph(nodes)
    return _root_resolver(nodes)(node_id)


def _root_resolver(
    nodes: Mapping[str, EvidenceNode],
) -> Callable[[str], frozenset[str]]:
    memo: dict[str, frozenset[str]] = {}

    def resolve(current_id: str) -> frozenset[str]:
        if current_id in memo:
            return memo[current_id]
        node = nodes[current_id]
        roots = (
            frozenset({current_id})
            if not node.parents
            else frozenset().union(*(resolve(parent) for parent in node.parents))
        )
        memo[current_id] = roots
        return roots

    return resolve


def assess_claims(
    nodes: Mapping[str, EvidenceNode],
    claims: Sequence[str],
    *,
    invalid_roots: Iterable[str] = (),
    independence_groups: Mapping[str, str] | None = None,
    threshold: int = 2,
) -> dict[str, ClaimAssessment]:
    """Classify claims after tracing reports to valid independent provenance groups."""

    if threshold < 1:
        raise ValueError("threshold must be at least one")
    validate_evidence_graph(nodes)
    resolve_roots = _root_resolver(nodes)
    invalid = frozenset(invalid_roots)
    unknown_invalid = invalid - nodes.keys()
    if unknown_invalid:
        raise ValueError(f"invalid roots are absent from graph: {sorted(unknown_invalid)}")

    groups = independence_groups or {}
    unknown_group_roots = groups.keys() - nodes.keys()
    if unknown_group_roots:
        raise ValueError(
            f"independence groups reference absent roots: {sorted(unknown_group_roots)}"
        )

    result: dict[str, ClaimAssessment] = {}
    for claim in claims:
        by_stance = {Stance.SUPPORT: set(), Stance.OPPOSE: set()}
        for node in nodes.values():
            if node.claim != claim:
                continue
            assert node.stance is not None
            valid_roots = resolve_roots(node.node_id) - invalid
            by_stance[node.stance].update(groups.get(root, root) for root in valid_roots)

        supporting = frozenset(by_stance[Stance.SUPPORT])
        opposing = frozenset(by_stance[Stance.OPPOSE])
        support_met = len(supporting) >= threshold
        oppose_met = len(opposing) >= threshold
        if support_met and oppose_met:
            verdict = Verdict.CONTESTED
        elif support_met:
            verdict = Verdict.SUPPORTED
        elif oppose_met:
            verdict = Verdict.REJECTED
        else:
            verdict = Verdict.UNCORROBORATED
        result[claim] = ClaimAssessment(verdict, supporting, opposing)
    return result


def surface_document_assessments(
    nodes: Mapping[str, EvidenceNode],
    claims: Sequence[str],
    *,
    directly_invalid_nodes: Iterable[str] = (),
    threshold: int = 2,
) -> dict[str, ClaimAssessment]:
    """Negative control: count report documents without tracing shared provenance."""

    if threshold < 1:
        raise ValueError("threshold must be at least one")
    validate_evidence_graph(nodes)
    invalid = frozenset(directly_invalid_nodes)
    unknown_invalid = invalid - nodes.keys()
    if unknown_invalid:
        raise ValueError(f"invalid nodes are absent from graph: {sorted(unknown_invalid)}")
    result: dict[str, ClaimAssessment] = {}
    for claim in claims:
        by_stance = {Stance.SUPPORT: set(), Stance.OPPOSE: set()}
        for node in nodes.values():
            if node.node_id in invalid or node.claim != claim:
                continue
            assert node.stance is not None
            by_stance[node.stance].add(node.node_id)
        supporting = frozenset(by_stance[Stance.SUPPORT])
        opposing = frozenset(by_stance[Stance.OPPOSE])
        support_met = len(supporting) >= threshold
        oppose_met = len(opposing) >= threshold
        if support_met and oppose_met:
            verdict = Verdict.CONTESTED
        elif support_met:
            verdict = Verdict.SUPPORTED
        elif oppose_met:
            verdict = Verdict.REJECTED
        else:
            verdict = Verdict.UNCORROBORATED
        result[claim] = ClaimAssessment(verdict, supporting, opposing)
    return result


def verdict_parts(
    assessments: Mapping[str, ClaimAssessment], claims: Sequence[str]
) -> list[str]:
    return [f"{claim}={assessments[claim].verdict.value}" for claim in claims]
