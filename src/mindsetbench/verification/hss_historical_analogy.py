from __future__ import annotations

from collections.abc import Mapping, Sequence

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register
from mindsetbench.verification.role_mapping import (
    Edge,
    MappingMatch,
    RelationalGraph,
    best_mappings,
)

ROLE_ORDER = ("O", "G", "P", "R", "B")
SOURCE_RELATIONS = {
    "informs": "informs",
    "restrains": "restrains",
    "harms": "harms",
    "sustains": "sustains",
    "protects": "protects",
}


def _source_graph() -> RelationalGraph:
    return RelationalGraph(
        frozenset(ROLE_ORDER),
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


def _graph(nodes: set[str], edges: set[Edge]) -> RelationalGraph:
    return RelationalGraph(frozenset(nodes), frozenset(edges))


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


def _contains_all(text: str, phrases: Sequence[str]) -> bool:
    return all(phrase in text for phrase in phrases)


def _encoded(mapping: Mapping[str, str], fatal: str) -> str:
    parts = [f"{role}={mapping[role]}" for role in ROLE_ORDER]
    parts.append(f"FATAL={fatal}")
    return ";".join(parts)


def _unique_best(
    graph: RelationalGraph,
    relation_map: Mapping[str, str],
) -> tuple[list[MappingMatch], MappingMatch | None]:
    matches = best_mappings(_source_graph(), graph, ROLE_ORDER, relation_map)
    return matches, matches[0] if len(matches) == 1 else None


SOURCE_REQUIRED_PHRASES = (
    "巡查员 S 向封育委员会 C 报告",
    "委员会 C 限制盗伐车队 D",
    "盗伐车队 D 破坏幼林带 F",
    "幼林带 F 支撑山麓村 V",
    "委员会 C 同时保护幼林带 F",
)


def _source_checks(case: Case) -> list[VerificationCheck]:
    source_target = _graph(
        {"S", "C", "D", "F", "V"},
        {
            ("S", "informs", "C"),
            ("C", "restrains", "D"),
            ("D", "harms", "F"),
            ("F", "sustains", "V"),
            ("C", "protects", "F"),
        },
    )
    matches, match = _unique_best(source_target, SOURCE_RELATIONS)
    expected = {"O": "S", "G": "C", "P": "D", "R": "F", "B": "V"}
    return [
        _check(
            "source-text-role-relations",
            _contains_all(case.source.problem, SOURCE_REQUIRED_PHRASES),
            True,
        ),
        _check("source-unique-mapping-count", len(matches), 1),
        _check("source-role-mapping", dict(match.mapping) if match else None, expected),
        _check("stored-source", case.source.answer, _encoded(expected, "NONE")),
    ]


def _verify_exact_case(
    case: Case,
    *,
    target: RelationalGraph,
    lure: RelationalGraph,
    relation_map: Mapping[str, str],
    expected_mapping: Mapping[str, str],
    expected_lure_mapping: Mapping[str, str],
    required_phrases: Sequence[str],
) -> VerificationResult:
    target_matches, target_match = _unique_best(target, relation_map)
    lure_matches, lure_match = _unique_best(lure, relation_map)
    target_answer = _encoded(expected_mapping, "NONE")
    lure_answer = _encoded(expected_lure_mapping, "NONE")
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None
    checks = _source_checks(case)
    checks.extend(
        [
            _check(
                "target-text-relations",
                _contains_all(case.target.problem, required_phrases),
                True,
            ),
            _check("target-best-score", target_match.score if target_match else None, 5),
            _check("target-unique-mapping-count", len(target_matches), 1),
            _check(
                "target-role-mapping",
                dict(target_match.mapping) if target_match else None,
                dict(expected_mapping),
            ),
            _check("lure-best-score", lure_match.score if lure_match else None, 5),
            _check("lure-unique-mapping-count", len(lure_matches), 1),
            _check(
                "lure-role-mapping",
                dict(lure_match.mapping) if lure_match else None,
                dict(expected_lure_mapping),
            ),
            _check("stored-target", case.target.answer.legacy_value(), target_answer),
            _check("stored-lure", case.lure.answer.legacy_value(), lure_answer),
            _check("copy-equals-lure", case.copy_probe.answer.legacy_value(), lure_answer),
            _check("copy-differs-from-target", target_answer != lure_answer, True),
        ]
    )
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


@register("HSS-P6-HIST-ANALOGY-L0-01")
def verify_hss_p6_hist_analogy_l0_01(case: Case) -> VerificationResult:
    relation_map = SOURCE_RELATIONS
    target = _graph(
        {"A", "B", "C", "D", "E"},
        {
            ("C", "informs", "A"),
            ("A", "restrains", "E"),
            ("E", "harms", "B"),
            ("B", "sustains", "D"),
            ("A", "protects", "B"),
        },
    )
    lure = _graph(
        {"A", "B", "C", "D", "E"},
        {
            ("A", "informs", "C"),
            ("C", "restrains", "E"),
            ("E", "harms", "B"),
            ("B", "sustains", "D"),
            ("C", "protects", "B"),
        },
    )
    return _verify_exact_case(
        case,
        target=target,
        lure=lure,
        relation_map=relation_map,
        expected_mapping={"O": "C", "G": "A", "P": "E", "R": "B", "B": "D"},
        expected_lure_mapping={"O": "A", "G": "C", "P": "E", "R": "B", "B": "D"},
        required_phrases=(
            "瞭望员 C 向巡护站 A 报告",
            "巡护站 A 限制偷猎船队 E",
            "偷猎船队 E 破坏繁殖地 B",
            "繁殖地 B 支撑渔村 D",
            "巡护站 A 同时保护繁殖地 B",
        ),
    )


@register("HSS-P6-HIST-ANALOGY-L1-01")
def verify_hss_p6_hist_analogy_l1_01(case: Case) -> VerificationResult:
    relation_map = {
        "informs": "alerts",
        "restrains": "contains",
        "harms": "damages",
        "sustains": "supports",
        "protects": "shields",
    }
    target = _graph(
        {"K", "L", "M", "N", "Q"},
        {
            ("K", "alerts", "N"),
            ("N", "contains", "L"),
            ("L", "damages", "Q"),
            ("Q", "supports", "M"),
            ("N", "shields", "Q"),
        },
    )
    lure = _graph(
        {"K", "L", "M", "N", "Q"},
        {
            ("N", "alerts", "K"),
            ("K", "contains", "L"),
            ("L", "damages", "Q"),
            ("Q", "supports", "M"),
            ("K", "shields", "Q"),
        },
    )
    return _verify_exact_case(
        case,
        target=target,
        lure=lure,
        relation_map=relation_map,
        expected_mapping={"O": "K", "G": "N", "P": "L", "R": "Q", "B": "M"},
        expected_lure_mapping={"O": "N", "G": "K", "P": "L", "R": "Q", "B": "M"},
        required_phrases=(
            "遥感台 K 向火场指挥部 N 预警",
            "指挥部 N 遏制火线 L",
            "火线 L 破坏流域 Q",
            "流域 Q 支撑农镇 M",
            "指挥部 N 同时守护流域 Q",
        ),
    )


@register("HSS-P6-HIST-ANALOGY-L2-01")
def verify_hss_p6_hist_analogy_l2_01(case: Case) -> VerificationResult:
    relation_map = {
        "informs": "notifies",
        "restrains": "constrains",
        "harms": "depletes",
        "sustains": "supports",
        "protects": "protects",
    }
    target = _graph(
        {"A", "E", "F", "R", "W"},
        {
            ("W", "notifies", "A"),
            ("A", "constrains", "E"),
            ("E", "depletes", "F"),
            ("F", "supports", "R"),
            ("A", "protects", "F"),
        },
    )
    lure = _graph(
        {"A", "E", "F", "R", "W"},
        {
            ("W", "notifies", "E"),
            ("E", "constrains", "A"),
            ("A", "depletes", "F"),
            ("F", "supports", "R"),
            ("E", "protects", "F"),
        },
    )
    return _verify_exact_case(
        case,
        target=target,
        lure=lure,
        relation_map=relation_map,
        expected_mapping={"O": "W", "G": "A", "P": "E", "R": "F", "B": "R"},
        expected_lure_mapping={"O": "W", "G": "E", "P": "A", "R": "F", "B": "R"},
        required_phrases=(
            "举报人 W 通知审计委员会 A",
            "委员会 A 约束抽取部门 E",
            "抽取部门 E 消耗养老池 F",
            "养老池 F 支撑退休者 R",
            "委员会 A 同时保护养老池 F",
        ),
    )


@register("HSS-P6-HIST-ANALOGY-L3-01")
def verify_hss_p6_hist_analogy_l3_01(case: Case) -> VerificationResult:
    relation_map = {
        "informs": "warns",
        "restrains": "restrains",
        "harms": "disrupts",
        "sustains": "sustains",
        "protects": "guards",
    }
    target = _graph(
        {"A", "C", "E", "G", "H", "I", "L", "M", "N", "P", "S", "X", "Y"},
        {
            ("L", "warns", "C"),
            ("C", "restrains", "P"),
            ("P", "disrupts", "G"),
            ("G", "sustains", "I"),
            ("C", "guards", "G"),
            ("E", "warns", "H"),
            ("H", "restrains", "M"),
            ("M", "disrupts", "N"),
            ("N", "sustains", "A"),
            ("S", "guards", "N"),
            ("X", "finances", "P"),
            ("Y", "registers", "A"),
        },
    )
    lure = _graph(
        {"A", "C", "E", "G", "H", "I", "L", "M", "N", "P", "S", "X", "Y"},
        {
            ("C", "restrains", "P"),
            ("P", "disrupts", "G"),
            ("G", "sustains", "I"),
            ("C", "guards", "G"),
            ("L", "records", "G"),
            ("E", "warns", "H"),
            ("H", "restrains", "M"),
            ("M", "disrupts", "N"),
            ("N", "sustains", "A"),
            ("H", "guards", "N"),
            ("X", "finances", "P"),
            ("Y", "registers", "A"),
        },
    )
    return _verify_exact_case(
        case,
        target=target,
        lure=lure,
        relation_map=relation_map,
        expected_mapping={"O": "L", "G": "C", "P": "P", "R": "G", "B": "I"},
        expected_lure_mapping={"O": "E", "G": "H", "P": "M", "R": "N", "B": "A"},
        required_phrases=(
            "灯塔抄报员 L 把私掠动向送交港盟议事会 C",
            "C 随后限制私掠团 P",
            "P 扰乱谷物航廊 G",
            "G 维持离岛公社 I",
            "C 同时护卫 G",
            "王室使节 E 向海关厅 H 告警",
            "守卫 N 的是慈善医院 S，不是 H",
        ),
    )


@register("HSS-P6-HIST-ANALOGY-L4-01")
def verify_hss_p6_hist_analogy_l4_01(case: Case) -> VerificationResult:
    relation_map = {
        "informs": "signals",
        "restrains": "restrains",
        "harms": "suppresses",
        "sustains": "sustains",
        "protects": "shields",
    }
    target = _graph(
        {"A", "B", "C", "E", "H", "K", "M", "N", "P", "Q", "R", "T", "W"},
        {
            ("P", "signals", "C"),
            ("M", "controls", "C"),
            ("M", "suppresses", "N"),
            ("N", "sustains", "A"),
            ("C", "shields", "N"),
            ("W", "relays", "K"),
            ("K", "relays", "H"),
            ("H", "restrains", "Q"),
            ("Q", "suppresses", "R"),
            ("R", "sustains", "B"),
            ("K", "shields", "R"),
            ("E", "edits", "P"),
            ("T", "taxes", "A"),
        },
    )
    lure = _graph(
        {"A", "B", "C", "E", "H", "K", "M", "N", "P", "Q", "R", "T", "W"},
        {
            ("P", "signals", "C"),
            ("C", "restrains", "M"),
            ("M", "suppresses", "N"),
            ("N", "sustains", "A"),
            ("C", "shields", "N"),
            ("W", "relays", "K"),
            ("K", "relays", "H"),
            ("H", "restrains", "Q"),
            ("Q", "suppresses", "R"),
            ("R", "sustains", "B"),
            ("K", "shields", "R"),
            ("E", "edits", "P"),
            ("T", "taxes", "A"),
        },
    )
    expected_mapping = {"O": "P", "G": "C", "P": "M", "R": "N", "B": "A"}
    target_matches, target_match = _unique_best(target, relation_map)
    lure_matches, lure_match = _unique_best(lure, relation_map)
    fatal = "P-CONTROLS-G"
    target_answer = _encoded(expected_mapping, fatal)
    lure_answer = _encoded(expected_mapping, "NONE")
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None
    checks = _source_checks(case)
    checks.extend(
        [
            _check(
                "target-text-relations",
                _contains_all(
                    case.target.problem,
                    (
                        "地下印刷网 P 向调解议会 C 传递镇压预警",
                        "M 控制 C，而不是 C 约束 M",
                        "M 压制互助网络 N",
                        "N 支撑街区大会 A",
                        "C 仍为 N 提供有限掩护",
                        "W 不直接向 H 预警",
                        "为 R 提供掩护的是 K，不是 H",
                    ),
                ),
                True,
            ),
            _check("target-best-score", target_match.score if target_match else None, 4),
            _check("target-unique-mapping-count", len(target_matches), 1),
            _check(
                "target-role-mapping",
                dict(target_match.mapping) if target_match else None,
                expected_mapping,
            ),
            _check(
                "target-missing-restraint",
                target_match.missing_edges if target_match else None,
                frozenset({("C", "restrains", "M")}),
            ),
            _check(
                "target-added-reverse-control",
                target_match.added_induced_edges if target_match else None,
                frozenset({("M", "controls", "C")}),
            ),
            _check("lure-best-score", lure_match.score if lure_match else None, 5),
            _check("lure-unique-mapping-count", len(lure_matches), 1),
            _check("stored-target", case.target.answer.legacy_value(), target_answer),
            _check("stored-lure", case.lure.answer.legacy_value(), lure_answer),
            _check("copy-equals-lure", case.copy_probe.answer.legacy_value(), lure_answer),
            _check("copy-differs-from-target", target_answer != lure_answer, True),
        ]
    )
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)
