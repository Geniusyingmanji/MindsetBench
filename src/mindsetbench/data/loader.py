from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import yaml

from mindsetbench.models.case import Case
from mindsetbench.models.schema_card import SchemaCard

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "all.jsonl"


class DatasetError(ValueError):
    pass


def load_cases(path: str | Path = DEFAULT_DATASET) -> list[Case]:
    return _load_cases(Path(path), seen=frozenset())


def _load_cases(dataset_path: Path, *, seen: frozenset[Path]) -> list[Case]:
    if not dataset_path.exists():
        raise DatasetError(f"dataset does not exist: {dataset_path}")

    if dataset_path.suffix.casefold() in {".yaml", ".yml"}:
        return _load_yaml_cases(dataset_path)
    if dataset_path.suffix.casefold() == ".json":
        return _load_case_bundle(dataset_path, seen=seen)

    cases: list[Case] = []
    with dataset_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                cases.append(Case.model_validate(row))
            except Exception as exc:
                raise DatasetError(f"{dataset_path}:{line_number}: {exc}") from exc
    return cases


def _load_case_bundle(path: Path, *, seen: frozenset[Path]) -> list[Case]:
    resolved_path = path.resolve()
    if resolved_path in seen:
        chain = " -> ".join(str(item) for item in (*seen, resolved_path))
        raise DatasetError(f"cyclic dataset bundle: {chain}")
    payload = _load_json_object(path, "dataset bundle")
    members = payload.get("datasets")
    if not isinstance(members, list) or not members or not all(
        isinstance(member, str) and member.strip() for member in members
    ):
        raise DatasetError(
            f"dataset bundle {path} must contain a non-empty string list named datasets"
        )

    next_seen = seen | {resolved_path}
    cases = [
        case
        for member in members
        for case in _load_cases((path.parent / member).resolve(), seen=next_seen)
    ]
    by_id = index_cases(cases)
    selected_ids = payload.get("case_ids")
    if selected_ids is None:
        return cases
    if not isinstance(selected_ids, list) or not selected_ids or not all(
        isinstance(case_id, str) and case_id for case_id in selected_ids
    ):
        raise DatasetError(f"dataset bundle {path} case_ids must be a non-empty string list")
    if len(selected_ids) != len(set(selected_ids)):
        raise DatasetError(f"dataset bundle {path} repeats a case id")
    missing = [case_id for case_id in selected_ids if case_id not in by_id]
    if missing:
        raise DatasetError(f"dataset bundle {path} references unknown cases: {missing}")
    return [by_id[case_id] for case_id in selected_ids]


def _load_yaml_cases(path: Path) -> list[Case]:
    payload = _load_yaml_list(path, "dataset")
    cases: list[Case] = []
    for index, row in enumerate(payload, 1):
        try:
            cases.append(Case.model_validate(row))
        except Exception as exc:
            raise DatasetError(f"{path}:item {index}: {exc}") from exc
    return cases


def load_schema_cards(path: str | Path) -> list[SchemaCard]:
    return _load_schema_cards(Path(path), seen=frozenset())


def _load_schema_cards(cards_path: Path, *, seen: frozenset[Path]) -> list[SchemaCard]:
    if cards_path.suffix.casefold() == ".json":
        return _load_schema_card_bundle(cards_path, seen=seen)
    payload = _load_yaml_list(cards_path, "schema-card file")
    cards: list[SchemaCard] = []
    for index, row in enumerate(payload, 1):
        try:
            cards.append(SchemaCard.model_validate(row))
        except Exception as exc:
            raise DatasetError(f"{cards_path}:item {index}: {exc}") from exc
    return cards


def _load_schema_card_bundle(path: Path, *, seen: frozenset[Path]) -> list[SchemaCard]:
    resolved_path = path.resolve()
    if resolved_path in seen:
        raise DatasetError(f"cyclic schema-card bundle: {resolved_path}")
    payload = _load_json_object(path, "schema-card bundle")
    members = payload.get("schema_card_files")
    if not isinstance(members, list) or not members or not all(
        isinstance(member, str) and member.strip() for member in members
    ):
        raise DatasetError(
            f"schema-card bundle {path} must contain a non-empty string list named "
            "schema_card_files"
        )
    next_seen = seen | {resolved_path}
    cards = [
        card
        for member in members
        for card in _load_schema_cards((path.parent / member).resolve(), seen=next_seen)
    ]
    schema_ids = [card.schema_id for card in cards]
    if len(schema_ids) != len(set(schema_ids)):
        raise DatasetError(f"schema-card bundle {path} contains duplicate schema ids")
    return cards


def _load_json_object(path: Path, kind: str) -> dict:
    if not path.exists():
        raise DatasetError(f"{kind} does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DatasetError(f"JSON {kind} {path} must contain a top-level object")
    return payload


def _load_yaml_list(path: Path, kind: str) -> list:
    if not path.exists():
        raise DatasetError(f"{kind} does not exist: {path}")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise DatasetError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(payload, list):
        raise DatasetError(f"YAML {kind} {path} must contain a top-level list")
    return payload


def load_manifest(
    manifest_path: str | Path,
    dataset_path: str | Path = DEFAULT_DATASET,
) -> list[Case]:
    path = Path(manifest_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = data.get("case_ids")
    if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
        raise DatasetError(f"manifest {path} must contain a string list named case_ids")

    by_id = index_cases(load_cases(dataset_path))
    overrides_path = data.get("overrides")
    if overrides_path is not None:
        if not isinstance(overrides_path, str):
            raise DatasetError(f"manifest {path} overrides must be a path string")
        resolved = (path.parent / overrides_path).resolve()
        overrides = json.loads(resolved.read_text(encoding="utf-8"))
        if not isinstance(overrides, dict):
            raise DatasetError(f"overrides {resolved} must be an object keyed by case id")
        for case_id, patch in overrides.items():
            if case_id not in by_id:
                raise DatasetError(f"override references unknown case: {case_id}")
            if not isinstance(patch, dict):
                raise DatasetError(f"override for {case_id} must be an object")
            base = by_id[case_id].model_dump(mode="json")
            by_id[case_id] = Case.model_validate(_deep_merge(base, patch))
    missing = [case_id for case_id in ids if case_id not in by_id]
    if missing:
        raise DatasetError(f"manifest references unknown cases: {missing}")
    return [by_id[case_id] for case_id in ids]


def _deep_merge(base: dict, patch: dict) -> dict:
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def index_cases(cases: Iterable[Case]) -> dict[str, Case]:
    result: dict[str, Case] = {}
    for case in cases:
        if case.id in result:
            raise DatasetError(f"duplicate case id: {case.id}")
        result[case.id] = case
    return result
