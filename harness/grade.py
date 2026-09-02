"""Backward-compatible wrapper around the package grader."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mindsetbench.grading import extract_answer as _extract_answer  # noqa: E402
from mindsetbench.grading import grade_response  # noqa: E402
from mindsetbench.models.case import Case  # noqa: E402


def extract_answer(text: str) -> str:
    answer, _ = _extract_answer(text, require_marker=False)
    return answer or ""


def grade_item(item: dict, model_output: str):
    """Legacy API: return ``(correct, extracted_answer)``."""
    payload = {
        "id": item.get("id", "legacy-item"),
        "level": item.get("level", 0),
        "thread": item.get("thread", "A-legacy"),
        "schema_name": item.get("schema_name", "legacy"),
        "source": item.get(
            "source",
            {"domain": "legacy", "problem": "legacy", "solution": "legacy", "answer": "legacy"},
        ),
        "target": item["target"],
        "mapping": item.get("mapping", {"objects": {}, "shared_relations": [], "varied": []}),
        "lure": item.get("lure"),
        "provenance": item.get("provenance", "legacy"),
    }
    case = Case.model_validate(payload)
    result = grade_response(case.gold_view(), model_output, require_marker=False)
    return result.correct, result.extracted or ""
