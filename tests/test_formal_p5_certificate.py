from itertools import combinations

from mindsetbench.data import (
    PROJECT_ROOT,
    load_cases,
    load_schema_cards,
    validate_dataset,
    validate_schema_cards,
    validate_transfer_design,
)
from mindsetbench.models.prompt import Condition
from mindsetbench.prompting import build_prompt
from mindsetbench.verification import verify_case
from mindsetbench.verification.formal_p5_certificate import LEVEL_SPECS
from mindsetbench.verification.formal_p5_chain import _goal, _replay

DATASET = PROJECT_ROOT / "data" / "v1" / "formal-p5-certificate-chain.yaml"
CARD = PROJECT_ROOT / "data" / "schema_cards" / "formal-p5-certificate-v1.yaml"
FORMAL35 = PROJECT_ROOT / "data" / "manifests" / "formal35.json"
FORMAL35_CARDS = PROJECT_ROOT / "data" / "manifests" / "formal35-cards.json"


def test_p5_certificate_chain_is_complete_strict_and_verified() -> None:
    cases = load_cases(DATASET)
    strict = validate_dataset(cases, strict_v1=True)
    design = validate_transfer_design(cases, require_complete_chains=True)
    assert strict.ok, strict.issues
    assert design.ok, design.issues
    assert [case.level for case in cases] == list(range(5))
    assert {case.chain for case in cases} == {"p5-stateful-planning-certificate-v1"}
    assert [case.id for case in cases] == [f"FORMAL-P5-CERT-L{level}-01" for level in range(5)]
    for case, check_count in zip(cases, (20, 20, 20, 23, 23), strict=True):
        result = verify_case(case)
        assert result.passed, result
        assert len(result.checks) == check_count


def test_p5_certificate_chain_has_fixed_six_part_gold_and_controls() -> None:
    expected = [
        "2;A1>A2;0;1;3;1",
        "4;B1>B2>B3;0;1;5;1",
        "11;C2>C1>C3>C4>C5>C6>C7;0;1;13;1",
        "15;K7>K2>K10>K4>K9>K1>K6>K3;0;1;16;3",
        "17;K8>K10>K4>K9>K1>K6;0;1;18;3",
    ]
    lures = [
        "1;A2;0;1;2;1",
        "1;B2;0;1;2;1",
        "3;C5>C6;0;1;4;2",
        "3;K1>K6;0;1;4;1",
        "15;K7>K2>K10>K4>K9>K1>K6>K3;0;1;16;3",
    ]
    for case, gold, lure in zip(load_cases(DATASET), expected, lures, strict=True):
        assert len(case.target.answer.parts) == 6
        assert "串内部只能用 >，不能用逗号" in case.source.problem
        assert "串内部只能用 >，不能用逗号" in case.target.problem
        assert case.target.answer.legacy_value() == gold
        assert case.lure is not None and case.lure.answer is not None
        assert case.lure.answer.legacy_value() == lure
        assert case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer


def test_p5_certificate_counts_match_independent_first_hit_dfs() -> None:
    expected = (
        {2: 1, 3: 1},
        {4: 1, 5: 1},
        {11: 1, 13: 1},
        {15: 1, 16: 3},
        {17: 1, 18: 3},
    )

    def counts_through(level: int, maximum_cost: int) -> dict[int, int]:
        instance = LEVEL_SPECS[level].target
        counts: dict[int, int] = {}

        def visit(state: frozenset[str], used: int, cost: int) -> None:
            if _goal(instance, state):
                counts[cost] = counts.get(cost, 0) + 1
                return
            for index, action in enumerate(instance.actions):
                next_cost = cost + action.cost
                if used & (1 << index) or next_cost > maximum_cost:
                    continue
                if not action.requires <= state or action.forbids & state:
                    continue
                next_state = (state - action.clears) | action.adds
                visit(next_state, used | (1 << index), next_cost)

        visit(instance.initial, 0, 0)
        return counts

    for level, cost_counts in enumerate(expected):
        assert counts_through(level, max(cost_counts)) == cost_counts


def test_p5_certificate_monotone_controls_have_independent_cost_layers() -> None:
    expected = ({1: 1, 2: 1}, {1: 1, 2: 1}, {3: 1, 4: 2}, {3: 1, 4: 1})
    for level, cost_counts in enumerate(expected):
        instance = LEVEL_SPECS[level].target
        maximum_cost = max(cost_counts)
        actual: dict[int, int] = {}
        for size in range(len(instance.actions) + 1):
            for selected in combinations(instance.actions, size):
                cost = sum(action.cost for action in selected)
                if cost > maximum_cost:
                    continue
                state = instance.initial | frozenset().union(*(action.adds for action in selected))
                if instance.goal_present <= state:
                    actual[cost] = actual.get(cost, 0) + 1
        assert actual == cost_counts


def test_p5_certificate_l4_is_single_effect_edit_and_stale_plan_fails() -> None:
    old = LEVEL_SPECS[3].target
    new = LEVEL_SPECS[4].target
    old_by_name = {action.name: action for action in old.actions}
    new_by_name = {action.name: action for action in new.actions}
    changed = {name for name in old_by_name if old_by_name[name] != new_by_name[name]}
    assert changed == {"K3"}
    assert old_by_name["K3"].adds == frozenset({"v"})
    assert new_by_name["K3"].adds == frozenset({"p"})
    assert not _replay(new, LEVEL_SPECS[3].expected_plan.actions)[0]


def test_p5_certificate_lure_prompts_do_not_disclose_control_status() -> None:
    forbidden = ("错误", "真实", "目标题", "新版")
    for case in load_cases(DATASET):
        prompt = build_prompt(case.prompt_view(), Condition.WITH_LURE)
        reference = prompt.user.split("【参考题】", 1)[1].split("【目标题】", 1)[0]
        assert not any(marker in reference for marker in forbidden)
        assert case.lure is not None
        assert case.lure.why_structurally_different not in prompt.user


def test_p5_certificate_verifier_rejects_runner_count_drift() -> None:
    case = load_cases(DATASET)[4].model_copy(deep=True)
    case.target.answer.parts[-1].value = "2"
    result = verify_case(case)
    assert not result.passed
    assert any(not check.passed and check.name == "stored-target" for check in result.checks)


def test_formal35_has_seven_complete_chains_and_matching_cards() -> None:
    cases = load_cases(FORMAL35)
    assert len(cases) == 35
    assert len({case.id for case in cases}) == 35
    design = validate_transfer_design(cases, require_complete_chains=True)
    assert design.ok, design.issues
    assert len({case.chain for case in cases}) == 7
    cards = load_schema_cards(FORMAL35_CARDS)
    assert len(cards) == 7
    card_report = validate_schema_cards(cards, cases)
    assert card_report.ok, card_report.issues
