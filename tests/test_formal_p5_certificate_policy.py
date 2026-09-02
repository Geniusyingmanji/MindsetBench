from mindsetbench.data import (
    PROJECT_ROOT,
    load_cases,
    validate_dataset,
    validate_transfer_design,
)
from mindsetbench.models.prompt import Condition
from mindsetbench.prompting import build_prompt
from mindsetbench.verification import verify_case
from mindsetbench.verification.formal_p5_certificate_outage import (
    TARGET_BASELINE,
    _apply_outage,
)
from mindsetbench.verification.formal_p5_certificate_policy import (
    FALSE_INSIGHT,
    LURE_JOINT_ANSWER,
    ORACLE_INSIGHT,
    SOURCE_POLICY_STATEMENT,
    TARGET_JOINT_ANSWER,
    TARGET_POLICIES,
)
from mindsetbench.verification.formal_p5_chain import Action, PlanningInstance, _parse_instance

DATASET = PROJECT_ROOT / "data" / "v1" / "formal-p5-certificate-policy-joint.yaml"
MANIFEST = PROJECT_ROOT / "data" / "manifests" / "formal-p5-certificate-policy-joint.json"


def test_policy_joint_case_is_strict_audited_and_verified() -> None:
    cases = load_cases(DATASET)
    assert len(cases) == 1
    strict = validate_dataset(cases, strict_v1=True)
    audit = validate_transfer_design(cases)
    assert strict.ok, strict.issues
    assert audit.ok, audit.issues
    result = verify_case(cases[0])
    assert result.passed, result
    assert len(result.checks) == 27


def test_policy_joint_answers_have_three_seven_part_blocks() -> None:
    case = load_cases(DATASET)[0]
    assert case.source.answer == "S5;2;S1>S2;0;1;3;1"
    assert SOURCE_POLICY_STATEMENT in case.source.problem
    assert case.target.answer.legacy_value() == TARGET_JOINT_ANSWER
    assert len(case.target.answer.parts) == 21
    assert case.lure is not None and case.lure.answer is not None
    assert case.lure.answer.legacy_value() == LURE_JOINT_ANSWER
    assert len(case.lure.answer.parts) == 21
    assert case.copy_probe is not None
    assert case.copy_probe.answer == case.lure.answer
    assert case.copy_probe.answer != case.target.answer

    blocks = [case.target.answer.parts[start : start + 7] for start in range(0, 21, 7)]
    assert [block[0].value for block in blocks] == ["K13", "K2", "K6"]
    assert all(len(block) == 7 for block in blocks)


def test_policy_joint_predicates_match_independently() -> None:
    positive = TARGET_BASELINE.goal_present
    negative = TARGET_BASELINE.goal_absent
    initial = TARGET_BASELINE.initial

    def alpha(action: Action) -> bool:
        return (
            action.cost == 4
            and len(action.requires) == 1
            and action.requires <= positive
            and action.adds == positive - action.requires
            and not action.forbids
            and not action.clears
        )

    def beta(action: Action) -> bool:
        return (
            action.cost == 2
            and action.requires == initial & negative
            and len(action.adds) == 1
            and action.adds <= negative
            and len(action.clears) == 1
            and action.clears <= positive
        )

    def gamma(action: Action) -> bool:
        return (
            action.cost == 1
            and len(action.requires) == len(action.adds) == 1
            and action.requires | action.adds <= positive
            and not action.forbids
            and not action.clears
        )

    assert tuple(
        tuple(action.name for action in TARGET_BASELINE.actions if predicate(action))
        for predicate in (alpha, beta, gamma)
    ) == (("K13",), ("K2",), ("K6",))


def test_policy_joint_cost_layers_match_independent_first_hit_dfs() -> None:
    expected = (("K13", {17: 1, 18: 2}), ("K2", {17: 1, 19: 3}), ("K6", {18: 1, 19: 3}))

    def count_through(instance: PlanningInstance, maximum_cost: int) -> dict[int, int]:
        actual: dict[int, int] = {}

        def visit(state: frozenset[str], used: int, cost: int) -> None:
            if instance.goal_present <= state and not instance.goal_absent & state:
                actual[cost] = actual.get(cost, 0) + 1
                return
            for index, action in enumerate(instance.actions):
                next_cost = cost + action.cost
                if used & (1 << index) or next_cost > maximum_cost:
                    continue
                if not action.requires <= state or action.forbids & state:
                    continue
                visit(
                    (state - action.clears) | action.adds,
                    used | (1 << index),
                    next_cost,
                )

        visit(instance.initial, 0, 0)
        return actual

    for action_name, cost_counts in expected:
        instance = _apply_outage(TARGET_BASELINE, action_name)
        assert count_through(instance, max(cost_counts)) == cost_counts


def test_policy_joint_target_and_lure_are_path_decoupled() -> None:
    case = load_cases(DATASET)[0]
    assert _parse_instance(case.target.problem) == TARGET_BASELINE
    assert case.lure is not None and case.lure.answer is not None
    lure_value = case.lure.answer.legacy_value()
    assert "K" not in lure_value
    assert "R" not in case.target.answer.legacy_value()
    assert "K8>K10>K4>K9>K1>K6" not in lure_value


def test_policy_joint_lure_prompt_is_role_blinded() -> None:
    case = load_cases(DATASET)[0]
    prompt = build_prompt(case.prompt_view(), Condition.WITH_LURE)
    reference = prompt.user.split("【参考题】", 1)[1].split("【目标题】", 1)[0]
    assert not any(marker in reference for marker in ("错误", "真实", "目标题", "新版"))
    assert case.lure is not None
    assert case.lure.why_structurally_different not in prompt.user


def test_policy_joint_mindset_controls_are_path_decoupled() -> None:
    case = load_cases(DATASET)[0]
    assert case.hints is not None
    assert case.hints.oracle_mindset is not None
    assert case.hints.false_mindset is not None
    assert case.hints.oracle_mindset.insight == ORACLE_INSIGHT
    assert case.hints.false_mindset.insight == FALSE_INSIGHT
    for condition in (Condition.H3_ORACLE_MINDSET, Condition.H3_FALSE_MINDSET):
        prompt = build_prompt(case.prompt_view(), condition)
        hint = prompt.user.split("【目标题】", 1)[0]
        assert "K1" not in hint
        assert "R1" not in hint


def test_policy_joint_verifier_rejects_predicate_drift() -> None:
    case = load_cases(DATASET)[0].model_copy(deep=True)
    case.target.problem = case.target.problem.replace("α:费用=4", "α:费用=5")
    result = verify_case(case)
    assert not result.passed
    assert any(
        not check.passed and check.name == "target-policy-statements" for check in result.checks
    )


def test_policy_joint_manifest_resolves_the_case() -> None:
    assert [case.id for case in load_cases(MANIFEST)] == ["FORMAL-P5-CERT-POLICY-JOINT-01"]


def test_policy_definitions_are_ordered_and_unique() -> None:
    assert tuple(policy.name for policy in TARGET_POLICIES) == ("α", "β", "γ")
    assert len({policy.statement for policy in TARGET_POLICIES}) == 3
