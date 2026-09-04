from fractions import Fraction

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
from mindsetbench.verification.far_horizon_exploration import (
    L3_WORLD,
    L4_WORLD,
    SOURCE_WORLD,
    SubmissionWorld,
    TrialWorld,
)

DATASET = PROJECT_ROOT / "data" / "v1" / "far-horizon-exploration-chain.yaml"
CARDS = PROJECT_ROOT / "data" / "schema_cards" / "far-horizon-exploration-v1.yaml"


def test_far_horizon_chain_is_strict_audited_surface_clean_and_verified() -> None:
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


def test_far_horizon_schema_card_matches_chain() -> None:
    report = validate_schema_cards(load_schema_cards(CARDS), load_cases(DATASET))
    assert report.ok, report.issues


def test_far_horizon_negative_controls_are_deterministic_and_distinct() -> None:
    for case in load_cases(DATASET):
        assert case.lure is not None and case.lure.answer is not None
        assert case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer


def test_source_world_threshold_and_value() -> None:
    assert SOURCE_WORLD.min_horizon() == 2
    assert SOURCE_WORLD.try_value(1) == Fraction(56, 5)  # 11.2 < 12
    assert SOURCE_WORLD.optimal_value(6) == Fraction(486, 5)  # 97.2


def test_washout_raises_threshold() -> None:
    assert L3_WORLD.min_horizon() == 4
    assert L3_WORLD.try_value(3) == Fraction(168, 5)  # 33.6 < 36
    assert L3_WORLD.try_value(4) == Fraction(248, 5)  # 49.6 > 48
    free = TrialWorld(safe=Fraction(12), p_good=Fraction(2, 5), good=Fraction(25), poor=Fraction(2))
    assert free.min_horizon() == 2


def test_deadline_fallback_needs_room_for_resubmission() -> None:
    assert L4_WORLD.first_choice(4) == "B"
    assert L4_WORLD.first_choice(5) == "A"
    assert L4_WORLD.min_months_for_risky() == 5
    parallel = SubmissionWorld(
        sure_value=Fraction(12),
        sure_months=2,
        risky_value=Fraction(25),
        risky_p=Fraction(2, 5),
        risky_months=3,
        parallel=True,
    )
    assert parallel.min_months_for_risky() == 3


def test_verifier_rejects_copied_threshold() -> None:
    case = next(case for case in load_cases(DATASET) if case.id == "FAR-HORIZON-L3-01")
    tampered = case.model_copy(deep=True)
    tampered.target.answer.parts[2].value = "MIN_WEEKS=2"
    failed = {check.name for check in verify_case(tampered).checks if not check.passed}
    assert "stored-target-answer" in failed
