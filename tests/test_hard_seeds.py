from mindsetbench.data import PROJECT_ROOT, load_cases, validate_dataset
from mindsetbench.verification import verify_case

DATASET = PROJECT_ROOT / "data" / "v1" / "hard-seeds.yaml"


def test_hard_seeds_are_strict_v1_and_verified() -> None:
    cases = load_cases(DATASET)
    report = validate_dataset(cases, strict_v1=True)
    assert report.ok, report.issues
    assert len(cases) == 9
    assert {case.paradigm.value for case in cases} == {"P2", "P3", "P4", "P6"}
    results = [verify_case(case) for case in cases]
    assert all(result.passed for result in results), results


def test_hard_seeds_have_deterministic_negative_controls() -> None:
    for case in load_cases(DATASET):
        assert case.lure is not None and case.lure.answer is not None
        assert case.copy_probe is not None
        assert case.copy_probe.answer != case.target.answer
