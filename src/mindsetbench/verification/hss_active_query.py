from __future__ import annotations

from collections.abc import Mapping, Sequence

from mindsetbench.models.case import Case
from mindsetbench.verification.active_query import (
    DiagnosticWorld,
    best_queries,
    decisive_branches,
    encode_active_answer,
)
from mindsetbench.verification.argument_evidence import (
    EvidenceNode,
    Stance,
    assess_claims,
    surface_document_assessments,
)
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.institutional_mechanism import (
    MechanismCase,
    classify_mechanism,
)
from mindsetbench.verification.norm_priority import Decision, PriorityRule, decide
from mindsetbench.verification.registry import register
from mindsetbench.verification.role_mapping import RelationalGraph, evaluate_mapping

QUERY_IDS = ("Q1", "Q2", "Q3", "Q4")
TWO_OBSERVATIONS = ("RED", "BLUE")
FOUR_OBSERVATIONS = ("RED", "BLUE", "GREEN", "GOLD")


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


def _contains_all(text: str, phrases: Sequence[str]) -> bool:
    return all(phrase in text for phrase in phrases)


def _worlds(
    outcomes: Sequence[str],
    observations_by_query: Mapping[str, Sequence[str]],
) -> tuple[DiagnosticWorld, ...]:
    if any(len(observations) != len(outcomes) for observations in observations_by_query.values()):
        raise ValueError("every query must predict one observation per world")
    return tuple(
        DiagnosticWorld(
            world_id=f"W{index + 1}",
            outcome=outcome,
            observations=tuple(
                (query_id, observations_by_query[query_id][index]) for query_id in QUERY_IDS
            ),
        )
        for index, outcome in enumerate(outcomes)
    )


def _active_answer(
    worlds: Sequence[DiagnosticWorld],
    observation_order: Sequence[str],
) -> tuple[str, str, dict[str, object]]:
    winners = best_queries(worlds, QUERY_IDS)
    if len(winners) != 1:
        raise ValueError(f"active query is not unique: {[winner.query_id for winner in winners]}")
    winner = winners[0]
    branches = decisive_branches(worlds, winner.query_id)
    answer = encode_active_answer(
        winner.query_id,
        branches,
        observation_order=observation_order,
    )
    diagnostics: dict[str, object] = {
        "query": winner.query_id,
        "worst_outcome_ambiguity": winner.worst_outcome_ambiguity,
        "branches": branches,
    }
    return winner.query_id, answer, diagnostics


def _verify_active_case(
    case: Case,
    *,
    target_worlds: Sequence[DiagnosticWorld],
    lure_worlds: Sequence[DiagnosticWorld],
    observation_order: Sequence[str],
    expected_target_query: str,
    expected_lure_query: str,
    required_phrases: Sequence[str],
    source_answer: str,
    source_phrases: Sequence[str],
) -> VerificationResult:
    target_query, target_answer, target_diagnostics = _active_answer(
        target_worlds, observation_order
    )
    lure_query, lure_answer, lure_diagnostics = _active_answer(lure_worlds, observation_order)
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None
    checks = [
        _check("source-text-schema", _contains_all(case.source.problem, source_phrases), True),
        _check("stored-source", case.source.answer, source_answer),
        _check(
            "target-text-active-query",
            _contains_all(case.target.problem, required_phrases),
            True,
        ),
        _check("target-best-query", target_query, expected_target_query),
        _check("target-query-is-decisive", target_diagnostics["worst_outcome_ambiguity"], 1),
        _check("lure-best-query", lure_query, expected_lure_query),
        _check("lure-query-is-decisive", lure_diagnostics["worst_outcome_ambiguity"], 1),
        _check("stored-target", case.target.answer.legacy_value(), target_answer),
        _check("stored-lure", case.lure.answer.legacy_value(), lure_answer),
        _check("copy-equals-lure", case.copy_probe.answer.legacy_value(), lure_answer),
        _check("copy-differs-from-target", case.copy_probe.answer != case.target.answer, True),
    ]
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


def _p4_outcomes(*, unrestricted_pair: bool) -> list[str]:
    left, right, bar, ex_left, ex_right, final, pardon = (
        "left",
        "right",
        "bar",
        "ex_left",
        "ex_right",
        "final",
        "pardon",
    )
    rules = (
        PriorityRule("base", frozenset({left, right}), Decision.ALLOW, 1),
        PriorityRule("bar", frozenset({bar}), Decision.DENY, 2),
        PriorityRule(
            "pair",
            frozenset({ex_left, ex_right}),
            Decision.ALLOW,
            6 if unrestricted_pair else 3,
        ),
        PriorityRule("final", frozenset({final}), Decision.DENY, 4),
        PriorityRule("pardon", frozenset({final, pardon}), Decision.ALLOW, 5),
    )
    records = (
        {left, right, bar, ex_left, ex_right},
        {left, right, bar},
        {left, right, bar, ex_left, ex_right, final},
        {left, right},
        {left, right, bar, ex_left, ex_right, final, pardon},
        {left},
    )
    return [decide(record, rules).decision.value.upper() for record in records]


