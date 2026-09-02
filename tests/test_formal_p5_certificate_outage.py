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
    OUTAGE_SPECS,
    SOURCE_BASELINE,
    SOURCE_EFFECTIVE,
    TARGET_BASELINE,
    _apply_outage,
    _parse_frozen_action,
)
from mindsetbench.verification.formal_p5_chain import PlanningInstance, _parse_instance

DATASET = PROJECT_ROOT / "data" / "v1" / "formal-p5-certificate-outages.yaml"
MANIFEST = PROJECT_ROOT / "data" / "manifests" / "formal-p5-certificate-outages.json"


def test_outage_variants_are_strict_audited_and_verified() -> None:
    cases = load_cases(DATASET)
    strict = validate_dataset(cases, strict_v1=True)
    audit = validate_transfer_design(cases)
    assert strict.ok, strict.issues
    assert audit.ok, audit.issues
    assert len(cases) == 3
    assert {case.level for case in cases} == {4}
    assert len({case.id for case in cases}) == 3
    for case in cases:
        result = verify_case(case)
        assert result.passed, result
        assert len(result.checks) == 22


def test_outage_variants_have_fixed_gold_and_stale_controls() -> None:
    expected = {
        "FORMAL-P5-CERT-OUTAGE-K13-01": "17;K8>K10>K4>K9>K1>K6;0;1;18;2",
        "FORMAL-P5-CERT-OUTAGE-K2-01": "17;K8>K10>K4>K9>K1>K6;0;1;19;3",
        "FORMAL-P5-CERT-OUTAGE-K6-01": "18;K7>K2>K10>K4>K9>K16>K1;0;1;19;3",
    }
    stale = "17;K8>K10>K4>K9>K1>K6;0;1;18;3"
    cases = load_cases(DATASET)
    assert all(case.source == cases[0].source for case in cases)
    for case in cases:
        assert case.target.answer.legacy_value() == expected[case.id]
        assert case.lure is not None and case.lure.answer is not None
        assert case.lure.answer.legacy_value() == stale
        assert case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer


def test_outage_target_tables_show_the_same_sixteen_actions() -> None:
    for case in load_cases(DATASET):
        assert _parse_instance(case.target.problem) == TARGET_BASELINE
        assert _parse_frozen_action(case.target.problem) == OUTAGE_SPECS[case.id].frozen_action
        assert len(_parse_instance(case.target.problem).actions) == 16
        assert "冻结卡仍列在操作表中，但本题不得使用" in case.target.problem


def test_outage_source_removes_one_runner_path() -> None:
    assert len(SOURCE_BASELINE.actions) == 5
    assert len(SOURCE_EFFECTIVE.actions) == 4
    assert {action.name for action in SOURCE_BASELINE.actions} - {
        action.name for action in SOURCE_EFFECTIVE.actions
    } == {"S5"}


def test_outage_cost_layers_match_independent_first_hit_dfs() -> None:
    expected = {
        "FORMAL-P5-CERT-OUTAGE-K13-01": {17: 1, 18: 2},
        "FORMAL-P5-CERT-OUTAGE-K2-01": {17: 1, 19: 3},
        "FORMAL-P5-CERT-OUTAGE-K6-01": {18: 1, 19: 3},
    }

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

    for case_id, cost_counts in expected.items():
        instance = _apply_outage(TARGET_BASELINE, OUTAGE_SPECS[case_id].frozen_action)
        assert count_through(instance, max(cost_counts)) == cost_counts


def test_outage_lure_prompts_are_role_blinded() -> None:
    forbidden = ("错误", "真实", "目标题", "新版")
    for case in load_cases(DATASET):
        prompt = build_prompt(case.prompt_view(), Condition.WITH_LURE)
        reference = prompt.user.split("【参考题】", 1)[1].split("【目标题】", 1)[0]
        assert not any(marker in reference for marker in forbidden)
        assert case.lure is not None
        assert case.lure.why_structurally_different not in prompt.user


def test_outage_verifier_rejects_freeze_marker_drift() -> None:
    case = load_cases(DATASET)[0].model_copy(deep=True)
    case.target.problem = case.target.problem.replace("冻结卡=K13", "冻结卡=K2")
    result = verify_case(case)
    assert not result.passed
    assert any(not check.passed and check.name == "target-freeze-marker" for check in result.checks)


def test_outage_manifest_resolves_only_the_three_variants() -> None:
    direct = load_cases(DATASET)
    manifest = load_cases(MANIFEST)
    assert [case.id for case in manifest] == [case.id for case in direct]
