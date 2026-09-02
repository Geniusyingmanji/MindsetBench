import pytest

from mindsetbench.data import (
    PROJECT_ROOT,
    load_cases,
    load_schema_cards,
    validate_dataset,
    validate_schema_cards,
    validate_transfer_design,
)
from mindsetbench.verification import verify_case
from mindsetbench.verification.norm_priority import (
    Decision,
    PriorityRule,
    decide,
    denied_record_ids,
)

DATASET = PROJECT_ROOT / "data" / "v1" / "hss-p4-norm-precedent-chain.yaml"
CARDS = PROJECT_ROOT / "data" / "schema_cards" / "hss-p4-norm-precedent-v1.yaml"
MANIFEST = PROJECT_ROOT / "data" / "manifests" / "hss5.json"


def _rule(
    name: str,
    conditions: set[str],
    decision: Decision,
    priority: int,
) -> PriorityRule:
    return PriorityRule(name, frozenset(conditions), decision, priority)


def test_hss_p4_chain_is_complete_strict_audited_and_verified() -> None:
    cases = load_cases(DATASET)
    strict = validate_dataset(cases, strict_v1=True)
    audit = validate_transfer_design(cases, require_complete_chains=True)
    assert strict.ok, strict.issues
    assert audit.ok, audit.issues
    assert len(cases) == 5
    assert [case.level for case in cases] == list(range(5))
    assert {case.chain for case in cases} == {"hss-p4-norm-precedent-v1"}

    results = [verify_case(case) for case in cases]
    assert all(result.passed for result in results), results


def test_hss_p4_schema_card_and_manifest_match_chain() -> None:
    direct = load_cases(DATASET)
    manifest = load_cases(MANIFEST)
    cards = load_schema_cards(CARDS)
    report = validate_schema_cards(cards, direct)
    assert report.ok, report.issues
    assert [case.id for case in manifest] == [case.id for case in direct]


def test_hss_p4_chain_has_deterministic_negative_controls() -> None:
    for case in load_cases(DATASET):
        assert case.lure is not None and case.lure.answer is not None
        assert case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer


def test_priority_engine_uses_default_and_highest_applicable_rule() -> None:
    rules = (
        _rule("permit", {"eligible"}, Decision.ALLOW, 1),
        _rule("bar", {"risk"}, Decision.DENY, 2),
        _rule("exception", {"review", "consent"}, Decision.ALLOW, 3),
    )
    records = {
        "A": frozenset(),
        "B": frozenset({"eligible", "risk"}),
        "C": frozenset({"eligible", "risk", "review", "consent"}),
    }
    assert denied_record_ids(records, rules) == ["A", "B"]
    decision = decide(records["C"], rules)
    assert decision.decision == Decision.ALLOW
    assert decision.winning_priority == 3
    assert decision.winning_rules == ("exception",)


def test_priority_engine_rejects_ambiguous_top_priority() -> None:
    rules = (
        _rule("permit", {"same"}, Decision.ALLOW, 7),
        _rule("deny", {"same"}, Decision.DENY, 7),
    )
    with pytest.raises(ValueError, match="conflicting decisions at priority 7"):
        decide({"same"}, rules)


@pytest.mark.parametrize("name", ["", "   "])
def test_priority_engine_rejects_blank_rule_names(name: str) -> None:
    with pytest.raises(ValueError, match="rule name must not be empty"):
        _rule(name, {"fact"}, Decision.ALLOW, 1)


def test_priority_engine_rejects_rules_without_conditions() -> None:
    with pytest.raises(ValueError, match="must have at least one condition"):
        _rule("empty", set(), Decision.ALLOW, 1)
