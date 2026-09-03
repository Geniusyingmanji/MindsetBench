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
from mindsetbench.verification.role_mapping import (
    RelationalGraph,
    best_mappings,
    evaluate_mapping,
)

DATASET = PROJECT_ROOT / "data" / "v1" / "hss-p6-historical-analogy-chain.yaml"
CARDS = PROJECT_ROOT / "data" / "schema_cards" / "hss-p6-historical-analogy-v1.yaml"
MANIFEST = PROJECT_ROOT / "data" / "manifests" / "hss15.json"


def test_hss_p6_chain_is_complete_strict_audited_and_verified() -> None:
    cases = load_cases(DATASET)
    strict = validate_dataset(cases, strict_v1=True)
    audit = validate_transfer_design(cases, require_complete_chains=True)
    assert strict.ok, strict.issues
    assert audit.ok, audit.issues
    assert len(cases) == 5
    assert [case.level for case in cases] == list(range(5))
    assert {case.chain for case in cases} == {"hss-p6-historical-analogy-v1"}

    results = [verify_case(case) for case in cases]
    assert all(result.passed for result in results), results


def test_hss_p6_schema_card_and_hss15_manifest_match() -> None:
    direct = load_cases(DATASET)
    cards = load_schema_cards(CARDS)
    report = validate_schema_cards(cards, direct)
    assert report.ok, report.issues

    manifest = load_cases(MANIFEST)
    assert len(manifest) == 15
    assert {case.paradigm.value for case in manifest} == {"P4", "P6", "P7"}
    assert [case.level for case in manifest].count(4) == 3


def test_hss_p6_chain_has_deterministic_negative_controls() -> None:
    for case in load_cases(DATASET):
        assert case.lure is not None and case.lure.answer is not None
        assert case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer


def test_role_matcher_finds_unique_renamed_mapping() -> None:
    source = RelationalGraph(
        frozenset({"O", "G", "P"}),
        frozenset({("O", "informs", "G"), ("G", "restrains", "P")}),
    )
    target = RelationalGraph(
        frozenset({"A", "B", "C", "noise"}),
        frozenset(
            {
                ("C", "warns", "A"),
                ("A", "blocks", "B"),
                ("noise", "observes", "B"),
            }
        ),
    )
    matches = best_mappings(
        source,
        target,
        ("O", "G", "P"),
        {"informs": "warns", "restrains": "blocks"},
    )
    assert len(matches) == 1
    assert matches[0].mapping == {"O": "C", "G": "A", "P": "B"}
    assert matches[0].score == 2


def test_role_matcher_reports_missing_and_added_induced_edges() -> None:
    source = RelationalGraph(
        frozenset({"G", "P"}),
        frozenset({("G", "restrains", "P")}),
    )
    target = RelationalGraph(
        frozenset({"A", "B"}),
        frozenset({("B", "controls", "A")}),
    )
    match = evaluate_mapping(
        source,
        target,
        {"G": "A", "P": "B"},
        {"restrains": "restrains"},
    )
    assert match.score == 0
    assert match.missing_edges == {("A", "restrains", "B")}
    assert match.added_induced_edges == {("B", "controls", "A")}


def test_role_matcher_rejects_invalid_graphs_and_mappings() -> None:
    with pytest.raises(ValueError, match="unknown nodes"):
        RelationalGraph(frozenset({"A"}), frozenset({("A", "r", "B")}))

    source = RelationalGraph(
        frozenset({"A", "B"}),
        frozenset({("A", "r", "B")}),
    )
    target = RelationalGraph(
        frozenset({"X", "Y"}),
        frozenset({("X", "r", "Y")}),
    )
    with pytest.raises(ValueError, match="injective"):
        evaluate_mapping(source, target, {"A": "X", "B": "X"}, {"r": "r"})
    with pytest.raises(ValueError, match="incomplete"):
        evaluate_mapping(source, target, {"A": "X", "B": "Y"}, {})
