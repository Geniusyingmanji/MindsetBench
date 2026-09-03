from __future__ import annotations

from collections.abc import Mapping, Sequence

from mindsetbench.models.case import Case
from mindsetbench.verification.argument_evidence import (
    ClaimAssessment,
    EvidenceNode,
    Stance,
    assess_claims,
    surface_document_assessments,
    verdict_parts,
)
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register


def _origin(node_id: str) -> EvidenceNode:
    return EvidenceNode(node_id)


def _report(
    node_id: str,
    claim: str,
    stance: Stance,
    *parents: str,
) -> EvidenceNode:
    return EvidenceNode(node_id, parents, claim, stance)


def _graph(*nodes: EvidenceNode) -> dict[str, EvidenceNode]:
    graph = {node.node_id: node for node in nodes}
    if len(graph) != len(nodes):
        raise ValueError("duplicate evidence node id")
    return graph


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


def _contains_all(text: str, phrases: Sequence[str]) -> bool:
    return all(phrase in text for phrase in phrases)


def _answer(assessments: Mapping[str, ClaimAssessment], claims: Sequence[str]) -> str:
    return ";".join(verdict_parts(assessments, claims))


SOURCE_CLAIMS = ("A", "B", "C", "D")
SOURCE_INVALID_ROOTS = {"O11"}
SOURCE_REQUIRED_PHRASES = (
    "追溯到最初的一手记录",
    "转引、摘录或改写同一一手记录只算一个来源",
    "支持侧和反对侧分别至少需要两个独立来源",
    "真实性警报会使该一手记录及其全部转引失效",
)


def _source_graph() -> dict[str, EvidenceNode]:
    return _graph(
        _origin("O1"),
        _report("A1", "A", Stance.SUPPORT, "O1"),
        _report("A2", "A", Stance.SUPPORT, "A1"),
        _origin("O2"),
        _report("A3", "A", Stance.SUPPORT, "O2"),
        _origin("O3"),
        _report("B1", "B", Stance.SUPPORT, "O3"),
        _report("B2", "B", Stance.SUPPORT, "B1"),
        _report("B3", "B", Stance.SUPPORT, "B2"),
        _origin("O4"),
        _report("B4", "B", Stance.OPPOSE, "O4"),
        _origin("O5"),
        _report("B5", "B", Stance.OPPOSE, "O5"),
        _origin("O6"),
        _report("C1", "C", Stance.SUPPORT, "O6"),
        _origin("O7"),
        _report("C2", "C", Stance.SUPPORT, "O7"),
        _origin("O8"),
        _report("C3", "C", Stance.OPPOSE, "O8"),
        _origin("O9"),
        _report("C4", "C", Stance.OPPOSE, "O9"),
        _origin("O10"),
        _report("D1", "D", Stance.SUPPORT, "O10"),
        _origin("O11"),
        _report("D2", "D", Stance.SUPPORT, "O11"),
    )


def _source_checks(case: Case) -> list[VerificationCheck]:
    assessments = assess_claims(
        _source_graph(),
        SOURCE_CLAIMS,
        invalid_roots=SOURCE_INVALID_ROOTS,
    )
    parts = verdict_parts(assessments, SOURCE_CLAIMS)
    return [
        _check(
            "source-text-defines-provenance-policy",
            _contains_all(case.source.problem, SOURCE_REQUIRED_PHRASES),
            True,
        ),
        _check(
            "source-verdicts",
            parts,
            [
                "A=SUPPORTED",
                "B=REJECTED",
                "C=CONTESTED",
                "D=UNCORROBORATED",
            ],
        ),
        _check("stored-source", case.source.answer, ";".join(parts)),
    ]


def _verify_case(
    case: Case,
    *,
    graph: Mapping[str, EvidenceNode],
    claims: Sequence[str],
    required_phrases: Sequence[str],
    expected_target: Sequence[str],
    expected_lure: Sequence[str],
    invalid_roots: Sequence[str] = (),
    independence_groups: Mapping[str, str] | None = None,
    lure_assessments: Mapping[str, ClaimAssessment] | None = None,
) -> VerificationResult:
    target = assess_claims(
        graph,
        claims,
        invalid_roots=invalid_roots,
        independence_groups=independence_groups,
    )
    lure = lure_assessments or surface_document_assessments(graph, claims)
    target_parts = verdict_parts(target, claims)
    lure_parts = verdict_parts(lure, claims)
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None
    checks = _source_checks(case)
    checks.extend(
        [
            _check(
                "target-text-provenance-facts",
                _contains_all(case.target.problem, required_phrases),
                True,
            ),
            _check("target-verdicts", target_parts, list(expected_target)),
            _check("negative-control-verdicts", lure_parts, list(expected_lure)),
            _check("stored-target", case.target.answer.legacy_value(), _answer(target, claims)),
            _check("stored-lure", case.lure.answer.legacy_value(), _answer(lure, claims)),
            _check(
                "copy-equals-lure",
                case.copy_probe.answer.legacy_value(),
                case.lure.answer.legacy_value(),
            ),
            _check(
                "copy-differs-from-target",
                case.copy_probe.answer != case.target.answer,
                True,
            ),
        ]
    )
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


