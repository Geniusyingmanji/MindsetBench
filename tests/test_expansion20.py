from collections import Counter

from mindsetbench.data import (
    PROJECT_ROOT,
    load_cases,
    load_schema_cards,
    validate_dataset,
    validate_schema_cards,
)
from mindsetbench.verification import verify_case

DATASET = PROJECT_ROOT / "data" / "v1" / "expansion20.yaml"


def test_expansion20_is_balanced_and_strict_v1() -> None:
    cases = load_cases(DATASET)
    report = validate_dataset(cases, strict_v1=True)
    assert report.ok, report.issues
    assert len(cases) == 20
    assert Counter(case.level for case in cases) == {0: 4, 1: 4, 2: 4, 3: 4, 4: 4}
    assert Counter(case.paradigm.value for case in cases) == {
        "P2": 5,
        "P3": 5,
        "P4": 5,
        "P6": 5,
    }


def test_expansion20_fixed_sources_do_not_drift() -> None:
    cases = load_cases(DATASET)
    chains = {case.chain for case in cases}
    for chain in chains:
        sources = {case.source.model_dump_json() for case in cases if case.chain == chain}
        assert len(sources) == 1


def test_expansion20_executable_verifiers_pass() -> None:
    cases = load_cases(DATASET)
    results = [verify_case(case) for case in cases]
    assert all(result.passed for result in results), [
        result for result in results if not result.passed
    ]


def test_expansion20_has_machine_checkable_lures_and_copy_probes() -> None:
    cases = load_cases(DATASET)
    for case in cases:
        if case.level >= 2:
            assert case.lure is not None
            assert case.lure.answer is not None
            assert case.lure.solution
        if case.level >= 3:
            assert case.copy_probe is not None
            assert case.copy_probe.answer != case.target.answer


def test_expansion20_matches_schema_cards() -> None:
    cases = load_cases(DATASET)
    cards = load_schema_cards(PROJECT_ROOT / "data" / "schema_cards" / "pilot-v1.yaml")
    report = validate_schema_cards(cards, cases)
    assert report.ok, report.issues
