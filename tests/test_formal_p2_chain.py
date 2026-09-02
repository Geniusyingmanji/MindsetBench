from mindsetbench.data import (
    PROJECT_ROOT,
    load_cases,
    load_schema_cards,
    validate_dataset,
    validate_schema_cards,
)
from mindsetbench.verification import verify_case

DATASET = PROJECT_ROOT / "data" / "v1" / "formal-p2-sensitivity-chain.yaml"
CARDS = PROJECT_ROOT / "data" / "schema_cards" / "formal-p2-sensitivity-v1.yaml"


def test_formal_p2_chain_is_complete_strict_and_verified() -> None:
    cases = load_cases(DATASET)
    report = validate_dataset(cases, strict_v1=True)
    assert report.ok, report.issues
    assert len(cases) == 5
    assert [case.level for case in cases] == list(range(5))
    assert {case.chain for case in cases} == {"p2-sensitivity-v1"}
    results = [verify_case(case) for case in cases]
    assert all(result.passed for result in results), results


def test_formal_p2_schema_card_matches_complete_chain() -> None:
    cases = load_cases(DATASET)
    cards = load_schema_cards(CARDS)
    report = validate_schema_cards(cards, cases)
    assert report.ok, report.issues


def test_formal_p2_chain_has_deterministic_negative_controls() -> None:
    for case in load_cases(DATASET):
        assert case.lure is not None and case.lure.answer is not None
        assert case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer
