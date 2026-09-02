from mindsetbench.data import (
    PROJECT_ROOT,
    load_cases,
    load_schema_cards,
    validate_dataset,
    validate_schema_cards,
)
from mindsetbench.verification import verify_case

DATASET = PROJECT_ROOT / "data" / "v1" / "formal-p5-planning-chain.yaml"
CARDS = PROJECT_ROOT / "data" / "schema_cards" / "formal-p5-planning-v1.yaml"


def test_formal_p5_chain_is_complete_strict_and_verified() -> None:
    cases = load_cases(DATASET)
    report = validate_dataset(cases, strict_v1=True)
    assert report.ok, report.issues
    assert len(cases) == 5
    assert [case.level for case in cases] == list(range(5))
    assert {case.chain for case in cases} == {"p5-stateful-planning-edit-v1"}
    results = [verify_case(case) for case in cases]
    assert all(result.passed for result in results), results


def test_formal_p5_schema_card_matches_complete_chain() -> None:
    cases = load_cases(DATASET)
    cards = load_schema_cards(CARDS)
    report = validate_schema_cards(cards, cases)
    assert report.ok, report.issues


def test_formal_p5_chain_has_deterministic_negative_controls() -> None:
    for case in load_cases(DATASET):
        assert case.lure is not None and case.lure.answer is not None
        assert case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer


def test_formal_p5_verifier_rejects_action_table_drift() -> None:
    case = load_cases(DATASET)[4].model_copy(deep=True)
    assert (
        "K3（费用1）只有 y 都已登记且 无 均未登记时可用；用后登记 p，并注销 无"
        in case.target.problem
    )
    case.target.problem = case.target.problem.replace(
        "K3（费用1）只有 y 都已登记且 无 均未登记时可用；用后登记 p，并注销 无",
        "K3（费用1）只有 y 都已登记且 无 均未登记时可用；用后登记 v，并注销 无",
        1,
    )
    result = verify_case(case)
    assert not result.passed
    assert any(not check.passed and check.name == "target-text-instance" for check in result.checks)
