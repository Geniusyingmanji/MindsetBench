from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from heapq import heappop, heappush
from itertools import combinations

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register


@dataclass(frozen=True)
class Action:
    name: str
    cost: int
    requires: frozenset[str]
    forbids: frozenset[str]
    adds: frozenset[str]
    clears: frozenset[str]


@dataclass(frozen=True)
class PlanningInstance:
    initial: frozenset[str]
    goal_present: frozenset[str]
    goal_absent: frozenset[str]
    actions: tuple[Action, ...]


@dataclass(frozen=True)
class Plan:
    cost: int
    actions: tuple[str, ...]
    final_state: frozenset[str]


def _tokens(raw: str) -> frozenset[str]:
    return frozenset() if raw == "-" else frozenset(raw.split(","))


def _action(
    name: str,
    cost: int,
    *,
    requires: str = "-",
    forbids: str = "-",
    adds: str = "-",
    clears: str = "-",
) -> Action:
    return Action(
        name=name,
        cost=cost,
        requires=_tokens(requires),
        forbids=_tokens(forbids),
        adds=_tokens(adds),
        clears=_tokens(clears),
    )


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


def _gold(case: Case) -> str:
    return case.target.answer.legacy_value()


def _lure(case: Case) -> str:
    assert case.lure and case.lure.answer
    return case.lure.answer.legacy_value()


def _copy(case: Case) -> str:
    assert case.copy_probe
    return case.copy_probe.answer.legacy_value()


def _goal(instance: PlanningInstance, state: frozenset[str]) -> bool:
    return instance.goal_present <= state and not instance.goal_absent & state


@cache
def _best_plans(instance: PlanningInstance, max_extra_cost: int = 0) -> tuple[Plan, ...]:
    """Find every plan within a fixed margin of the optimum."""

    queue: list[tuple[int, tuple[str, ...], frozenset[str], int]] = [(0, (), instance.initial, 0)]
    best_by_state_and_used = {(instance.initial, 0): 0}
    best_goal_cost: int | None = None
    plans: list[Plan] = []

    while queue:
        cost, path, state, used = heappop(queue)
        if cost != best_by_state_and_used.get((state, used)):
            continue
        if best_goal_cost is not None and cost > best_goal_cost + max_extra_cost:
            break
        if _goal(instance, state):
            best_goal_cost = cost if best_goal_cost is None else best_goal_cost
            plans.append(Plan(cost=cost, actions=path, final_state=state))
            continue

        for index, action in enumerate(instance.actions):
            if used & (1 << index):
                continue
            if not action.requires <= state or action.forbids & state:
                continue
            next_state = (state - action.clears) | action.adds
            next_used = used | (1 << index)
            next_cost = cost + action.cost
            key = (next_state, next_used)
            if next_cost > best_by_state_and_used.get(key, 10**18):
                continue
            best_by_state_and_used[key] = next_cost
            heappush(queue, (next_cost, (*path, action.name), next_state, next_used))

    return tuple(sorted(plans, key=lambda plan: (plan.cost, plan.actions)))


@cache
def _monotone_lure_plans(instance: PlanningInstance) -> tuple[Plan, ...]:
    """Solve the preregistered wrong model: independent add-only operations."""

    best_cost: int | None = None
    plans: list[Plan] = []
    actions = instance.actions
    for size in range(len(actions) + 1):
        for selected in combinations(actions, size):
            state = instance.initial | frozenset().union(*(action.adds for action in selected))
            if not instance.goal_present <= state:
                continue
            cost = sum(action.cost for action in selected)
            ordered = tuple(
                action.name
                for action in sorted(selected, key=lambda action: _identifier_key(action.name))
            )
            plan = Plan(cost=cost, actions=ordered, final_state=state)
            if best_cost is None or cost < best_cost:
                best_cost = cost
                plans = [plan]
            elif cost == best_cost:
                plans.append(plan)
    return tuple(sorted(plans, key=lambda plan: plan.actions))


def _identifier_key(identifier: str) -> tuple[str, int]:
    match = re.fullmatch(r"([A-Za-z]+)(\d+)", identifier)
    if match is None:
        raise ValueError(f"invalid action identifier: {identifier}")
    return match.group(1), int(match.group(2))


def _format_plan(plan: Plan) -> str:
    return ";".join((str(plan.cost), *plan.actions))


_ACTION_PATTERN = re.compile(
    r"([A-Za-z]+\d+)\[(\d+)\]:"
    r"需=([A-Za-z0-9,]+|-);"
    r"禁=([A-Za-z0-9,]+|-);"
    r"置=([A-Za-z0-9,]+|-);"
    r"清=([A-Za-z0-9,]+|-)"
)
_CARD_PATTERN = re.compile(
    r"([A-Za-z]+\d+)（费用(\d+)）只有 ([A-Za-z0-9,]+|无) 都已登记且 "
    r"([A-Za-z0-9,]+|无) 均未登记时可用；"
    r"用后登记 ([A-Za-z0-9,]+|无)，并注销 ([A-Za-z0-9,]+|无)"
)


