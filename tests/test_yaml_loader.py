from pathlib import Path

import pytest

from mindsetbench.data.loader import DatasetError, load_cases, load_schema_cards


def test_yaml_loader_supports_anchors(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.yaml"
    dataset.write_text(
        """
- &case
  id: yaml-1
  level: 0
  thread: A-test
  schema_name: test
  source: &source
    domain: d
    problem: p
    solution: s
    answer: a
  target: {domain: d, problem: p2, answer: a}
  mapping: {objects: {}, shared_relations: []}
  lure: null
  provenance: original
- <<: *case
  id: yaml-2
  level: 1
  source: *source
""",
        encoding="utf-8",
    )
    cases = load_cases(dataset)
    assert [case.id for case in cases] == ["yaml-1", "yaml-2"]
    assert cases[0].source == cases[1].source


def test_yaml_loader_rejects_non_list(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.yaml"
    dataset.write_text("cases: []\n", encoding="utf-8")
    with pytest.raises(DatasetError, match="top-level list"):
        load_cases(dataset)


def test_dataset_bundle_composes_and_selects_yaml_cases(tmp_path: Path) -> None:
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    template = """
- id: {case_id}
  level: 0
  thread: A-test
  schema_name: test
  source: {{domain: d, problem: p, solution: s, answer: a}}
  target: {{domain: d, problem: p2, answer: a}}
  mapping: {{objects: {{}}, shared_relations: []}}
  lure: null
  provenance: original
"""
    first.write_text(template.format(case_id="bundle-1"), encoding="utf-8")
    second.write_text(template.format(case_id="bundle-2"), encoding="utf-8")
    bundle = tmp_path / "bundle.json"
    bundle.write_text(
        '{"datasets":["first.yaml","second.yaml"],"case_ids":["bundle-2"]}',
        encoding="utf-8",
    )
    assert [case.id for case in load_cases(bundle)] == ["bundle-2"]


def test_dataset_bundle_rejects_cycles(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text('{"datasets":["second.json"]}', encoding="utf-8")
    second.write_text('{"datasets":["first.json"]}', encoding="utf-8")
    with pytest.raises(DatasetError, match="cyclic dataset bundle"):
        load_cases(first)


def test_schema_card_bundle_composes_yaml_cards(tmp_path: Path) -> None:
    card = tmp_path / "card.yaml"
    card.write_text(
        """
- schema_id: bundle-schema
  paradigm: P2
  thread: B-test
  name: bundle
  definition: bundle definition
  required_relations: [one]
  invalid_variants: [bad]
  level_plan: {L0: a, L1: b, L2: c, L3: d, L4: e}
  copy_probe: probe
  lure: lure
  verifier: verifier
""",
        encoding="utf-8",
    )
    bundle = tmp_path / "cards.json"
    bundle.write_text('{"schema_card_files":["card.yaml"]}', encoding="utf-8")
    assert [item.schema_id for item in load_schema_cards(bundle)] == ["bundle-schema"]
