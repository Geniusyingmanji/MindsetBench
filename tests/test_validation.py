from mindsetbench.data import PROJECT_ROOT, load_cases, load_manifest, validate_dataset
from mindsetbench.data.validate import Severity


def test_legacy_dataset_passes_compatibility_validation() -> None:
    report = validate_dataset(load_cases())
    assert report.ok
    assert report.warnings


def test_strict_v1_rejects_legacy_cases() -> None:
    case = next(case for case in load_cases() if case.id == "L3-A-01")
    report = validate_dataset([case], strict_v1=True)
    codes = {issue.code for issue in report.issues if issue.severity == Severity.ERROR}
    assert {"legacy-version", "missing-split", "missing-copy-probe", "incomplete-lure"} <= codes


def test_vertical_slice_passes_strict_v1() -> None:
    cases = load_manifest(PROJECT_ROOT / "data" / "manifests" / "smoke.json")
    report = validate_dataset(cases, strict_v1=True)
    assert report.ok, report.issues


def test_duplicate_ids_are_rejected() -> None:
    case = load_cases()[0]
    report = validate_dataset([case, case.model_copy(deep=True)])
    assert any(issue.code == "duplicate-id" for issue in report.errors)


def test_answer_format_must_not_embed_complete_multipart_gold() -> None:
    case = next(case for case in load_cases() if len(case.target.answer.parts) > 1)
    leaked = case.model_copy(deep=True)
    leaked.target.answer_format = leaked.target.answer.legacy_value()
    report = validate_dataset([leaked])
    assert any(issue.code == "answer-format-leaks-gold" for issue in report.errors)


def test_answer_format_prefix_must_match_gold_part() -> None:
    case = load_cases()[0].model_copy(deep=True)
    case.target.answer_format = "VALUE=<答案>"
    report = validate_dataset([case])
    assert any(issue.code == "answer-format-prefix-mismatch" for issue in report.errors)
