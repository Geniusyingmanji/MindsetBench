from mindsetbench.data import (
    MAX_SOURCE_TARGET_CJK,
    PROJECT_ROOT,
    audit_surface,
    format_surface_table,
    load_cases,
    surface_metrics,
)
from mindsetbench.data.surface import cjk_bigrams, jaccard, notation_tokens, shared_templates
from mindsetbench.data.validate import Severity
from mindsetbench.models.case import Split

V1 = PROJECT_ROOT / "data" / "v1"


def test_bigram_and_notation_primitives() -> None:
    assert cjk_bigrams("菌落迁徙") == {"菌落", "落迁", "迁徙"}
    assert cjk_bigrams("A→B:2") == set()
    assert notation_tokens("U1→U2:2,蓝；R 与 K13") == {"U1", "U2", "R", "K13"}
    assert jaccard(set(), set()) == 0.0
    assert jaccard({"a", "b"}, {"b", "c"}) == 1 / 3


def test_shared_template_detects_edge_tables_and_label_codes() -> None:
    assert shared_templates("U1→U2:2,蓝", "A→C:5,V") == ("edge-table",)
    assert shared_templates("输出 O=S;G=C", "输出 O=A;G=B") == ("label-assignment",)
    assert shared_templates("一段普通叙述", "另一段普通叙述") == ()


def test_renamed_formal_chain_fails_surface_gate_when_calibrated() -> None:
    cases = load_cases(V1 / "formal-p2-sensitivity-chain.yaml")
    # The chain is stored as sanity; re-label it to see what the gate would say.
    relabeled = [case.model_copy(update={"split": Split.CALIBRATION}) for case in cases]
    report = audit_surface(relabeled)
    flagged = {issue.case_id for issue in report.errors}
    assert flagged == {"FORMAL-P2-SENS-L2-01", "FORMAL-P2-SENS-L3-01", "FORMAL-P2-SENS-L4-01"}
    template_hits = {
        issue.case_id for issue in report.errors if issue.code == "surface-shared-template"
    }
    assert template_hits == flagged
    assert all(
        "edge-table" in issue.message
        for issue in report.errors
        if issue.case_id in template_hits and issue.code == "surface-shared-template"
    )


def test_sanity_split_is_measured_but_not_gated() -> None:
    cases = load_cases(V1 / "formal-p2-sensitivity-chain.yaml")
    assert {case.split for case in cases} == {Split.SANITY}
    report = audit_surface(cases)
    assert report.ok
    assert report.warnings, "sanity items still surface their metrics as warnings"
    assert all(issue.severity == Severity.WARNING for issue in report.issues)


def test_legacy_far_analogies_pass_surface_gate() -> None:
    legacy = [case for case in load_cases() if case.level == 4 and case.id.startswith("L4-")]
    assert legacy
    relabeled = [case.model_copy(update={"split": Split.CALIBRATION}) for case in legacy]
    report = audit_surface(relabeled)
    assert report.ok, report.errors
    for case in legacy:
        assert surface_metrics(case).source_target_cjk <= MAX_SOURCE_TARGET_CJK


def test_surface_table_lists_every_case() -> None:
    cases = load_cases(V1 / "hss-p6-historical-analogy-chain.yaml")
    table = format_surface_table(cases)
    assert table.count("\n") == len(cases)
    assert "HSS-P6-HIST-ANALOGY-L4-01" in table
