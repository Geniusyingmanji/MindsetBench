from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum


class Decision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class PriorityRule:
    """A defeasible rule whose larger priority value defeats smaller ones."""

    name: str
    conditions: frozenset[str]
    decision: Decision
    priority: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("rule name must not be empty")
        if not self.conditions:
            raise ValueError(f"rule {self.name!r} must have at least one condition")


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    decision: Decision
    winning_priority: int | None
    winning_rules: tuple[str, ...]


def decide(
    facts: Iterable[str],
    rules: Iterable[PriorityRule],
    *,
    default: Decision = Decision.DENY,
) -> PolicyDecision:
    """Evaluate a finite priority policy and reject unresolved top-priority conflicts."""

    fact_set = frozenset(facts)
    applicable = tuple(rule for rule in rules if rule.conditions <= fact_set)
    if not applicable:
        return PolicyDecision(default, None, ())

    winning_priority = max(rule.priority for rule in applicable)
    winners = tuple(rule for rule in applicable if rule.priority == winning_priority)
    decisions = {rule.decision for rule in winners}
    if len(decisions) != 1:
        names = ", ".join(sorted(rule.name for rule in winners))
        raise ValueError(f"conflicting decisions at priority {winning_priority}: {names}")
    return PolicyDecision(
        decision=next(iter(decisions)),
        winning_priority=winning_priority,
        winning_rules=tuple(sorted(rule.name for rule in winners)),
    )


def evaluate_policy(
    records: Mapping[str, Iterable[str]],
    rules: Iterable[PriorityRule],
    *,
    default: Decision = Decision.DENY,
) -> dict[str, PolicyDecision]:
    """Evaluate records in input order with a materialized, reusable rule set."""

    normalized_rules = tuple(rules)
    return {
        record_id: decide(facts, normalized_rules, default=default)
        for record_id, facts in records.items()
    }


def denied_record_ids(
    records: Mapping[str, Iterable[str]],
    rules: Iterable[PriorityRule],
    *,
    default: Decision = Decision.DENY,
) -> list[str]:
    decisions = evaluate_policy(records, rules, default=default)
    return [
        record_id for record_id, result in decisions.items() if result.decision == Decision.DENY
    ]