def _card_tokens(raw: str) -> frozenset[str]:
    return frozenset() if raw == "无" else frozenset(raw.split(","))


def _parse_instance(problem: str) -> PlanningInstance:
    initial_match = re.search(r"初态=([A-Za-z0-9,]+|-);", problem)
    goal_match = re.search(r"终态必须含=([A-Za-z0-9,]+|-);不得含=([A-Za-z0-9,]+|-)", problem)
    if initial_match is not None and goal_match is not None:
        try:
            action_section = problem.split("操作表：", 1)[1].split("求最低", 1)[0]
        except IndexError as exc:
            raise ValueError("planning problem is missing its active action table") from exc
        actions = tuple(
            Action(
                name=name,
                cost=int(cost),
                requires=_tokens(requires),
                forbids=_tokens(forbids),
                adds=_tokens(adds),
                clears=_tokens(clears),
            )
            for name, cost, requires, forbids, adds, clears in _ACTION_PATTERN.findall(
                action_section
            )
        )
        initial = _tokens(initial_match.group(1))
        goal_present = _tokens(goal_match.group(1))
        goal_absent = _tokens(goal_match.group(2))
    else:
        initial_match = re.search(r"初始登记=([A-Za-z0-9,]+|无);", problem)
        goal_match = re.search(
            r"验收须有=([A-Za-z0-9,]+|无);须无=([A-Za-z0-9,]+|无)",
            problem,
        )
        if initial_match is None or goal_match is None:
            raise ValueError("planning problem is missing its initial or goal state")
        try:
            action_section = problem.split("操作卡：", 1)[1].split("求最低", 1)[0]
        except IndexError as exc:
            raise ValueError("planning problem is missing its active action cards") from exc
        actions = tuple(
            Action(
                name=name,
                cost=int(cost),
                requires=_card_tokens(requires),
                forbids=_card_tokens(forbids),
                adds=_card_tokens(adds),
                clears=_card_tokens(clears),
            )
            for name, cost, requires, forbids, adds, clears in _CARD_PATTERN.findall(action_section)
        )
        initial = _card_tokens(initial_match.group(1))
        goal_present = _card_tokens(goal_match.group(1))
        goal_absent = _card_tokens(goal_match.group(2))
    if not actions:
        raise ValueError("planning problem contains no parseable actions")
    if len({action.name for action in actions}) != len(actions):
        raise ValueError("planning problem contains duplicate action identifiers")
    return PlanningInstance(
        initial=initial,
        goal_present=goal_present,
        goal_absent=goal_absent,
        actions=actions,
    )


def _source_instance() -> PlanningInstance:
    return PlanningInstance(
        initial=frozenset({"A", "B", "C"}),
        goal_present=frozenset({"B", "I", "J"}),
        goal_absent=frozenset({"A", "D", "E"}),
        actions=(
            _action("S1", 2, requires="B", adds="D", clears="C"),
            _action("S2", 2, requires="A", adds="E", clears="B"),
            _action("S3", 3, requires="D,E", adds="F", clears="A"),
            _action("S4", 2, requires="F", adds="G", clears="D"),
            _action("S5", 2, requires="G", forbids="D", adds="H", clears="E"),
            _action("S6", 2, requires="H", adds="I", clears="G"),
            _action("S7", 1, requires="I", adds="J"),
            _action("S8", 1, requires="J", adds="B"),
            _action("S9", 7, requires="A", adds="D,E", clears="C"),
            _action("S10", 7, requires="F", adds="G,I", clears="B,D,E"),
            _action(
                "S11",
                6,
                requires="G",
                forbids="D",
                adds="I,J",
                clears="B,E",
            ),
            _action("S12", 4, requires="I", adds="B", clears="J"),
            _action("S13", 4, requires="J", adds="B,I"),
            _action("S14", 5, requires="F", adds="H", clears="A,B,D,E"),
            _action("S15", 8, requires="A", adds="F,D", clears="B,C"),
            _action("S16", 5, requires="H", adds="B,J", clears="G,I"),
        ),
    )


def _target_l0() -> PlanningInstance:
    return PlanningInstance(
        initial=frozenset({"x"}),
        goal_present=frozenset({"z"}),
        goal_absent=frozenset(),
        actions=(
            _action("A1", 1, requires="x", adds="y"),
            _action("A2", 1, requires="y", adds="z"),
            _action("A3", 3, requires="x", adds="z"),
        ),
    )


