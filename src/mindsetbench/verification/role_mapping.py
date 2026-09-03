from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import permutations

Edge = tuple[str, str, str]


@dataclass(frozen=True, slots=True)
class RelationalGraph:
    nodes: frozenset[str]
    edges: frozenset[Edge]

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("relational graph must contain at least one node")
        unknown = {
            endpoint
            for subject, _, object_ in self.edges
            for endpoint in (subject, object_)
            if endpoint not in self.nodes
        }
        if unknown:
            raise ValueError(f"edges reference unknown nodes: {sorted(unknown)}")


@dataclass(frozen=True, slots=True)
class MappingMatch:
    mapping: Mapping[str, str]
    preserved_edges: frozenset[Edge]
    missing_edges: frozenset[Edge]
    added_induced_edges: frozenset[Edge]

    @property
    def score(self) -> int:
        return len(self.preserved_edges)


def evaluate_mapping(
    source: RelationalGraph,
    target: RelationalGraph,
    mapping: Mapping[str, str],
    relation_map: Mapping[str, str],
) -> MappingMatch:
    if set(mapping) != set(source.nodes):
        raise ValueError("mapping must assign every source node exactly once")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("mapping must be injective")
    if not set(mapping.values()) <= target.nodes:
        raise ValueError("mapping references unknown target nodes")

    source_relations = {relation for _, relation, _ in source.edges}
    missing_relation_names = source_relations - relation_map.keys()
    if missing_relation_names:
        raise ValueError(
            f"relation map is incomplete: {sorted(missing_relation_names)}"
        )

    expected = frozenset(
        (mapping[subject], relation_map[relation], mapping[object_])
        for subject, relation, object_ in source.edges
    )
    preserved = expected & target.edges
    missing = expected - target.edges
    mapped_nodes = frozenset(mapping.values())
    induced = frozenset(
        edge
        for edge in target.edges
        if edge[0] in mapped_nodes and edge[2] in mapped_nodes
    )
    return MappingMatch(mapping, preserved, missing, induced - expected)


def best_mappings(
    source: RelationalGraph,
    target: RelationalGraph,
    role_order: Sequence[str],
    relation_map: Mapping[str, str],
) -> list[MappingMatch]:
    if set(role_order) != set(source.nodes) or len(role_order) != len(source.nodes):
        raise ValueError("role order must contain every source node exactly once")
    if len(target.nodes) < len(source.nodes):
        raise ValueError("target graph has fewer nodes than the source graph")

    best_score = -1
    matches: list[MappingMatch] = []
    for targets in permutations(sorted(target.nodes), len(role_order)):
        mapping = dict(zip(role_order, targets, strict=True))
        match = evaluate_mapping(source, target, mapping, relation_map)
        if match.score > best_score:
            best_score = match.score
            matches = [match]
        elif match.score == best_score:
            matches.append(match)
    return matches
