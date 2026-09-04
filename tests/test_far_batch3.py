"""Third far-transfer batch: invariants, selection-induced association, scaling laws."""

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
from mindsetbench.verification import far_invariant_reachability as invar
from mindsetbench.verification import far_scaling_law as scale
from mindsetbench.verification import far_selection_association as berk
from mindsetbench.verification import verify_case

V1 = PROJECT_ROOT / "data" / "v1"
CARDS = PROJECT_ROOT / "data" / "schema_cards"
FAMILIES = {
    "far-invariant-reachability": "FAR-INVAR",
    "far-selection-association": "FAR-BERK",
    "far-scaling-law": "FAR-SCALE",
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


def test_invariants_block_unreachable_targets() -> None:
    assert invar.blackboard_finals(range(1, 10)) == {1, 3, 5, 7, 9}
    assert 0 in invar.blackboard_finals(range(1, 12))
    assert invar.cup_reachable_up_counts(7, 4) == {1, 3, 5, 7}
    assert invar.knight_distances((0, 0))[(7, 7)] == 6
    assert invar.knight_answer((0, 0), (7, 6), 5) == "FIVE=YES;MIN=5"
    assert len(invar.rotation_distances(6)) == 360, "3-cycles reach exactly half of 6!"
    assert invar.ledger_gap((50, 30, 20), (40, 60, 35)) == 5
    assert not invar.ledger_brute_force_reachable((50, 30, 20), (40, 60, 35), limit=60)
    assert invar.ledger_brute_force_reachable((50, 30, 20), (45, 60, 45), limit=60)


def test_selection_creates_or_reverses_association() -> None:
    assert berk.SOURCE.association() == "NONE"
    assert berk.SOURCE.select(berk.either).association() == "NEG"
    assert berk.L3.association() == "POS"
    assert berk.L3.select(berk.either).association() == "NEG"
    assert berk.grid_association([(1, 1), (1, 16), (4, 1), (4, 16)]) == "NONE"
    assert berk.l4_answer() == "POP=NONE;CAT=POS;INFER=NO"


def test_scaling_ratios() -> None:
    F = Fraction
    assert scale.intake_share(F(10), F(100), F(50)) == 5
    assert scale.time_scaled_by_length(F(4), F(8), F(10)) == 20
    assert scale.cube_root_scale(F(8)) == 2
    assert scale.safety_factor_at_scale(F(30), F(40)) == F(3, 4)
    assert scale.envelope_cost_per_m3(F(20), F(400)) == 120
    with pytest.raises(ValueError):
        scale.cube_root_scale(F(10))


def test_verifiers_reject_tampered_gold() -> None:
    by_id = {
        case.id: case for family in FAMILIES for case in load_cases(V1 / f"{family}-chain.yaml")
    }
    for case_id, index, value in [
        ("FAR-INVAR-L3-01", 0, "SWAP=YES"),
        ("FAR-BERK-L4-01", 0, "POP=POS"),
        ("FAR-SCALE-L3-01", 1, "MAX_SCALE=UNLIMITED"),
    ]:
        tampered = by_id[case_id].model_copy(deep=True)
        tampered.target.answer.parts[index].value = value
        failed = {check.name for check in verify_case(tampered).checks if not check.passed}
        assert "stored-target-answer" in failed, case_id
