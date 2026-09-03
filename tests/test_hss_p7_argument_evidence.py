import pytest

from mindsetbench.data import (
    PROJECT_ROOT,
    load_cases,
    load_schema_cards,
    validate_dataset,
    validate_schema_cards,
    validate_transfer_design,
)
from mindsetbench.verification import verify_case
from mindsetbench.verification.argument_evidence import (
    EvidenceNode,
    Stance,
    Verdict,
    assess_claims,
    ultimate_roots,
    validate_evidence_graph,
)

DATASET = PROJECT_ROOT / "data" / "v1" / "hss-p7-argument-evidence-chain.yaml"
CARDS = PROJECT_ROOT / "data" / "schema_cards" / "hss-p7-argument-evidence-v1.yaml"
MANIFEST = PROJECT_ROOT / "data" / "manifests" / "hss10.json"


def _origin(node_id: str) -> EvidenceNode:
    return EvidenceNode(node_id)


def _report(
    node_id: str,
    claim: str,
    stance: Stance,
    *parents: str,
) -> EvidenceNode:
    return EvidenceNode(node_id, parents, claim, stance)


def test_hss_p7_chain_is_complete_strict_audited_and_verified() -> None:
    cases = load_cases(DATASET)
    strict = validate_dataset(cases, strict_v1=True)
    audit = validate_transfer_design(cases, require_complete_chains=True)
    assert strict.ok, strict.issues
    assert audit.ok, audit.issues
    assert len(cases) == 5
    assert [case.level for case in cases] == list(range(5))
    assert {case.chain for case in cases} == {"hss-p7-argument-evidence-v1"}

    results = [verify_case(case) for case in cases]
    assert all(result.passed for result in results), results


def test_hss_p7_schema_card_and_hss10_manifest_match() -> None:
    direct = load_cases(DATASET)
    cards = load_schema_cards(CARDS)
    report = validate_schema_cards(cards, direct)
    assert report.ok, report.issues

    manifest = load_cases(MANIFEST)
    assert len(manifest) == 10
    assert {case.paradigm.value for case in manifest} == {"P4", "P7"}
    assert [case.level for case in manifest].count(4) == 2


def test_hss_p7_chain_has_deterministic_negative_controls() -> None:
    for case in load_cases(DATASET):
        assert case.lure is not None and case.lure.answer is not None
        assert case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer


def test_argument_engine_traces_roots_and_propagates_invalidity() -> None:
    nodes = {
        "O1": _origin("O1"),
        "R1": _report("R1", "H", Stance.SUPPORT, "O1"),
        "R2": _report("R2", "H", Stance.SUPPORT, "R1"),
        "O2": _origin("O2"),
        "R3": _report("R3", "H", Stance.SUPPORT, "O2"),
    }
    assert ultimate_roots("R2", nodes) == {"O1"}
    supported = assess_claims(nodes, ("H",))["H"]
    assert supported.verdict == Verdict.SUPPORTED
    invalidated = assess_claims(nodes, ("H",), invalid_roots={"O2"})["H"]
    assert invalidated.verdict == Verdict.UNCORROBORATED
    assert invalidated.supporting_groups == {"O1"}


def test_argument_engine_can_merge_distinct_roots_by_generation_process() -> None:
    nodes = {
        "O1": _origin("O1"),
        "R1": _report("R1", "H", Stance.SUPPORT, "O1"),
        "O2": _origin("O2"),
        "R2": _report("R2", "H", Stance.SUPPORT, "O2"),
    }
    independent = assess_claims(nodes, ("H",))["H"]
    coordinated = assess_claims(
        nodes,
        ("H",),
        independence_groups={"O1": "briefing", "O2": "briefing"},
    )["H"]
    assert independent.verdict == Verdict.SUPPORTED
    assert coordinated.verdict == Verdict.UNCORROBORATED
    assert coordinated.supporting_groups == {"briefing"}


def test_argument_engine_rejects_missing_parents_and_cycles() -> None:
    missing = {"R": _report("R", "H", Stance.SUPPORT, "absent")}
    with pytest.raises(ValueError, match="missing parents"):
        validate_evidence_graph(missing)

    cyclic = {
        "R1": _report("R1", "H", Stance.SUPPORT, "R2"),
        "R2": _report("R2", "H", Stance.SUPPORT, "R1"),
    }
    with pytest.raises(ValueError, match="contains a cycle"):
        validate_evidence_graph(cyclic)


def test_argument_engine_rejects_invalid_configuration() -> None:
    nodes = {"O1": _origin("O1")}
    with pytest.raises(ValueError, match="threshold must be at least one"):
        assess_claims(nodes, ("H",), threshold=0)
    with pytest.raises(ValueError, match="invalid roots are absent"):
        assess_claims(nodes, ("H",), invalid_roots={"missing"})
    with pytest.raises(ValueError, match="independence groups reference absent roots"):
        assess_claims(nodes, ("H",), independence_groups={"missing": "group"})
