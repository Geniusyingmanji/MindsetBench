from mindsetbench.data import (
    PROJECT_ROOT,
    load_cases,
    validate_dataset,
    validate_transfer_design,
)
from mindsetbench.verification import verify_case
from mindsetbench.verification.formal_p5_latent import (
    CATALOGUE,
    CHAIN_LEVEL_SPECS,
    L4_CATALOGUE,
    _parse_problem,
)

DATASET = PROJECT_ROOT / "data" / "v1" / "p5-latent-seeds.yaml"
CHAIN_DATASET = PROJECT_ROOT / "data" / "v1" / "formal-p5-latent-chain.yaml"
STAGED_DATASET = PROJECT_ROOT / "data" / "v1" / "p5-latent-staged.yaml"


def test_p5_latent_seed_is_strict_and_verified() -> None:
    cases = load_cases(DATASET)
    report = validate_dataset(cases, strict_v1=True)
    assert report.ok, report.issues
    assert len(cases) == 1
    result = verify_case(cases[0])
    assert result.passed, result
    assert len(result.checks) == 19


def test_p5_latent_seed_has_deterministic_negative_control() -> None:
    case = load_cases(DATASET)[0]
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None
    assert case.copy_probe.answer == case.lure.answer
    assert case.copy_probe.answer != case.target.answer


def test_p5_latent_verifier_rejects_calibration_log_drift() -> None:
    case = load_cases(DATASET)[0].model_copy(deep=True)
    assert "K7:10010111→01011110" in case.target.problem
    case.target.problem = case.target.problem.replace(
        "K7:10010111→01011110",
        "K7:10010111→01011111",
        1,
    )
    result = verify_case(case)
    assert not result.passed
    assert any(not check.passed and check.name == "target-text-problem" for check in result.checks)


def test_p5_latent_chain_is_complete_strict_and_verified() -> None:
    cases = load_cases(CHAIN_DATASET)
    report = validate_transfer_design(cases, require_complete_chains=True)
    assert report.ok, report.issues
    assert [case.level for case in cases] == [0, 1, 2, 3, 4]
    assert len({case.chain for case in cases}) == 1
    for case in cases:
        result = verify_case(case)
        assert result.passed, result
        assert len(result.checks) == 16


def test_p5_latent_l4_set_representation_matches_bit_affine_catalogue() -> None:
    bit_transforms = dict(CATALOGUE)
    set_transforms = dict(L4_CATALOGUE)
    for index in range(1, 10):
        bit_transform = bit_transforms[f"F{index}"]
        set_transform = set_transforms[f"G{index}"]
        assert all(bit_transform.apply(state) == set_transform.apply(state) for state in range(256))

    l4_case = load_cases(CHAIN_DATASET)[4]
    assert _parse_problem(l4_case.target.problem) == CHAIN_LEVEL_SPECS[4].target


def test_p5_latent_l4_verifier_rejects_set_toggle_drift() -> None:
    case = load_cases(CHAIN_DATASET)[4].model_copy(deep=True)
    assert "G9=取(b,a,d,c,f,e,h,g)△{c,d,f,h}" in case.target.problem
    case.target.problem = case.target.problem.replace(
        "G9=取(b,a,d,c,f,e,h,g)△{c,d,f,h}",
        "G9=取(b,a,d,c,f,e,h,g)△{c,d,f,g}",
        1,
    )
    result = verify_case(case)
    assert not result.passed
    assert any(not check.passed and check.name == "target-text-problem" for check in result.checks)


def test_formal30_manifest_has_no_duplicate_cases() -> None:
    cases = load_cases(PROJECT_ROOT / "data" / "manifests" / "formal30.json")
    assert len(cases) == 30
    assert len({case.id for case in cases}) == 30


def test_p5_latent_staged_probes_are_strict_audited_and_verified() -> None:
    cases = load_cases(STAGED_DATASET)
    report = validate_transfer_design(cases)
    assert report.ok, report.issues
    assert [case.id for case in cases] == [
        "DIAG-P5-LATENT-L4-ID-01",
        "DIAG-P5-LATENT-L4-PLAN-01",
        "DIAG-P5-LATENT-L4-PLAN-Q1-01",
        "DIAG-P5-LATENT-L4-PLAN-Q2-01",
        "DIAG-P5-LATENT-L4-PLAN-Q3-01",
    ]
    expected_checks = [13, 15, 15, 15, 15]
    for case, check_count in zip(cases, expected_checks, strict=True):
        result = verify_case(case)
        assert result.passed, result
        assert len(result.checks) == check_count


def test_staged_identification_and_planning_match_full_l4_gold() -> None:
    identification, planning, *single_queries = load_cases(STAGED_DATASET)
    full = load_cases(CHAIN_DATASET)[4]
    assert identification.target.answer.parts[2].value == "T3=G9"
    assert identification.target.answer.parts[-1].value == "UNUSED=G4"
    assert planning.target.answer == full.target.answer
    assert planning.copy_probe is not None and full.copy_probe is not None
    assert planning.copy_probe.answer == full.copy_probe.answer
    assert [case.target.answer.legacy_value() for case in single_queries] == [
        "7;T5>T3>T4>T2",
        "11;T5>T3>T2>T8>T6",
        "11;T8>T3>T2>T5>T6",
    ]


def test_staged_verifiers_reject_codebook_drift() -> None:
    identification, planning, *_ = [
        case.model_copy(deep=True) for case in load_cases(STAGED_DATASET)
    ]
    identification.target.problem = identification.target.problem.replace(
        "G9=取(b,a,d,c,f,e,h,g)△{c,d,f,h}",
        "G9=取(b,a,d,c,f,e,h,g)△{c,d,f,g}",
        1,
    )
    id_result = verify_case(identification)
    assert not id_result.passed
    assert any(
        not check.passed and check.name == "target-observation-text" for check in id_result.checks
    )

    planning.target.problem = planning.target.problem.replace("T3=G9", "T3=G4", 1)
    plan_result = verify_case(planning)
    assert not plan_result.passed
    assert any(
        not check.passed and check.name == "target-explicit-codebook"
        for check in plan_result.checks
    )