@register("HSS-P7-ARG-EVIDENCE-L0-01")
def verify_hss_p7_arg_evidence_l0_01(case: Case) -> VerificationResult:
    graph = _graph(
        _origin("O1"),
        _report("E1", "X", Stance.SUPPORT, "O1"),
        _report("E2", "X", Stance.SUPPORT, "E1"),
        _report("E3", "X", Stance.SUPPORT, "E2"),
    )
    return _verify_case(
        case,
        graph=graph,
        claims=("X",),
        required_phrases=(
            "E1 直接整理自原始日志 O1",
            "E2 只转引 E1",
            "E3 又只摘录 E2",
        ),
        expected_target=("X=UNCORROBORATED",),
        expected_lure=("X=SUPPORTED",),
    )


@register("HSS-P7-ARG-EVIDENCE-L1-01")
def verify_hss_p7_arg_evidence_l1_01(case: Case) -> VerificationResult:
    graph = _graph(
        _origin("O1"),
        _report("E1", "H1", Stance.SUPPORT, "O1"),
        _report("E2", "H1", Stance.SUPPORT, "E1"),
        _origin("O2"),
        _report("E3", "H1", Stance.SUPPORT, "O2"),
        _origin("O3"),
        _report("F1", "H2", Stance.SUPPORT, "O3"),
        _report("F2", "H2", Stance.SUPPORT, "F1"),
        _report("F3", "H2", Stance.SUPPORT, "F2"),
        _origin("O4"),
        _report("F4", "H2", Stance.OPPOSE, "O4"),
        _origin("O5"),
        _report("F5", "H2", Stance.OPPOSE, "O5"),
    )
    return _verify_case(
        case,
        graph=graph,
        claims=("H1", "H2"),
        required_phrases=(
            "E2 改写 E1",
            "E3 来自独立检查 O2",
            "F1、F2、F3 最终都来自 O3",
            "F4 与 F5 分别来自 O4、O5",
        ),
        expected_target=("H1=SUPPORTED", "H2=REJECTED"),
        expected_lure=("H1=SUPPORTED", "H2=CONTESTED"),
    )


@register("HSS-P7-ARG-EVIDENCE-L2-01")
def verify_hss_p7_arg_evidence_l2_01(case: Case) -> VerificationResult:
    graph = _graph(
        _origin("P1"),
        _report("J1A", "J1", Stance.SUPPORT, "P1"),
        _report("J1B", "J1", Stance.SUPPORT, "J1A"),
        _origin("P2"),
        _report("J1C", "J1", Stance.SUPPORT, "P2"),
        _origin("P3"),
        _report("J2A", "J2", Stance.SUPPORT, "P3"),
        _report("J2B", "J2", Stance.SUPPORT, "J2A"),
        _report("J2C", "J2", Stance.SUPPORT, "J2B"),
        _origin("P4"),
        _report("J2D", "J2", Stance.OPPOSE, "P4"),
        _origin("P5"),
        _report("J2E", "J2", Stance.OPPOSE, "P5"),
        _origin("P6"),
        _report("J3A", "J3", Stance.SUPPORT, "P6"),
        _origin("P7"),
        _report("J3B", "J3", Stance.SUPPORT, "P7"),
        _origin("P8"),
        _report("J3C", "J3", Stance.OPPOSE, "P8"),
        _origin("P9"),
        _report("J3D", "J3", Stance.OPPOSE, "P9"),
    )
    return _verify_case(
        case,
        graph=graph,
        claims=("J1", "J2", "J3"),
        invalid_roots=("P2",),
        required_phrases=(
            "J1B 转述 J1A",
            "真实性核验判定 P2 经过伪造",
            "J2A、J2B、J2C 都追溯到同一匿名帖子 P3",
            "J2D、J2E 分别依据互不相干的 P4、P5",
            "关于 J3，两项支持和两项反对各自来自四个互不相干的来源",
        ),
        expected_target=(
            "J1=UNCORROBORATED",
            "J2=REJECTED",
            "J3=CONTESTED",
        ),
        expected_lure=("J1=SUPPORTED", "J2=CONTESTED", "J3=CONTESTED"),
    )


