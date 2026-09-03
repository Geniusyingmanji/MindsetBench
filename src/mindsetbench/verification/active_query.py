from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import product


@dataclass(frozen=True, slots=True)
class DiagnosticWorld:
    """One still-possible reconstruction and the observations it predicts."""

    world_id: str
    outcome: str
    observations: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not self.world_id.strip():
            raise ValueError("world id must not be empty")
        if not self.outcome.strip():
            raise ValueError(f"world {self.world_id!r} has an empty outcome")
        query_ids = [query_id for query_id, _ in self.observations]
        if len(query_ids) != len(set(query_ids)):
            raise ValueError(f"world {self.world_id!r} repeats a query")
        if any(
            not query_id.strip() or not observation.strip()
            for query_id, observation in self.observations
        ):
            raise ValueError(f"world {self.world_id!r} has a blank query or observation")

    def observation_for(self, query_id: str) -> str:
        try:
            return dict(self.observations)[query_id]
        except KeyError as exc:
            raise ValueError(
                f"world {self.world_id!r} has no observation for {query_id!r}"
            ) from exc


@dataclass(frozen=True, slots=True)
class QueryScore:
    query_id: str
    worst_outcome_ambiguity: int
    ambiguous_observation_count: int
    worst_remaining_worlds: int
    expected_remaining_worlds: Fraction

    @property
    def objective(self) -> tuple[int, int, int, Fraction]:
        """Lexicographic minimax objective, prioritizing decision sufficiency."""

        return (
            self.worst_outcome_ambiguity,
            self.ambiguous_observation_count,
            self.worst_remaining_worlds,
            self.expected_remaining_worlds,
        )


def score_queries(
    worlds: Sequence[DiagnosticWorld],
    query_ids: Iterable[str],
) -> dict[str, QueryScore]:
    """Score queries by remaining outcome ambiguity, then residual version-space size."""

    normalized_worlds = tuple(worlds)
    if not normalized_worlds:
        raise ValueError("at least one diagnostic world is required")
    world_ids = [world.world_id for world in normalized_worlds]
    if len(world_ids) != len(set(world_ids)):
        raise ValueError("diagnostic world ids must be unique")

    normalized_queries = tuple(query_ids)
    if not normalized_queries:
        raise ValueError("at least one query is required")
    if len(normalized_queries) != len(set(normalized_queries)):
        raise ValueError("query ids must be unique")

    scores: dict[str, QueryScore] = {}
    for query_id in normalized_queries:
        buckets: dict[str, list[DiagnosticWorld]] = defaultdict(list)
        for world in normalized_worlds:
            buckets[world.observation_for(query_id)].append(world)
        outcome_counts = [len({world.outcome for world in bucket}) for bucket in buckets.values()]
        bucket_sizes = [len(bucket) for bucket in buckets.values()]
        expected_remaining = Fraction(
            sum(bucket_size * bucket_size for bucket_size in bucket_sizes),
            len(normalized_worlds),
        )
        scores[query_id] = QueryScore(
            query_id=query_id,
            worst_outcome_ambiguity=max(outcome_counts),
            ambiguous_observation_count=sum(count > 1 for count in outcome_counts),
            worst_remaining_worlds=max(bucket_sizes),
            expected_remaining_worlds=expected_remaining,
        )
    return scores


def best_queries(
    worlds: Sequence[DiagnosticWorld],
    query_ids: Iterable[str],
) -> list[QueryScore]:
    scores = score_queries(worlds, query_ids)
    best_objective = min(score.objective for score in scores.values())
    return [
        scores[query_id]
        for query_id in sorted(scores)
        if scores[query_id].objective == best_objective
    ]


def decisive_branches(
    worlds: Sequence[DiagnosticWorld],
    query_id: str,
) -> dict[str, str]:
    """Return observation-to-outcome branches, rejecting a non-decisive query."""

    branches: dict[str, set[str]] = defaultdict(set)
    for world in worlds:
        branches[world.observation_for(query_id)].add(world.outcome)
    ambiguous = {
        observation: outcomes for observation, outcomes in branches.items() if len(outcomes) != 1
    }
    if ambiguous:
        raise ValueError(f"query {query_id!r} leaves ambiguous branches: {ambiguous}")
    return {observation: next(iter(outcomes)) for observation, outcomes in sorted(branches.items())}


