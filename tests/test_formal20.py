import pytest

from mindsetbench.data import (
    PROJECT_ROOT,
    load_cases,
    load_schema_cards,
    validate_dataset,
    validate_schema_cards,
    validate_transfer_design,
)
from mindsetbench.models.case import Paradigm, Split
from mindsetbench.verification import verify_case

CHAINS = {
    Paradigm.P2: (
        PROJECT_ROOT / "data" / "v1" / "formal-p2-sensitivity-chain.yaml",
        PROJECT_ROOT / "data" / "schema_cards" / "formal-p2-sensitivity-v1.yaml",
    ),
    Paradigm.P3: (
        PROJECT_ROOT / "data" / "v1" / "formal-p3-causal-chain.yaml",
        PROJECT_ROOT / "data" / "schema_cards" / "formal-p3-causal-v1.yaml",
    ),
    Paradigm.P4: (
        PROJECT_ROOT / "data" / "v1" / "formal-p4-closure-chain.yaml",
        PROJECT_ROOT / "data" / "schema_cards" / "formal-p4-closure-v1.yaml",
    ),
    Paradigm.P6: (
        PROJECT_ROOT / "data" / "v1" / "formal-p6-alignment-chain.yaml",
        PROJECT_ROOT / "data" / "schema_cards" / "formal-p6-alignment-v1.yaml",
    ),
}


def test_formal20_has_four_disjoint_complete_chains() -> None:
    cases = [case for dataset, _cards in CHAINS.values() for case in load_cases(dataset)]
    assert len(cases) == 20
    assert len({case.id for case in cases}) == 20
    assert {case.paradigm for case in cases} == set(CHAINS)
    assert {case.split for case in cases} == {Split.SANITY}
    for paradigm in CHAINS:
        members = [case for case in cases if case.paradigm == paradigm]
        assert sorted(case.level for case in members) == list(range(5))
        assert len({case.chain for case in members}) == 1


def test_formal20_cards_and_verifiers_cover_every_case() -> None:
    for dataset, cards_path in CHAINS.values():
        cases = load_cases(dataset)
        report = validate_schema_cards(load_schema_cards(cards_path), cases)
        assert report.ok, report.issues
        assert all(verify_case(case).passed for case in cases)


def test_formal20_bundles_support_full_runs_and_high_level_prescreen() -> None:
    full = load_cases(PROJECT_ROOT / "data" / "manifests" / "formal20.json")
    new = load_cases(PROJECT_ROOT / "data" / "manifests" / "formal-new15.json")
    high = load_cases(PROJECT_ROOT / "data" / "manifests" / "formal-new-high.json")
    cards = load_schema_cards(PROJECT_ROOT / "data" / "manifests" / "formal20-cards.json")
    assert len(full) == 20
    assert len(new) == 15
    assert len(high) == 8
    assert {case.level for case in high} == {3, 4}
    assert {case.paradigm for case in high} == {
        Paradigm.P3,
        Paradigm.P4,
        Paradigm.P5,
        Paradigm.P6,
    }
    assert validate_dataset(full, strict_v1=True).ok
    assert validate_schema_cards(cards, full).ok
    assert validate_transfer_design(full, require_complete_chains=True).ok


def test_transfer_design_audit_detects_shallow_advanced_mapping() -> None:
    case = load_cases(PROJECT_ROOT / "data" / "v1" / "formal-p3-causal-chain.yaml")[3]
    shallow = case.model_copy(deep=True)
    shallow.mapping.shared_relations = shallow.mapping.shared_relations[:3]
    report = validate_transfer_design([shallow])
    assert any(issue.code == "design-shallow-relation-map" for issue in report.errors)


def test_transfer_design_audit_detects_target_method_label_leak() -> None:
    case = load_cases(PROJECT_ROOT / "data" / "v1" / "formal-p4-closure-chain.yaml")[3]
    leaked = case.model_copy(deep=True)
    leaked.target.problem += " 这是最小不动点问题。"
    report = validate_transfer_design([leaked])
    assert any(issue.code == "design-method-label-leak" for issue in report.errors)


@pytest.mark.parametrize(
    ("dataset", "level", "original", "mutated"),
    [
        ("formal-p3-causal-chain.yaml", 4, "V→Q:9", "V→Q:8"),
        ("formal-p4-closure-chain.yaml", 4, "Q12(197)", "Q12(198)"),
        ("formal-p6-alignment-chain.yaml", 4, "D6-○-D4", "D6-○-D5"),
    ],
)
def test_advanced_verifiers_reject_target_text_table_drift(
    dataset: str,
    level: int,
    original: str,
    mutated: str,
) -> None:
    case = next(
        case for case in load_cases(PROJECT_ROOT / "data" / "v1" / dataset) if case.level == level
    ).model_copy(deep=True)
    assert original in case.target.problem
    case.target.problem = case.target.problem.replace(original, mutated, 1)
    result = verify_case(case)
    assert not result.passed
    assert any(
        not check.passed and check.name.startswith("target-text-") for check in result.checks
    )
