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
from mindsetbench.verification.far_credible_commitment import (
    L3_MEASURES,
    L4_LURE_MEASURES,
    L4_MEASURES,
    Measure,
    ThreatMeasure,
    classify,
    credible,
    shortcut,
    threat_answer,
)

DATASET = PROJECT_ROOT / "data" / "v1" / "far-credible-commitment-chain.yaml"
CARDS = PROJECT_ROOT / "data" / "schema_cards" / "far-credible-commitment-v1.yaml"


def test_far_commit_chain_is_strict_audited_surface_clean_and_verified() -> None:
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


def test_far_commit_schema_card_matches_chain() -> None:
    report = validate_schema_cards(load_schema_cards(CARDS), load_cases(DATASET))
    assert report.ok, report.issues


def test_far_commit_negative_controls_are_deterministic_and_distinct() -> None:
    for case in load_cases(DATASET):
        assert case.lure is not None and case.lure.answer is not None
        assert case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer


def test_alignment_turns_a_third_party_into_the_promiser() -> None:
    aligned = Measure("X", "other", aligned=True, enforcement=True)
    assert not credible(aligned)
    assert credible(aligned, check_alignment=False)
    assert shortcut(aligned)
    assert classify(L3_MEASURES, credible) == "T1=CHEAP;T2=CHEAP;T3=CREDIBLE;T4=CHEAP"


def test_threat_credibility_is_a_payoff_comparison() -> None:
    assert threat_answer(L4_MEASURES) == "M1=CHEAP;M2=CREDIBLE;M3=CHEAP;M4=CHEAP"
    assert threat_answer(L4_LURE_MEASURES) == "M1=CHEAP;M2=CREDIBLE;M3=CREDIBLE;M4=CREDIBLE"
    tie = ThreatMeasure("Z", Fraction(-2), Fraction(-2))
    assert not tie.credible(), "a tie does not make the threat credible"


def test_verifier_rejects_shortcut_answer() -> None:
    case = next(case for case in load_cases(DATASET) if case.id == "FAR-COMMIT-L2-01")
    tampered = case.model_copy(deep=True)
    tampered.target.answer.parts[2].value = "M3=CREDIBLE"
    failed = {check.name for check in verify_case(tampered).checks if not check.passed}
    assert "stored-target-answer" in failed
