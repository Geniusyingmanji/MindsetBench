from fractions import Fraction

import pytest

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
from mindsetbench.verification.far_evidence_independence import (
    failure_on_demand,
    independent_roots,
    witness_grade,
)

DATASET = PROJECT_ROOT / "data" / "v1" / "far-evidence-independence-chain.yaml"
CARDS = PROJECT_ROOT / "data" / "schema_cards" / "far-evidence-independence-v1.yaml"


def test_far_indep_chain_is_strict_audited_surface_clean_and_verified() -> None:
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


def test_far_indep_schema_card_matches_chain() -> None:
    report = validate_schema_cards(load_schema_cards(CARDS), load_cases(DATASET))
    assert report.ok, report.issues


def test_far_indep_negative_controls_are_deterministic_and_distinct() -> None:
    for case in load_cases(DATASET):
        assert case.lure is not None and case.lure.answer is not None
        assert case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer


def test_provenance_roots_and_grades() -> None:
    assert independent_roots({"a": None, "b": "a", "c": "b", "d": None}) == {"a", "d"}
    assert witness_grade(3) == "确证" and witness_grade(2) == "可信" and witness_grade(1) == "孤证"
    with pytest.raises(ValueError, match="cyclic"):
        independent_roots({"a": "b", "b": "a"})


def test_common_cause_probability_matches_hand_computation() -> None:
    p = Fraction(1, 10)
    independent = failure_on_demand(
        [p] * 3, [False] * 3, detections_needed=2, reference_fault=Fraction(0)
    )
    assert independent == 3 * p * p * (1 - p) + p**3
    shared = failure_on_demand(
        [p] * 3, [True, True, False], detections_needed=2, reference_fault=Fraction(1, 20)
    )
    assert shared == Fraction(1, 20) + Fraction(19, 20) * independent
    assert float(shared) == pytest.approx(0.0766)


def test_verifier_rejects_tampered_gold_and_missing_facts() -> None:
    cases = {case.id: case for case in load_cases(DATASET)}
    tampered = cases["FAR-INDEP-L4-01"].model_copy(deep=True)
    tampered.target.answer.parts[1].value = "A"
    assert not verify_case(tampered).passed

    stripped = cases["FAR-INDEP-L3-01"].model_copy(deep=True)
    stripped.target.problem = stripped.target.problem.replace("14:00 起方可调阅", "可以调阅")
    failed = [check.name for check in verify_case(stripped).checks if not check.passed]
    assert failed == ["target-text-carries-required-facts"]
