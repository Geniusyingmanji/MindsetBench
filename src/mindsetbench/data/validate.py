from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import pairwise

from mindsetbench.models.case import Case, Split
from mindsetbench.models.schema_card import SchemaCard


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ValidationIssue:
    severity: Severity
    code: str
    message: str
    case_id: str | None = None


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == Severity.WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(
        self,
        severity: Severity,
        code: str,
        message: str,
        case_id: str | None = None,
    ) -> None:
        self.issues.append(ValidationIssue(severity, code, message, case_id))


def validate_dataset(cases: list[Case], *, strict_v1: bool = False) -> ValidationReport:
    report = ValidationReport()
    duplicates = [case_id for case_id, count in Counter(c.id for c in cases).items() if count > 1]
    for case_id in duplicates:
        report.add(Severity.ERROR, "duplicate-id", "case id is not unique", case_id)

    by_chain: dict[str, list[Case]] = defaultdict(list)
    for case in cases:
        _validate_case(case, report, strict_v1=strict_v1)
        if case.chain:
            by_chain[case.chain].append(case)

    for chain, members in by_chain.items():
        if "multihop" in chain:
            _validate_multihop_chain(chain, members, report)
        else:
            _validate_fixed_chain(chain, members, report)
    return report


def validate_schema_cards(cards: list[SchemaCard], cases: list[Case]) -> ValidationReport:
    report = ValidationReport()
    by_id = {card.schema_id: card for card in cards}
    if len(by_id) != len(cards):
        report.add(Severity.ERROR, "duplicate-schema-card", "schema card ids are not unique")

    grouped: dict[str, list[Case]] = defaultdict(list)
    for case in cases:
        assert case.schema_id is not None
        grouped[case.schema_id].append(case)
        card = by_id.get(case.schema_id)
        if card is None:
            report.add(
                Severity.ERROR,
                "missing-schema-card",
                f"no schema card for {case.schema_id}",
                case.id,
            )
            continue
        if card.paradigm != case.paradigm:
            report.add(
                Severity.ERROR,
                "schema-paradigm-mismatch",
                f"card={card.paradigm.value} case={case.paradigm.value}",
                case.id,
            )
        if card.thread_code != case.thread_code:
            report.add(
                Severity.ERROR,
                "schema-thread-mismatch",
                f"card={card.thread_code} case={case.thread_code}",
                case.id,
            )

    for schema_id, members in grouped.items():
        levels = {member.level for member in members}
        if levels != set(range(5)):
            report.add(
                Severity.ERROR,
                "incomplete-schema-levels",
                f"schema has levels {sorted(levels)}, expected 0..4",
                schema_id,
            )
    return report


def validate_transfer_design(
    cases: list[Case],
    *,
    require_complete_chains: bool = False,
) -> ValidationReport:
    """Audit benchmark-construction invariants beyond basic schema validity."""

    report = validate_dataset(cases, strict_v1=True)
    by_chain: dict[str, list[Case]] = defaultdict(list)
    method_leak_terms = (
        "最小不动点",
        "结构因果模型",
        "scm",
        "矩阵树定理",
        "局部灵敏度",
        "角色映射",
    )
    for case in cases:
        if case.chain:
            by_chain[case.chain].append(case)
        normalized_target = case.target.problem.casefold()
        leaked = [term for term in method_leak_terms if term.casefold() in normalized_target]
        if leaked:
            report.add(
                Severity.ERROR,
                "design-method-label-leak",
                f"target-only text exposes method labels: {leaked}",
                case.id,
            )
        if case.lure is None or case.lure.answer is None:
            report.add(Severity.ERROR, "design-missing-lure", "case needs a solved lure", case.id)
            continue
        if case.copy_probe is None:
            report.add(
                Severity.ERROR,
                "design-missing-copy-probe",
                "case needs a deterministic copy probe",
                case.id,
            )
            continue
        if case.copy_probe.answer != case.lure.answer:
            report.add(
                Severity.ERROR,
                "design-copy-lure-mismatch",
                "copy probe must equal the preregistered lure answer",
                case.id,
            )
        if case.copy_probe.answer == case.target.answer:
            report.add(
                Severity.ERROR,
                "design-copy-equals-target",
                "copy probe must differ from target gold",
                case.id,
            )
        if case.level >= 3:
            if len(case.mapping.objects) < 4:
                report.add(
                    Severity.ERROR,
                    "design-shallow-object-map",
                    "L3+ needs at least four mapped functional objects",
                    case.id,
                )
            if len(case.mapping.shared_relations) < 4:
                report.add(
                    Severity.ERROR,
                    "design-shallow-relation-map",
                    "L3+ needs at least four explicitly preserved relations",
                    case.id,
                )
        if case.level == 4:
            broken_count = len(case.mapping.added_relations) + len(case.mapping.removed_relations)
            if broken_count == 0:
                report.add(
                    Severity.ERROR,
                    "design-missing-broken-relation",
                    "L4 needs at least one added or removed relation",
                    case.id,
                )
            if not case.mapping.adaptation_required:
                report.add(
                    Severity.ERROR,
                    "design-missing-adaptation",
                    "L4 needs an explicit adaptation requirement",
                    case.id,
                )

    if require_complete_chains:
        for chain, members in by_chain.items():
            levels = {member.level for member in members}
            if levels != set(range(5)):
                report.add(
                    Severity.ERROR,
                    "design-incomplete-chain",
                    f"chain has levels {sorted(levels)}, expected 0..4",
                    chain,
                )
    return report


