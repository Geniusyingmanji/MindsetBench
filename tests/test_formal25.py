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


def test_formal25_bundle_has_five_complete_chains() -> None:
    cases = load_cases(PROJECT_ROOT / "data" / "manifests" / "formal25.json")
    assert len(cases) == 25
    assert len({case.id for case in cases}) == 25
    assert {case.paradigm for case in cases} == {
        Paradigm.P2,
        Paradigm.P3,
        Paradigm.P4,
        Paradigm.P5,
        Paradigm.P6,
    }
    assert {case.split for case in cases} == {Split.SANITY}
    for paradigm in {case.paradigm for case in cases}:
        members = [case for case in cases if case.paradigm == paradigm]
        assert sorted(case.level for case in members) == list(range(5))
        assert len({case.chain for case in members}) == 1


def test_formal25_bundle_passes_all_construction_gates() -> None:
    cases = load_cases(PROJECT_ROOT / "data" / "manifests" / "formal25.json")
    cards = load_schema_cards(PROJECT_ROOT / "data" / "manifests" / "formal25-cards.json")
    assert validate_dataset(cases, strict_v1=True).ok
    assert validate_schema_cards(cards, cases).ok
    assert validate_transfer_design(cases, require_complete_chains=True).ok
    assert all(verify_case(case).passed for case in cases)


def test_formal_new20_and_high_prescreen_have_expected_coverage() -> None:
    new = load_cases(PROJECT_ROOT / "data" / "manifests" / "formal-new20.json")
    high = load_cases(PROJECT_ROOT / "data" / "manifests" / "formal-new-high.json")
    p5_high = load_cases(PROJECT_ROOT / "data" / "manifests" / "formal-p5-high.json")
    assert len(new) == 20
    assert len(high) == 8
    expected = {Paradigm.P3, Paradigm.P4, Paradigm.P5, Paradigm.P6}
    assert {case.paradigm for case in new} == expected
    assert {case.paradigm for case in high} == expected
    assert {case.level for case in high} == {3, 4}
    assert [case.id for case in p5_high] == [
        "FORMAL-P5-PLAN-L3-01",
        "FORMAL-P5-PLAN-L4-01",
    ]
    assert validate_dataset(high, strict_v1=True).ok
