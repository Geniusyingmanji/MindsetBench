from collections import Counter

from mindsetbench.data import (
    PROJECT_ROOT,
    load_cases,
    load_schema_cards,
    validate_dataset,
    validate_schema_cards,
    validate_transfer_design,
)
from mindsetbench.verification import verify_case
from mindsetbench.verification.institutional_mechanism import (
    MechanismCase,
    MechanismLabel,
    classify_mechanism,
)

DATASET = PROJECT_ROOT / "data" / "v1" / "hss-p8-institutional-mechanism-chain.yaml"
CARDS = PROJECT_ROOT / "data" / "schema_cards" / "hss-p8-institutional-mechanism-v1.yaml"
MANIFEST = PROJECT_ROOT / "data" / "manifests" / "hss20.json"
HARD_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "hss20-hard.json"


def test_hss_p8_chain_is_complete_strict_audited_and_verified() -> None:
    cases = load_cases(DATASET)
    strict = validate_dataset(cases, strict_v1=True)
    audit = validate_transfer_design(cases, require_complete_chains=True)
    assert strict.ok, strict.issues
    assert audit.ok, audit.issues
    assert len(cases) == 5
    assert [case.level for case in cases] == list(range(5))
    assert {case.chain for case in cases} == {"hss-p8-institutional-mechanism-v1"}

    results = [verify_case(case) for case in cases]
    assert all(result.passed for result in results), results


def test_hss_p8_schema_card_and_hss20_manifest_match() -> None:
    direct = load_cases(DATASET)
    cards = load_schema_cards(CARDS)
    report = validate_schema_cards(cards, direct)
    assert report.ok, report.issues

    manifest = load_cases(MANIFEST)
    assert len(manifest) == 20
    assert Counter(case.level for case in manifest) == {0: 4, 1: 4, 2: 4, 3: 4, 4: 4}
    assert Counter(case.paradigm.value for case in manifest) == {
        "P4": 5,
        "P6": 5,
        "P7": 5,
        "P8": 5,
    }


def test_hss20_meets_nonnumeric_and_distance_contracts() -> None:
    cases = load_cases(MANIFEST)
    assert all(part.type.value != "number" for case in cases for part in case.target.answer.parts)
    for case in cases:
        assert case.lure is not None and case.lure.answer is not None
        assert case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer
        if case.level == 4:
            assert case.mapping.added_relations or case.mapping.removed_relations
            assert case.mapping.adaptation_required


def test_hss20_hard_manifest_selects_every_l3_and_l4_once() -> None:
    full = load_cases(MANIFEST)
    hard = load_cases(HARD_MANIFEST)
    expected = {case.id for case in full if case.level >= 3}
    assert len(hard) == 8
    assert {case.id for case in hard} == expected
    assert all(case.level >= 3 for case in hard)


def test_mechanism_classifier_distinguishes_core_mechanisms() -> None:
    separating = MechanismCase(
        True,
        costly_action=True,
        actor_bears_cost=True,
        committed_type_can_bear=True,
    )
    commitment = MechanismCase(True, removes_defection_option=True)
    pooling = MechanismCase(
        True,
        costly_action=True,
        actor_bears_cost=True,
        committed_type_can_bear=True,
        opportunistic_type_can_bear=True,
    )
    assert classify_mechanism(separating) == MechanismLabel.SEPARATING_SIGNAL
    assert classify_mechanism(commitment) == MechanismLabel.CREDIBLE_COMMITMENT
    assert classify_mechanism(pooling) == MechanismLabel.POOLING_SIGNAL
    assert classify_mechanism(MechanismCase(False)) == MechanismLabel.NONCREDIBLE


def test_third_party_reimbursement_turns_separation_into_pooling() -> None:
    case = MechanismCase(
        True,
        costly_action=True,
        actor_bears_cost=True,
        committed_type_can_bear=True,
        third_party_reimbursement=True,
    )
    assert classify_mechanism(case) == MechanismLabel.POOLING_SIGNAL


def test_timing_and_feasibility_precede_costly_signal_classification() -> None:
    too_late = MechanismCase(
        False,
        removes_defection_option=True,
        costly_action=True,
        actor_bears_cost=True,
        committed_type_can_bear=True,
    )
    infeasible = MechanismCase(
        True,
        costly_action=True,
        actor_bears_cost=True,
        committed_type_can_bear=False,
    )
    assert classify_mechanism(too_late) == MechanismLabel.NONCREDIBLE
    assert classify_mechanism(infeasible) == MechanismLabel.NONCREDIBLE