@register("HSS-ACTIVE-P4-NORM-L4-01")
def verify_hss_active_p4_norm_l4_01(case: Case) -> VerificationResult:
    observations = {
        "Q1": ("RED", "RED", "RED", "BLUE", "BLUE", "BLUE"),
        "Q2": ("RED", "BLUE", "RED", "RED", "RED", "BLUE"),
        "Q3": ("RED", "BLUE", "BLUE", "RED", "RED", "BLUE"),
        "Q4": ("RED", "BLUE", "GREEN", "BLUE", "GREEN", "RED"),
    }
    return _verify_active_case(
        case,
        target_worlds=_worlds(_p4_outcomes(unrestricted_pair=False), observations),
        lure_worlds=_worlds(_p4_outcomes(unrestricted_pair=True), observations),
        observation_order=TWO_OBSERVATIONS,
        expected_target_query="Q3",
        expected_lure_query="Q2",
        required_phrases=("松卷", "雪卷", "Q1", "Q4", "最坏情况下"),
        source_answer="T2;T4;T5",
        source_phrases=("事故审查条款优先", "双重批准例外优先", "法律保全条款优先"),
    )


def _evidence_verdict(
    support_documents: int,
    support_groups: int,
    oppose_documents: int,
    oppose_groups: int,
    *,
    surface_count: bool,
) -> str:
    nodes: dict[str, EvidenceNode] = {}

    def add_side(prefix: str, documents: int, groups: int, stance: Stance) -> None:
        for group_index in range(groups):
            root = f"{prefix}O{group_index + 1}"
            nodes[root] = EvidenceNode(root)
        for document_index in range(documents):
            root = f"{prefix}O{document_index % groups + 1}"
            report = f"{prefix}D{document_index + 1}"
            nodes[report] = EvidenceNode(report, (root,), "H", stance)

    add_side("S", support_documents, support_groups, Stance.SUPPORT)
    add_side("O", oppose_documents, oppose_groups, Stance.OPPOSE)
    assessments = (
        surface_document_assessments(nodes, ("H",))
        if surface_count
        else assess_claims(nodes, ("H",))
    )
    return assessments["H"].verdict.value


def _p7_outcomes(*, surface_count: bool) -> list[str]:
    configurations = (
        (3, 2, 0, 0),
        (3, 1, 0, 0),
        (2, 2, 2, 2),
        (3, 1, 2, 2),
        (2, 2, 3, 1),
        (3, 1, 3, 1),
    )
    return [
        _evidence_verdict(*configuration, surface_count=surface_count)
        for configuration in configurations
    ]


@register("HSS-ACTIVE-P7-PROVENANCE-L4-01")
def verify_hss_active_p7_provenance_l4_01(case: Case) -> VerificationResult:
    observations = {
        "Q1": ("RED", "RED", "RED", "BLUE", "BLUE", "BLUE"),
        "Q2": ("RED", "RED", "BLUE", "BLUE", "GREEN", "GOLD"),
        "Q3": ("RED", "BLUE", "GREEN", "GOLD", "RED", "BLUE"),
        "Q4": ("RED", "BLUE", "GREEN", "RED", "BLUE", "GREEN"),
    }
    return _verify_active_case(
        case,
        target_worlds=_worlds(_p7_outcomes(surface_count=False), observations),
        lure_worlds=_worlds(_p7_outcomes(surface_count=True), observations),
        observation_order=FOUR_OBSERVATIONS,
        expected_target_query="Q3",
        expected_lure_query="Q2",
        required_phrases=("潮谱", "雪谱", "呈现材料数", "独立底本家族数", "Q4"),
        source_answer="A=SUPPORTED;B=REJECTED;C=CONTESTED;D=UNCORROBORATED",
        source_phrases=("追溯到最初的一手记录", "只算一个来源", "全部转引失效"),
    )


SOURCE_ROLE_GRAPH = RelationalGraph(
    frozenset({"O", "G", "P", "R", "B"}),
    frozenset(
        {
            ("O", "informs", "G"),
            ("G", "restrains", "P"),
            ("P", "harms", "R"),
            ("R", "sustains", "B"),
            ("G", "protects", "R"),
        }
    ),
)


