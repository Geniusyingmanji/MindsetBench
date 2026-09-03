import pytest

from mindsetbench.verification.active_query import (
    DiagnosticWorld,
    best_queries,
    best_two_stage_policies,
    decisive_branches,
    encode_active_answer,
    encode_two_stage_policy,
    score_queries,
)


def _world(world_id: str, outcome: str, q1: str, q2: str) -> DiagnosticWorld:
    return DiagnosticWorld(world_id, outcome, (("Q1", q1), ("Q2", q2)))


def _adaptive_world(
    world_id: str,
    outcome: str,
    **observations: str,
) -> DiagnosticWorld:
    return DiagnosticWorld(world_id, outcome, tuple(sorted(observations.items())))


def test_active_query_prefers_decision_sufficiency_over_world_identification() -> None:
    worlds = (
        _world("W1", "ALLOW", "A", "X"),
        _world("W2", "ALLOW", "B", "X"),
        _world("W3", "DENY", "A", "Y"),
        _world("W4", "DENY", "B", "Y"),
    )
    scores = score_queries(worlds, ("Q1", "Q2"))
    assert scores["Q1"].worst_outcome_ambiguity == 2
    assert scores["Q2"].worst_outcome_ambiguity == 1
    assert [score.query_id for score in best_queries(worlds, ("Q1", "Q2"))] == ["Q2"]
    assert decisive_branches(worlds, "Q2") == {"X": "ALLOW", "Y": "DENY"}
    assert encode_active_answer("Q2", {"X": "ALLOW", "Y": "DENY"}) == (
        "QUERY=Q2;IF_X=ALLOW;IF_Y=DENY"
    )


def test_active_query_rejects_invalid_or_ambiguous_inputs() -> None:
    with pytest.raises(ValueError, match="repeats a query"):
        DiagnosticWorld("W", "A", (("Q", "X"), ("Q", "Y")))

    worlds = (
        _world("W1", "ALLOW", "A", "X"),
        _world("W2", "DENY", "A", "Y"),
    )
    with pytest.raises(ValueError, match="ambiguous branches"):
        decisive_branches(worlds, "Q1")
    with pytest.raises(ValueError, match="observation order"):
        encode_active_answer("Q2", {"X": "ALLOW", "Y": "DENY"}, observation_order=("X",))


def test_two_stage_policy_can_adapt_the_second_query() -> None:
    worlds = (
        _adaptive_world("W1", "A", Q1="RED", Q2="RED", Q3="RED"),
        _adaptive_world("W2", "B", Q1="RED", Q2="BLUE", Q3="RED"),
        _adaptive_world("W3", "A", Q1="BLUE", Q2="RED", Q3="RED"),
        _adaptive_world("W4", "B", Q1="BLUE", Q2="RED", Q3="BLUE"),
    )
    policies = best_two_stage_policies(
        worlds,
        ("Q1", "Q2", "Q3"),
        {"Q1": 1, "Q2": 2, "Q3": 3},
    )
    assert len(policies) == 1
    assert encode_two_stage_policy(
        policies[0],
        root_observation_order=("RED", "BLUE"),
        second_observation_order=("RED", "BLUE"),
    ) == ("ROOT=Q1;ON_RED=Q2;ON_RED_RED=A;ON_RED_BLUE=B;ON_BLUE=Q3;ON_BLUE_RED=A;ON_BLUE_BLUE=B")


def test_two_stage_policy_validates_query_costs() -> None:
    worlds = (
        _adaptive_world("W1", "A", Q1="RED"),
        _adaptive_world("W2", "B", Q1="BLUE"),
    )
    with pytest.raises(ValueError, match="cover exactly"):
        best_two_stage_policies(worlds, ("Q1",), {})
    with pytest.raises(ValueError, match="positive integers"):
        best_two_stage_policies(worlds, ("Q1",), {"Q1": 0})