@register("HSS-P7-ARG-EVIDENCE-L3-01")
def verify_hss_p7_arg_evidence_l3_01(case: Case) -> VerificationResult:
    graph = _graph(
        _origin("O1"),
        _report("A1", "A", Stance.SUPPORT, "O1"),
        _report("A2", "A", Stance.SUPPORT, "A1"),
        _report("A3", "A", Stance.SUPPORT, "A2"),
        _origin("O2"),
        _report("A4", "A", Stance.SUPPORT, "O2"),
        _origin("O3"),
        _report("B1", "B", Stance.SUPPORT, "O3"),
        _report("B2", "B", Stance.SUPPORT, "B1"),
        _report("B3", "B", Stance.SUPPORT, "B2"),
        _origin("O4"),
        _report("B4", "B", Stance.OPPOSE, "O4"),
        _origin("O5"),
        _report("B5", "B", Stance.OPPOSE, "O5"),
        _origin("O6"),
        _report("C1", "C", Stance.SUPPORT, "O6"),
        _origin("O7"),
        _report("C2", "C", Stance.SUPPORT, "O7"),
        _origin("O8"),
        _report("C3", "C", Stance.OPPOSE, "O8"),
        _origin("O9"),
        _report("C4", "C", Stance.OPPOSE, "O9"),
        _origin("O10"),
        _report("D1", "D", Stance.SUPPORT, "O10"),
        _origin("O11"),
        _report("D2", "D", Stance.SUPPORT, "O11"),
    )
    return _verify_case(
        case,
        graph=graph,
        claims=("A", "B", "C", "D"),
        invalid_roots=("O11",),
        required_phrases=(
            "展签 A2 抄自图录 A1，新闻稿 A3 又抄自 A2",
            "海关底册 A4 来自另一档案 O2",
            "三份所有权支持材料最终都来自同一本失踪笔记 O3",
            "两份反证分别来自税册 O4 和保险清单 O5",
            "鉴定警报认定印章底片 O11 不真实",
        ),
        expected_target=(
            "A=SUPPORTED",
            "B=REJECTED",
            "C=CONTESTED",
            "D=UNCORROBORATED",
        ),
        expected_lure=(
            "A=SUPPORTED",
            "B=CONTESTED",
            "C=CONTESTED",
            "D=SUPPORTED",
        ),
    )


@register("HSS-P7-ARG-EVIDENCE-L4-01")
def verify_hss_p7_arg_evidence_l4_01(case: Case) -> VerificationResult:
    graph = _graph(
        _origin("A0"),
        _report("A1", "H1", Stance.SUPPORT, "A0"),
        _report("A2", "H1", Stance.SUPPORT, "A1"),
        _origin("A3"),
        _report("A4", "H1", Stance.SUPPORT, "A3"),
        _origin("B0"),
        _report("B1", "H2", Stance.SUPPORT, "B0"),
        _origin("B2"),
        _report("B3", "H2", Stance.SUPPORT, "B2"),
        _origin("B4"),
        _report("B5", "H2", Stance.OPPOSE, "B4"),
        _origin("C0"),
        _report("C1", "H3", Stance.SUPPORT, "C0"),
        _origin("C2"),
        _report("C3", "H3", Stance.SUPPORT, "C2"),
        _origin("C4"),
        _report("C5", "H3", Stance.OPPOSE, "C4"),
        _origin("C6"),
        _report("C7", "H3", Stance.OPPOSE, "C6"),
        _origin("D0"),
        _report("D1", "H4", Stance.SUPPORT, "D0"),
        _origin("D2"),
        _report("D3", "H4", Stance.SUPPORT, "D2"),
    )
    groups = {
        "A0": "shared-briefing",
        "A3": "shared-briefing",
        "D0": "shared-submission",
        "D2": "shared-submission",
    }
    copied_source_logic = assess_claims(graph, ("H1", "H2", "H3", "H4"))
    return _verify_case(
        case,
        graph=graph,
        claims=("H1", "H2", "H3", "H4"),
        independence_groups=groups,
        lure_assessments=copied_source_logic,
        required_phrases=(
            "日记底稿 A0 与私人信件 A3 都是在同一次编辑简报后形成",
            "打印所账簿 B0 与投递回执 B2 没有共同上游",
            "H3 的两项支持与两项反对分属四个证据家族",
            "印章底片 D0 与登记簿 D2 都由同一份委员会送审包生成",
            "不同文本若由同一次协调性生产过程生成，仍只算一个独立证据家族",
        ),
        expected_target=(
            "H1=UNCORROBORATED",
            "H2=SUPPORTED",
            "H3=CONTESTED",
            "H4=UNCORROBORATED",
        ),
        expected_lure=(
            "H1=SUPPORTED",
            "H2=SUPPORTED",
            "H3=CONTESTED",
            "H4=SUPPORTED",
        ),
    )