def _validate_case(case: Case, report: ValidationReport, *, strict_v1: bool) -> None:
    if case.thread_code not in set("ABCDEFGHIJK"):
        report.add(Severity.ERROR, "invalid-thread", f"unknown thread {case.thread!r}", case.id)
    if case.level >= 2 and case.lure is None and not (case.chain and "multihop" in case.chain):
        report.add(Severity.ERROR, "missing-lure", "L2+ case must define a lure", case.id)
    if case.level >= 3 and case.copy_probe is None:
        report.add(
            Severity.ERROR if strict_v1 else Severity.WARNING,
            "missing-copy-probe",
            "L3+ case must define a structured copy probe",
            case.id,
        )
    if case.lure is not None and (case.lure.solution is None or case.lure.answer is None):
        report.add(
            Severity.ERROR if strict_v1 else Severity.WARNING,
            "incomplete-lure",
            "lure must have a structured solution and answer",
            case.id,
        )
    if case.target.tolerance_note:
        report.add(
            Severity.ERROR if strict_v1 else Severity.WARNING,
            "legacy-tolerance",
            "descriptive tolerance must be migrated to per-part numeric tolerances",
            case.id,
        )
    if strict_v1:
        if not case.version.startswith("1."):
            report.add(Severity.ERROR, "legacy-version", "strict v1 requires version 1.x", case.id)
        if case.split == Split.UNASSIGNED:
            report.add(
                Severity.ERROR, "missing-split", "strict v1 requires an explicit split", case.id
            )
        if case.verification is None or not case.verification.entrypoint:
            report.add(
                Severity.ERROR,
                "missing-verifier",
                "strict v1 requires a verifier entrypoint",
                case.id,
            )
        if case.hints is None or case.hints.oracle_mindset is None:
            report.add(
                Severity.ERROR,
                "missing-oracle-hint",
                "strict v1 requires an oracle mindset",
                case.id,
            )


def _validate_fixed_chain(chain: str, members: list[Case], report: ValidationReport) -> None:
    source_fingerprints = {
        json.dumps(member.source.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        for member in members
    }
    if len(source_fingerprints) != 1:
        report.add(Severity.ERROR, "fixed-chain-source", "fixed chain sources differ", chain)
    levels = [member.level for member in members]
    if len(levels) != len(set(levels)):
        report.add(Severity.ERROR, "fixed-chain-level", "fixed chain repeats a level", chain)


def _validate_multihop_chain(chain: str, members: list[Case], report: ValidationReport) -> None:
    if any(member.hop is None for member in members):
        report.add(Severity.ERROR, "missing-hop", "multihop member is missing hop", chain)
        return
    ordered = sorted(members, key=lambda item: item.hop or -1)
    hops = [member.hop for member in ordered]
    expected = list(range(min(hops), max(hops) + 1))
    if hops != expected:
        report.add(Severity.ERROR, "noncontiguous-hop", f"got hops {hops}", chain)
    for previous, current in pairwise(ordered):
        if current.source.problem.strip() != previous.target.problem.strip():
            report.add(
                Severity.ERROR,
                "broken-hop",
                f"hop {current.hop} source does not equal prior target",
                current.id,
            )
