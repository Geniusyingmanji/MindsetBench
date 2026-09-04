from fractions import Fraction

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
from mindsetbench.verification.far_social_learning import (
    HIGH_BAR_THRESHOLDS,
    SOURCE_ACCURACIES,
    TARGET_ACCURACIES,
    positive_sequence,
    sealed_positive_posterior,
)

DATASET = PROJECT_ROOT / "data" / "v1" / "far-social-learning-seed.yaml"
MANIFEST = PROJECT_ROOT / "data" / "manifests" / "far-social-learning-seed.json"
CARD = PROJECT_ROOT / "data" / "schema_cards" / "far-social-learning-cascade-v1.yaml"


def test_social_learning_cases_are_strict_audited_surface_clean_and_verified() -> None:
    cases = load_cases(DATASET)
    assert len(cases) == 3
    assert {case.split for case in cases} == {Split.SANITY}
    assert validate_dataset(cases, strict_v1=True).ok
    audit = validate_transfer_design(cases)
    assert audit.ok, audit.issues
    surface = audit_surface(cases)
    assert surface.ok, surface.errors
    assert all(verify_case(case).passed for case in cases)


def test_social_learning_manifest_and_card_parse() -> None:
    assert len(load_cases(MANIFEST)) == 3
    cards = load_schema_cards(CARD)
    assert len(cards) == 1
    assert cards[0].schema_id == "far-social-learning-cascade-v1"


def test_homogeneous_public_actions_stop_revealing_signals() -> None:
    informative, posterior = positive_sequence(SOURCE_ACCURACIES)
    assert informative == 2
    assert posterior == Fraction(49, 58)


def test_stronger_third_expert_temporarily_breaks_the_cascade() -> None:
    informative, posterior = positive_sequence(TARGET_ACCURACIES)
    assert informative == 3
    assert posterior == Fraction(49, 50)
    assert sealed_positive_posterior(TARGET_ACCURACIES) == Fraction(343, 346)


def test_high_decision_bar_restores_the_fourth_signal() -> None:
    informative, posterior = positive_sequence(
        TARGET_ACCURACIES,
        thresholds=HIGH_BAR_THRESHOLDS,
    )
    assert informative == 4
    assert posterior == Fraction(343, 346)