def encode_active_answer(
    query_id: str,
    branches: Mapping[str, str],
    *,
    observation_order: Sequence[str] | None = None,
) -> str:
    order = tuple(observation_order) if observation_order is not None else tuple(sorted(branches))
    if set(order) != set(branches) or len(order) != len(branches):
        raise ValueError("observation order must contain every branch exactly once")
    parts = [f"QUERY={query_id}"]
    parts.extend(f"IF_{observation}={branches[observation]}" for observation in order)
    return ";".join(parts)


@dataclass(frozen=True, slots=True)
class AdaptiveBranch:
    root_observation: str
    second_query: str | None
    outcomes: tuple[tuple[str, str], ...]

    @property
    def is_terminal(self) -> bool:
        return self.second_query is None


@dataclass(frozen=True, slots=True)
class AdaptivePolicy:
    root_query: str
    branches: tuple[AdaptiveBranch, ...]
    worst_total_cost: int
    expected_total_cost: Fraction
    worst_remaining_worlds: int
    expected_remaining_worlds: Fraction

    @property
    def objective(self) -> tuple[int, Fraction, int, Fraction]:
        return (
            self.worst_total_cost,
            self.expected_total_cost,
            self.worst_remaining_worlds,
            self.expected_remaining_worlds,
        )


@dataclass(frozen=True, slots=True)
class _BranchChoice:
    query_id: str | None
    outcomes: tuple[tuple[str, str], ...]
    cost: int
    leaves: tuple[int, ...]


def best_two_stage_policies(
    worlds: Sequence[DiagnosticWorld],
    query_ids: Iterable[str],
    query_costs: Mapping[str, int],
) -> list[AdaptivePolicy]:
    """Find all minimum-cost depth-two policies whose leaves determine the outcome."""

    normalized_worlds = tuple(worlds)
    normalized_queries = tuple(query_ids)
    _validate_policy_inputs(normalized_worlds, normalized_queries, query_costs)
    policies: list[AdaptivePolicy] = []
    for root_query in normalized_queries:
        root_buckets = _partition(normalized_worlds, root_query)
        choices_by_observation: list[tuple[str, list[_BranchChoice]]] = []
        feasible = True
        for observation, bucket in sorted(root_buckets.items()):
            choices = _decisive_branch_choices(
                bucket,
                query_ids=(query for query in normalized_queries if query != root_query),
                query_costs=query_costs,
            )
            if not choices:
                feasible = False
                break
            best_objective = min(
                (choice.cost, max(choice.leaves), sum(size * size for size in choice.leaves))
                for choice in choices
            )
            best_choices = [
                choice
                for choice in choices
                if (
                    choice.cost,
                    max(choice.leaves),
                    sum(size * size for size in choice.leaves),
                )
                == best_objective
            ]
            choices_by_observation.append((observation, best_choices))
        if not feasible:
            continue

        for branch_combination in product(
            *(choices for _observation, choices in choices_by_observation)
        ):
            branches = tuple(
                AdaptiveBranch(observation, choice.query_id, choice.outcomes)
                for (observation, _choices), choice in zip(
                    choices_by_observation, branch_combination, strict=True
                )
            )
            branch_sizes = [len(root_buckets[branch.root_observation]) for branch in branches]
            path_costs = [query_costs[root_query] + choice.cost for choice in branch_combination]
            leaves = [size for choice in branch_combination for size in choice.leaves]
            policies.append(
                AdaptivePolicy(
                    root_query=root_query,
                    branches=branches,
                    worst_total_cost=max(path_costs),
                    expected_total_cost=Fraction(
                        sum(
                            size * cost for size, cost in zip(branch_sizes, path_costs, strict=True)
                        ),
                        len(normalized_worlds),
                    ),
                    worst_remaining_worlds=max(leaves),
                    expected_remaining_worlds=Fraction(
                        sum(size * size for size in leaves),
                        len(normalized_worlds),
                    ),
                )
            )
    if not policies:
        return []
    best_objective = min(policy.objective for policy in policies)
    return sorted(
        (policy for policy in policies if policy.objective == best_objective),
        key=_policy_sort_key,
    )


