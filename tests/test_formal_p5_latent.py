from mindsetbench.data import PROJECT_ROOT, load_cases, validate_dataset
from mindsetbench.verification import verify_case

DATASET = PROJECT_ROOT / "data" / "v1" / "p5-latent-seeds.yaml"


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
