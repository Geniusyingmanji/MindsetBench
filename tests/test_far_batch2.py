"""Second far-transfer batch: delayed feedback, selection extremes, threshold cascades."""

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
from mindsetbench.verification import far_delayed_feedback as delay
from mindsetbench.verification import far_selection_extreme as extreme
from mindsetbench.verification import far_threshold_cascade as cascade
from mindsetbench.verification import verify_case

V1 = PROJECT_ROOT / "data" / "v1"
CARDS = PROJECT_ROOT / "data" / "schema_cards"
FAMILIES = {
    "far-delayed-feedback": "FAR-DELAY",
    "far-selection-extreme": "FAR-EXTREME",
    "far-threshold-cascade": "FAR-CASCADE",
}


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_family_is_strict_audited_surface_clean_and_verified(family: str) -> None:
    cases = load_cases(V1 / f"{family}-chain.yaml")
    assert len(cases) == 5
    assert [case.level for case in cases] == list(range(5))
    assert {case.level: case.split for case in cases} == {
        0: Split.CALIBRATION,
        1: Split.CALIBRATION,
        2: Split.SANITY,
        3: Split.SANITY,
        4: Split.SANITY,
    }
    assert all(case.id.startswith(FAMILIES[family]) for case in cases)
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
    cards = validate_schema_cards(load_schema_cards(CARDS / f"{family}-v1.yaml"), cases)
    assert cards.ok, cards.issues
    for case in cases:
        assert case.lure is not None and case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer


def test_delayed_feedback_full_correction_oscillates_and_small_gain_settles() -> None:
    F = Fraction
    full = delay.simulate_errors(F(-20), F(1), 2, 12)
    assert delay.settle_step(full, F(1)) is None
    assert full[1] == 0 and full[2] == 20, "one-step 'success' followed by a 20-degree overshoot"
    gentle = delay.simulate_errors(F(-20), F(1, 5), 2, 12)
    assert delay.settle_step(gentle, F(1)) == 6
    assert not delay.overshoots(gentle, F(1))
    assert delay.steady_level(F(100), F(1, 5), F(3, 10)) == 60
    gain, tail = delay.attenuating_gain()
    assert gain == F(3, 10) and float(tail) == pytest.approx(3.06, abs=0.01)


def test_selection_extreme_family_wise_versus_single_unit() -> None:
    F = Fraction
    single = extreme.tail(200, F(3, 20), 43)
    family = extreme.any_unit_tail([(200, 43)] * 25, F(3, 20))
    assert single < F(1, 20) < family
    assert extreme.min_alarming_count(25, 200, F(3, 20), F(1, 20)) == 46
    assert extreme.l3_answers() == ("ACT=YES;MIN40=10", "ACT=NO;MIN40=11")
    expected = extreme.posterior_mean_ability(19, 20, extreme.L4_ABILITIES) * 20
    assert float(expected) == pytest.approx(17.6, abs=0.05)


def test_threshold_cascade_gap_ring_and_collapse() -> None:
    assert cascade.cascade_size(cascade.expand(cascade.SOURCE_A)) == 100
    assert cascade.cascade_size(cascade.expand(cascade.SOURCE_B)) == 15
    assert cascade.ring_cascade((1, 2), 12, 2, 2) == 12
    assert cascade.ring_cascade((1, 7), 12, 2, 2) == 2
    F = Fraction
    assert cascade.collapse(cascade.L4_LOADS, cascade.L4_P, 2) == 8
    assert cascade.collapse(cascade.L4_LOADS, cascade.L4_Q, 2) == 1
    assert cascade.collapse(cascade.L4_LOADS, tuple(F(16) for _ in range(8)), 2) == 1


def test_verifiers_reject_tampered_gold() -> None:
    by_id = {
        case.id: case for family in FAMILIES for case in load_cases(V1 / f"{family}-chain.yaml")
    }
    for case_id, index, value in [
        ("FAR-DELAY-L2-01", 0, "GAIN=1.0"),
        ("FAR-EXTREME-L2-01", 0, "ACT=YES"),
        ("FAR-CASCADE-L4-01", 0, "P=1"),
    ]:
        tampered = by_id[case_id].model_copy(deep=True)
        tampered.target.answer.parts[index].value = value
        failed = {check.name for check in verify_case(tampered).checks if not check.passed}
        assert "stored-target-answer" in failed, case_id
