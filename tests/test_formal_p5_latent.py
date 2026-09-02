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