def encode_two_stage_policy(
    policy: AdaptivePolicy,
    *,
    root_observation_order: Sequence[str],
    second_observation_order: Sequence[str],
) -> str:
    branches = {branch.root_observation: branch for branch in policy.branches}
    if set(branches) != set(root_observation_order):
        raise ValueError("root observation order must contain every policy branch exactly once")
    parts = [f"ROOT={policy.root_query}"]
    for root_observation in root_observation_order:
        branch = branches[root_observation]
        if branch.is_terminal:
            parts.append(f"ON_{root_observation}={branch.outcomes[0][1]}")
            continue
        assert branch.second_query is not None
        parts.append(f"ON_{root_observation}={branch.second_query}")
        outcomes = dict(branch.outcomes)
        if set(outcomes) != set(second_observation_order):
            raise ValueError(f"second observation order does not match branch {root_observation!r}")
        parts.extend(
            f"ON_{root_observation}_{observation}={outcomes[observation]}"
            for observation in second_observation_order
        )
    return ";".join(parts)


def _validate_policy_inputs(
    worlds: tuple[DiagnosticWorld, ...],
    query_ids: tuple[str, ...],
    query_costs: Mapping[str, int],
) -> None:
    if not worlds:
        raise ValueError("at least one diagnostic world is required")
    if len({world.world_id for world in worlds}) != len(worlds):
        raise ValueError("diagnostic world ids must be unique")
    if not query_ids or len(set(query_ids)) != len(query_ids):
        raise ValueError("query ids must be nonempty and unique")
    if set(query_costs) != set(query_ids):
        raise ValueError("query costs must cover exactly the available queries")
    if any(
        isinstance(cost, bool) or not isinstance(cost, int) or cost <= 0
        for cost in query_costs.values()
    ):
        raise ValueError("query costs must be positive integers")
    for world in worlds:
        for query_id in query_ids:
            world.observation_for(query_id)


def _partition(
    worlds: Sequence[DiagnosticWorld],
    query_id: str,
) -> dict[str, tuple[DiagnosticWorld, ...]]:
    buckets: dict[str, list[DiagnosticWorld]] = defaultdict(list)
    for world in worlds:
        buckets[world.observation_for(query_id)].append(world)
    return {observation: tuple(bucket) for observation, bucket in buckets.items()}


def _decisive_branch_choices(
    worlds: tuple[DiagnosticWorld, ...],
    *,
    query_ids: Iterable[str],
    query_costs: Mapping[str, int],
) -> list[_BranchChoice]:
    outcomes = {world.outcome for world in worlds}
    if len(outcomes) == 1:
        return [_BranchChoice(None, (("STOP", next(iter(outcomes))),), 0, (len(worlds),))]

    choices: list[_BranchChoice] = []
    for query_id in query_ids:
        buckets = _partition(worlds, query_id)
        if any(len({world.outcome for world in bucket}) != 1 for bucket in buckets.values()):
            continue
        choices.append(
            _BranchChoice(
                query_id=query_id,
                outcomes=tuple(
                    (observation, bucket[0].outcome)
                    for observation, bucket in sorted(buckets.items())
                ),
                cost=query_costs[query_id],
                leaves=tuple(len(bucket) for bucket in buckets.values()),
            )
        )
    return choices


def _policy_sort_key(policy: AdaptivePolicy) -> tuple[object, ...]:
    return (
        policy.root_query,
        tuple(
            (
                branch.root_observation,
                branch.second_query or "",
                branch.outcomes,
            )
            for branch in policy.branches
        ),
    )