def _target_l1() -> PlanningInstance:
    return PlanningInstance(
        initial=frozenset({"a", "b"}),
        goal_present=frozenset({"b", "e"}),
        goal_absent=frozenset(),
        actions=(
            _action("B3", 2, requires="e", adds="b"),
            _action("B1", 1, requires="a", adds="c", clears="b"),
            _action("B4", 5, requires="a", adds="e"),
            _action("B2", 1, requires="c", adds="e"),
        ),
    )


def _target_l2() -> PlanningInstance:
    return PlanningInstance(
        initial=frozenset({"a", "b"}),
        goal_present=frozenset({"b", "g", "h"}),
        goal_absent=frozenset({"a", "d"}),
        actions=(
            _action("C8", 4, requires="g", adds="b"),
            _action("C2", 2, requires="b", adds="d"),
            _action("C5", 2, requires="f", forbids="d", adds="g"),
            _action("C1", 2, requires="a", adds="c", clears="b"),
            _action("C7", 1, requires="h", adds="b"),
            _action("C4", 1, requires="e", adds="f", clears="d"),
            _action("C9", 7, requires="a", adds="c,d"),
            _action("C6", 1, requires="g", adds="h"),
            _action("C3", 2, requires="c,d", adds="e", clears="a"),
        ),
    )


FEATURE_RENAME = {
    "A": "q",
    "B": "v",
    "C": "p",
    "D": "t",
    "E": "w",
    "F": "r",
    "G": "u",
    "H": "s",
    "I": "x",
    "J": "y",
}
ACTION_RENAME = {
    "S1": "K7",
    "S2": "K2",
    "S3": "K10",
    "S4": "K4",
    "S5": "K9",
    "S6": "K1",
    "S7": "K6",
    "S8": "K3",
    "S9": "K8",
    "S10": "K5",
    "S11": "K11",
    "S12": "K12",
    "S13": "K13",
    "S14": "K14",
    "S15": "K15",
    "S16": "K16",
}


def _rename_action(action: Action) -> Action:
    def renamed(values: frozenset[str]) -> frozenset[str]:
        return frozenset(FEATURE_RENAME[value] for value in values)

    return Action(
        name=ACTION_RENAME[action.name],
        cost=action.cost,
        requires=renamed(action.requires),
        forbids=renamed(action.forbids),
        adds=renamed(action.adds),
        clears=renamed(action.clears),
    )


def _target_full(*, edited: bool) -> PlanningInstance:
    by_name = {action.name: action for action in map(_rename_action, _source_instance().actions)}
    if edited:
        old = by_name["K3"]
        by_name["K3"] = Action(
            name=old.name,
            cost=old.cost,
            requires=old.requires,
            forbids=old.forbids,
            adds=frozenset({"p"}),
            clears=old.clears,
        )
    shuffled_order = (
        "K13",
        "K5",
        "K2",
        "K16",
        "K9",
        "K7",
        "K12",
        "K3",
        "K11",
        "K1",
        "K15",
        "K6",
        "K8",
        "K4",
        "K14",
        "K10",
    )
    return PlanningInstance(
        initial=frozenset({"q", "v", "p"}),
        goal_present=frozenset({"v", "x", "y"}),
        goal_absent=frozenset({"q", "t", "w"}),
        actions=tuple(by_name[name] for name in shuffled_order),
    )


def _verify_case(
    case: Case,
    *,
    expected_instance: PlanningInstance,
    expected_plan: Plan,
    expected_lure: Plan,
) -> VerificationResult:
    parsed_source = _parse_instance(case.source.problem)
    parsed_target = _parse_instance(case.target.problem)
    source_plans = _best_plans(_source_instance())
    target_plans = _best_plans(expected_instance)
    lure_plans = _monotone_lure_plans(expected_instance)
    expected_source_plan = Plan(
        15,
        ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"),
        frozenset({"B", "F", "H", "I", "J"}),
    )
    checks = [
        _check("source-text-instance", parsed_source, _source_instance()),
        _check("source-unique-optimum", source_plans, (expected_source_plan,)),
        _check("stored-source-answer", case.source.answer, _format_plan(source_plans[0])),
        _check("target-text-instance", parsed_target, expected_instance),
        _check("target-unique-optimum", target_plans, (expected_plan,)),
        _check("lure-unique-optimum", lure_plans, (expected_lure,)),
        _check("stored-target", _gold(case), _format_plan(expected_plan)),
        _check("stored-lure", _lure(case), _format_plan(expected_lure)),
        _check("copy-equals-lure", _copy(case), _lure(case)),
        _check("copy-differs-from-target", _copy(case) != _gold(case), True),
    ]
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