def _p6_fatal(*, reverse_control: bool, finance_only: bool = False) -> str:
    edges = {
        ("O", "informs", "G"),
        ("P", "harms", "R"),
        ("R", "sustains", "B"),
        ("G", "protects", "R"),
    }
    if reverse_control:
        edges.add(("P", "controls", "G"))
    else:
        edges.add(("G", "restrains", "P"))
    if finance_only:
        edges.add(("P", "finances", "G"))
    graph = RelationalGraph(SOURCE_ROLE_GRAPH.nodes, frozenset(edges))
    match = evaluate_mapping(
        SOURCE_ROLE_GRAPH,
        graph,
        {role: role for role in SOURCE_ROLE_GRAPH.nodes},
        {relation: relation for _, relation, _ in SOURCE_ROLE_GRAPH.edges},
    )
    if not match.missing_edges:
        return "NONE"
    if match.added_induced_edges == {("P", "controls", "G")}:
        return "P-CONTROLS-G"
    raise ValueError(f"unsupported role-graph difference: {match}")


def _p6_outcomes(*, treat_finance_as_control: bool) -> list[str]:
    configurations = (
        (False, False),
        (True, False),
        (True, False),
        (False, False),
        (False, True),
        (True, False),
    )
    return [
        _p6_fatal(
            reverse_control=reverse_control or (treat_finance_as_control and finance_only),
            finance_only=finance_only and not treat_finance_as_control,
        )
        for reverse_control, finance_only in configurations
    ]


@register("HSS-ACTIVE-P6-NARRATIVE-L4-01")
def verify_hss_active_p6_narrative_l4_01(case: Case) -> VerificationResult:
    observations = {
        "Q1": ("RED", "RED", "RED", "BLUE", "BLUE", "BLUE"),
        "Q2": ("RED", "BLUE", "BLUE", "RED", "BLUE", "BLUE"),
        "Q3": ("RED", "BLUE", "BLUE", "RED", "RED", "BLUE"),
        "Q4": ("RED", "BLUE", "GREEN", "BLUE", "GREEN", "RED"),
    }
    return _verify_active_case(
        case,
        target_worlds=_worlds(_p6_outcomes(treat_finance_as_control=False), observations),
        lure_worlds=_worlds(_p6_outcomes(treat_finance_as_control=True), observations),
        observation_order=TWO_OBSERVATIONS,
        expected_target_query="Q3",
        expected_lure_query="Q2",
        required_phrases=("第一复原本", "第六复原本", "资助关系", "任免多数席位", "Q4"),
        source_answer="O=S;G=C;P=D;R=F;B=V;FATAL=NONE",
        source_phrases=("巡查员 S 向封育委员会 C 报告", "委员会 C 限制", "委员会 C 同时保护"),
    )


def _p8_outcomes(*, visible_form_only: bool) -> list[str]:
    cases = (
        MechanismCase(
            True,
            costly_action=True,
            actor_bears_cost=True,
            committed_type_can_bear=True,
        ),
        MechanismCase(True, removes_defection_option=True),
        MechanismCase(
            True,
            costly_action=True,
            actor_bears_cost=True,
            committed_type_can_bear=True,
            opportunistic_type_can_bear=True,
        ),
        MechanismCase(
            False,
            costly_action=True,
            actor_bears_cost=True,
            committed_type_can_bear=True,
        ),
        MechanismCase(
            True,
            costly_action=True,
            actor_bears_cost=True,
            committed_type_can_bear=True,
            third_party_reimbursement=not visible_form_only,
        ),
        MechanismCase(True, removes_defection_option=visible_form_only),
    )
    return [classify_mechanism(case).value for case in cases]


@register("HSS-ACTIVE-P8-RITUAL-L4-01")
def verify_hss_active_p8_ritual_l4_01(case: Case) -> VerificationResult:
    observations = {
        "Q1": ("RED", "RED", "RED", "BLUE", "BLUE", "BLUE"),
        "Q2": ("RED", "BLUE", "GREEN", "GOLD", "RED", "BLUE"),
        "Q3": ("RED", "BLUE", "GREEN", "GOLD", "GREEN", "GOLD"),
        "Q4": ("RED", "BLUE", "GREEN", "GREEN", "BLUE", "RED"),
    }
    return _verify_active_case(
        case,
        target_worlds=_worlds(_p8_outcomes(visible_form_only=False), observations),
        lure_worlds=_worlds(_p8_outcomes(visible_form_only=True), observations),
        observation_order=FOUR_OBSERVATIONS,
        expected_target_query="Q3",
        expected_lure_query="Q2",
        required_phrases=("六种铭文复原", "第五种", "第六种", "Q1", "Q4"),
        source_answer=(
            "S1=SEPARATING_SIGNAL;S2=CREDIBLE_COMMITMENT;"
            "S3=POOLING_SIGNAL;S4=NONCREDIBLE"
        ),
        source_phrases=("永久删除日后背离选项", "机会主义类型无法承受", "第三方全额补偿"),
    )
