"""Surface-distance audit: is the target really far from the source on the page?

A transfer item measures schema transfer only if the source cannot be recognised
as relevant from surface cues alone. This module quantifies three cheap cues that
made earlier chains "look alike at a glance":

* shared notation templates (edge tables, ``LABEL=`` assignments, bit strings,
  pipe tables) reused verbatim between source and target;
* lexical overlap of the problem statements measured with CJK character bigrams;
* the lure being *farther* from the target than the source is, which inverts the
  intended design (the lure is supposed to be the surface-near reference).

The audit is deliberately representation-level: it cannot certify that a target is
schema-opaque, but it catches renamed isomorphs mechanically and reproducibly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import pairwise

from mindsetbench.models.case import Case, Split

from .validate import Severity, ValidationReport

#: Above this CJK-bigram Jaccard the two statements share too much phrasing to count
#: as a cross-domain pair. Calibrated on the legacy library, where L2/L3/L4 targets
#: average 0.09/0.04/0.03 against their sources, while renamed chains sit at 0.15–0.8.
MAX_SOURCE_TARGET_CJK = 0.12

#: Splits whose L2+ members must pass the surface gate.
GATED_SPLITS = frozenset({Split.CALIBRATION, Split.TEST})

_CJK = re.compile(r"[一-鿿]")
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,7}")
_TEMPLATES: dict[str, re.Pattern[str]] = {
    # X→Y:5,蓝  /  A→C:5,V   (successor/edge tables)
    "edge-table": re.compile(r"[A-Za-z]\d?→[A-Za-z]\d?:\d+"),
    # O=S;G=C  /  A=SUPPORTED  (label assignment codes; K=1 style formula bindings excluded)
    "label-assignment": re.compile(r"(?<![A-Za-z])[A-Z]{1,8}=[A-Z][A-Za-z_-]*"),
    # long bit strings
    "bit-string": re.compile(r"(?<![0-9])[01]{6,}(?![0-9])"),
    # markdown-style pipe tables
    "pipe-table": re.compile(r"\|[^|\n]+\|[^|\n]+\|"),
}


@dataclass(frozen=True)
class SurfaceMetrics:
    case_id: str
    level: int
    split: Split
    source_target_cjk: float
    source_target_notation: float
    target_lure_cjk: float | None
    target_lure_notation: float | None
    shared_templates: tuple[str, ...] = field(default_factory=tuple)

    @property
    def lure_farther_than_source(self) -> bool | None:
        if self.target_lure_cjk is None:
            return None
        return self.target_lure_cjk < self.source_target_cjk


def cjk_bigrams(text: str) -> set[str]:
    chars = [char for char in text if _CJK.match(char)]
    return {first + second for first, second in pairwise(chars)}


def notation_tokens(text: str) -> set[str]:
    """Identifiers such as U1, R, K13, ALLOW: the symbols a reader aligns at a glance."""

    return set(_IDENTIFIER.findall(text))


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    return len(left & right) / len(left | right)


def shared_templates(source: str, target: str) -> tuple[str, ...]:
    return tuple(
        name
        for name, pattern in _TEMPLATES.items()
        if pattern.search(source) and pattern.search(target)
    )


def surface_metrics(case: Case) -> SurfaceMetrics:
    source = case.source.problem
    target = case.target.problem
    lure = case.lure.problem if case.lure is not None else None
    return SurfaceMetrics(
        case_id=case.id,
        level=case.level,
        split=case.split,
        source_target_cjk=jaccard(cjk_bigrams(source), cjk_bigrams(target)),
        source_target_notation=jaccard(notation_tokens(source), notation_tokens(target)),
        target_lure_cjk=None if lure is None else jaccard(cjk_bigrams(target), cjk_bigrams(lure)),
        target_lure_notation=(
            None if lure is None else jaccard(notation_tokens(target), notation_tokens(lure))
        ),
        shared_templates=shared_templates(source, target),
    )


def audit_surface(
    cases: list[Case],
    *,
    max_source_target_cjk: float = MAX_SOURCE_TARGET_CJK,
) -> ValidationReport:
    """Gate L2+ calibration/test items on representation-level distance.

    Sanity and dev items are measured but never fail: the sanity split exists precisely
    to hold verified material that does not pass this gate.
    """

    report = ValidationReport()
    for case in cases:
        metrics = surface_metrics(case)
        if case.level < 2:
            continue
        gated = case.split in GATED_SPLITS
        severity = Severity.ERROR if gated else Severity.WARNING
        if metrics.shared_templates:
            report.add(
                severity,
                "surface-shared-template",
                "source and target reuse the same notation template: "
                + ", ".join(metrics.shared_templates),
                case.id,
            )
        if metrics.source_target_cjk > max_source_target_cjk:
            report.add(
                severity,
                "surface-lexical-overlap",
                f"source/target CJK-bigram Jaccard {metrics.source_target_cjk:.2f} "
                f"exceeds {max_source_target_cjk:.2f}",
                case.id,
            )
        if gated and metrics.lure_farther_than_source:
            report.add(
                Severity.WARNING,
                "surface-lure-farther-than-source",
                "the lure shares less phrasing with the target than the source does "
                f"({metrics.target_lure_cjk:.2f} < {metrics.source_target_cjk:.2f})",
                case.id,
            )
    return report


def format_surface_table(cases: list[Case]) -> str:
    header = (
        f"{'case':44} {'L':>1} {'split':11} {'S-T cjk':>7} {'S-T sym':>7} "
        f"{'T-L cjk':>7} {'T-L sym':>7} templates"
    )
    lines = [header]
    for case in cases:
        metrics = surface_metrics(case)
        lines.append(
            f"{metrics.case_id:44} {metrics.level:>1} {metrics.split.value:11} "
            f"{metrics.source_target_cjk:7.2f} {metrics.source_target_notation:7.2f} "
            f"{_fmt(metrics.target_lure_cjk):>7} {_fmt(metrics.target_lure_notation):>7} "
            f"{','.join(metrics.shared_templates) or '-'}"
        )
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"