@register("FORMAL-P5-PLAN-L0-01")
def verify_formal_p5_plan_l0_01(case: Case) -> VerificationResult:
    return _verify_case(
        case,
        expected_instance=_target_l0(),
        expected_plan=Plan(2, ("A1", "A2"), frozenset({"x", "y", "z"})),
        expected_lure=Plan(1, ("A2",), frozenset({"x", "z"})),
    )


@register("FORMAL-P5-PLAN-L1-01")
def verify_formal_p5_plan_l1_01(case: Case) -> VerificationResult:
    return _verify_case(
        case,
        expected_instance=_target_l1(),
        expected_plan=Plan(4, ("B1", "B2", "B3"), frozenset({"a", "b", "c", "e"})),
        expected_lure=Plan(1, ("B2",), frozenset({"a", "b", "e"})),
    )


@register("FORMAL-P5-PLAN-L2-01")
def verify_formal_p5_plan_l2_01(case: Case) -> VerificationResult:
    return _verify_case(
        case,
        expected_instance=_target_l2(),
        expected_plan=Plan(
            11,
            ("C2", "C1", "C3", "C4", "C5", "C6", "C7"),
            frozenset({"b", "c", "e", "f", "g", "h"}),
        ),
        expected_lure=Plan(3, ("C5", "C6"), frozenset({"a", "b", "g", "h"})),
    )


def _verify_full(case: Case, *, edited: bool) -> VerificationResult:
    expected = _target_full(edited=edited)
    expected_plan = (
        Plan(
            17,
            ("K8", "K10", "K4", "K9", "K1", "K6"),
            frozenset({"v", "r", "s", "x", "y"}),
        )
        if edited
        else Plan(
            15,
            ("K7", "K2", "K10", "K4", "K9", "K1", "K6", "K3"),
            frozenset({"v", "r", "s", "x", "y"}),
        )
    )
    result = _verify_case(
        case,
        expected_instance=expected,
        expected_plan=expected_plan,
        expected_lure=Plan(
            3,
            ("K1", "K6"),
            frozenset({"q", "v", "p", "x", "y"}),
        ),
    )

    renamed_source = tuple(_rename_action(action) for action in _source_instance().actions)
    expected_by_name = {action.name: action for action in expected.actions}
    mismatches = {
        action.name: (action, expected_by_name[action.name])
        for action in renamed_source
        if action != expected_by_name[action.name]
    }
    near_plans = _best_plans(expected, max_extra_cost=1)
    near_costs = sorted({plan.cost for plan in near_plans})
    result.checks.append(
        _check(
            "one-cost-runner-up-margin",
            near_costs,
            [expected_plan.cost, expected_plan.cost + 1],
        )
    )
    if edited:
        old, new = mismatches["K3"]
        edit_signature = (old.adds, new.adds)
        old_plan = ("K7", "K2", "K10", "K4", "K9", "K1", "K6", "K3")
        result.checks.extend(
            [
                _check("single-broken-action", set(mismatches), {"K3"}),
                _check("single-effect-edit", edit_signature, (frozenset({"v"}), frozenset({"p"}))),
                _check(
                    "old-renamed-plan-is-not-goal",
                    _replay(expected, old_plan)[0],
                    False,
                ),
            ]
        )
    else:
        source = _source_instance()
        result.checks.extend(
            [
                _check("complete-action-isomorphism", mismatches, {}),
                _check(
                    "feature-isomorphism-initial",
                    expected.initial,
                    frozenset(FEATURE_RENAME[value] for value in source.initial),
                ),
                _check(
                    "feature-isomorphism-positive-goal",
                    expected.goal_present,
                    frozenset(FEATURE_RENAME[value] for value in source.goal_present),
                ),
                _check(
                    "feature-isomorphism-negative-goal",
                    expected.goal_absent,
                    frozenset(FEATURE_RENAME[value] for value in source.goal_absent),
                ),
            ]
        )
    return result


def _replay(instance: PlanningInstance, path: tuple[str, ...]) -> tuple[bool, frozenset[str]]:
    by_name = {action.name: action for action in instance.actions}
    state = instance.initial
    used: set[str] = set()
    for name in path:
        action = by_name[name]
        if name in used or not action.requires <= state or action.forbids & state:
            return False, state
        used.add(name)
        state = (state - action.clears) | action.adds
    return _goal(instance, state), state


@register("FORMAL-P5-PLAN-L3-01")
def verify_formal_p5_plan_l3_01(case: Case) -> VerificationResult:
    return _verify_full(case, edited=False)


@register("FORMAL-P5-PLAN-L4-01")
def verify_formal_p5_plan_l4_01(case: Case) -> VerificationResult:
    return _verify_full(case, edited=True)
