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
from mindsetbench.verification.far_latent_mechanism import (
    ALLOW,
    DENY,
    REMAND,
    feasible_policy,
    optimal_policies,
    response_matrix,
)
from mindsetbench.verification.far_social_learning import (
    joint_positive_action_likelihood,
    marginal_positive_action_likelihood,
)

DATASET = PROJECT_ROOT / "data" / "v1" / "far-latent-mechanism-seeds.yaml"
MANIFEST = PROJECT_ROOT / "data" / "manifests" / "far-latent-mechanism-seeds.json"
CARD = PROJECT_ROOT / "data" / "schema_cards" / "far-costed-active-identification-v1.yaml"


def test_latent_mechanism_seed_is_strict_far_and_verified() -> None:
    cases = load_cases(DATASET)
    assert len(cases) == 2
    assert {case.split for case in cases} == {Split.SANITY}
    assert validate_dataset(cases, strict_v1=True).ok
    assert validate_transfer_design(cases).ok
    assert audit_surface(cases).ok
    results = [verify_case(case) for case in cases]
    assert all(result.passed for result in results), [
        (result.case_id, [check for check in result.checks if not check.passed])
        for result in results
    ]


def test_schema_card_parses_for_seed_first_expansion() -> None:
    cards = load_schema_cards(CARD)
    assert len(cards) == 1
    assert cards[0].schema_id == "far-costed-active-identification-v1"


def test_latent_mechanism_manifest_resolves_both_screened_cases() -> None:
    assert {case.id for case in load_cases(MANIFEST)} == {
        "FAR-LATENT-PRECEDENT-L4-01",
        "FAR-LATENT-SOCIAL-CORRELATED-L4-02",
    }


def test_response_matrix_is_recovered_from_rules() -> None:
    matrix = response_matrix()
    assert tuple(matrix["X"].values()) == (DENY, DENY, ALLOW, REMAND, REMAND, DENY)
    assert tuple(matrix["Y"].values()) == (ALLOW, DENY, DENY, ALLOW, REMAND, REMAND)


def test_minimax_policy_is_unique_and_beats_balanced_first_split() -> None:
    policies = optimal_policies()
    assert len(policies) == 1
    policy = policies[0]
    assert policy.first == "X"
    assert policy.followups == {ALLOW: "STOP", DENY: "W", REMAND: "V"}
    assert policy.worst_cost == 7
    balanced = feasible_policy("Y")
    assert balanced is not None
    assert balanced.worst_cost == 8


def test_correlated_public_actions_are_not_squared_marginals() -> None:
    common_accuracy = Fraction(7, 10)
    private_accuracy = Fraction(13, 20)
    joint_true = joint_positive_action_likelihood(
        True,
        common_accuracy=common_accuracy,
        private_accuracy=private_accuracy,
    )
    joint_false = joint_positive_action_likelihood(
        False,
        common_accuracy=common_accuracy,
        private_accuracy=private_accuracy,
    )
    marginal_true = marginal_positive_action_likelihood(
        True,
        common_accuracy=common_accuracy,
        private_accuracy=private_accuracy,
    )
    marginal_false = marginal_positive_action_likelihood(
        False,
        common_accuracy=common_accuracy,
        private_accuracy=private_accuracy,
    )
    assert joint_true == Fraction(94809, 160000)
    assert joint_false == Fraction(17689, 160000)
    assert marginal_true == Fraction(741, 1000)
    assert marginal_false == Fraction(259, 1000)
    assert joint_true != marginal_true**2
    assert joint_false != marginal_false**2
