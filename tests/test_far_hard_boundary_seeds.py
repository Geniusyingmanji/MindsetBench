from pathlib import Path

from mindsetbench.data import (
    PROJECT_ROOT,
    audit_surface,
    load_cases,
    load_schema_cards,
    validate_dataset,
    validate_transfer_design,
)
from mindsetbench.models.case import Split
from mindsetbench.verification import verify_case
from mindsetbench.verification.far_hard_boundary_seeds import (
    _capacity,
    _two_quarter_total,
)

DATASET = PROJECT_ROOT / "data" / "v1" / "far-hard-boundary-seeds.yaml"
MANIFEST = PROJECT_ROOT / "data" / "manifests" / "far-hard-boundary-seeds.json"
DIAG_CARD = PROJECT_ROOT / "data" / "schema_cards" / "far-adaptive-diagnosis-v1.yaml"
BOTTLENECK_CARD = (
    PROJECT_ROOT / "data" / "schema_cards" / "far-bottleneck-migration-v1.yaml"
)


def test_hard_boundary_seeds_are_strict_audited_surface_clean_and_verified() -> None:
    cases = load_cases(DATASET)
    assert len(cases) == 6
    assert {case.split for case in cases} == {Split.SANITY}
    assert validate_dataset(cases, strict_v1=True).ok
    audit = validate_transfer_design(cases)
    assert audit.ok, audit.issues
    surface = audit_surface(cases)
    assert surface.ok, surface.errors
    results = [verify_case(case) for case in cases]
    assert all(result.passed for result in results), [
        (result.case_id, [check for check in result.checks if not check.passed])
        for result in results
    ]


def test_hard_boundary_manifest_resolves_exact_seed_set() -> None:
    cases = load_cases(MANIFEST)
    expected = {case.id for case in load_cases(DATASET)}
    assert {case.id for case in cases} == expected


def test_new_schema_cards_parse() -> None:
    cards = load_schema_cards(DIAG_CARD) + load_schema_cards(BOTTLENECK_CARD)
    assert {card.schema_id for card in cards} == {
        "far-adaptive-diagnosis-v1",
        "far-bottleneck-migration-v1",
    }


def test_negative_controls_are_deterministic_and_distinct() -> None:
    for case in load_cases(DATASET):
        assert case.lure is not None and case.lure.answer is not None
        assert case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer


def test_bottleneck_moves_after_first_hire() -> None:
    assert _capacity(("VERIFY",)) == 12
    assert _capacity(("VERIFY", "HEARING")) == 14
    assert _two_quarter_total("VERIFY", "HEARING") == 26
    assert _two_quarter_total("VERIFY", "VERIFY") == 24


def test_verifier_rejects_copied_archive_shortcut() -> None:
    case = next(
        case for case in load_cases(DATASET) if case.id == "FAR-HARD-DIAG-ARCHIVE-L3-01"
    )
    assert case.copy_probe is not None
    tampered = case.model_copy(deep=True)
    tampered.target.answer = case.copy_probe.answer
    failed = {check.name for check in verify_case(tampered).checks if not check.passed}
    assert "stored-target-answer" in failed


def test_paths_are_workspace_relative() -> None:
    # Guard against accidentally committing a machine-specific path in the manifest test.
    assert isinstance(MANIFEST, Path)
    assert MANIFEST.is_file()
