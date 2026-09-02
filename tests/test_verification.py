from mindsetbench.data import PROJECT_ROOT, load_manifest
from mindsetbench.verification import registered_case_ids, verify_case


def test_vertical_slice_has_executable_verifiers() -> None:
    cases = load_manifest(PROJECT_ROOT / "data" / "manifests" / "smoke.json")
    assert {case.id for case in cases} <= registered_case_ids()
    results = [verify_case(case) for case in cases]
    assert all(result.passed for result in results)
