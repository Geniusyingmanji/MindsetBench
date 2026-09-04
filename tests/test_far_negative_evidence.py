from mindsetbench.data import (
    PROJECT_ROOT,
    audit_surface,
    load_cases,
    load_schema_cards,
    validate_dataset,
    validate_schema_cards,
    validate_transfer_design,
)
from mindsetbench.models.case import Split
from mindsetbench.verification import verify_case
from mindsetbench.verification.far_negative_evidence import (
    L3_EVENTS,
    SOURCE_WORLD,
    dating_interval,
    feasible,
    route_answer,
    simple_paths,
)

DATASET = PROJECT_ROOT / "data" / "v1" / "far-negative-evidence-chain.yaml"
CARDS = PROJECT_ROOT / "data" / "schema_cards" / "far-negative-evidence-v1.yaml"


def test_far_neg_chain_is_strict_audited_surface_clean_and_verified() -> None:
    cases = load_cases(DATASET)
    assert len(cases) == 5
    assert [case.level for case in cases] == list(range(5))
    assert {case.level: case.split for case in cases} == {
        0: Split.CALIBRATION,
        1: Split.CALIBRATION,
        2: Split.SANITY,
        3: Split.SANITY,
        4: Split.SANITY,
    }
    assert validate_dataset(cases, strict_v1=True).ok
    audit = validate_transfer_design(cases, require_complete_chains=True)
    assert audit.ok, audit.issues
    surface = audit_surface(cases)
    assert surface.ok, surface.errors
    results = [verify_case(case) for case in cases]
    assert all(result.passed for result in results), [
        (result.case_id, [check for check in result.checks if not check.passed])
        for result in results
    ]


def test_far_neg_schema_card_matches_chain() -> None:
    report = validate_schema_cards(load_schema_cards(CARDS), load_cases(DATASET))
    assert report.ok, report.issues


def test_far_neg_negative_controls_are_deterministic_and_distinct() -> None:
    for case in load_cases(DATASET):
        assert case.lure is not None and case.lure.answer is not None
        assert case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer


def test_source_world_needs_the_negative_sample() -> None:
    assert SOURCE_WORLD.gold() == "S2"
    assert SOURCE_WORLD.decoy() == "S3"


def test_dating_interval_distinguishes_informative_silence() -> None:
    assert dating_interval(L3_EVENTS, informative_silence_only=True) == (1466, 1470)
    assert dating_interval(L3_EVENTS, informative_silence_only=False) == (1466, 1467)


def test_route_reconstruction_uses_timing_and_silence() -> None:
    assert route_answer(use_silence=True, shortest=False) == "A>C>F"
    assert route_answer(use_silence=False, shortest=True) == "A>C>D>F"
    assert not feasible(("A", "C", "E", "F"), use_silence=False), "arrives at F after 08:00"
    assert ("A", "B", "F") in simple_paths("A", "F")
    assert not feasible(("A", "B", "F"), use_silence=True)


def test_verifier_rejects_tampered_route() -> None:
    case = next(case for case in load_cases(DATASET) if case.id == "FAR-NEG-L4-01")
    tampered = case.model_copy(deep=True)
    tampered.target.answer.parts[0].value = "ROUTE=A>C>D>F"
    failed = {check.name for check in verify_case(tampered).checks if not check.passed}
    assert "stored-target-answer" in failed
