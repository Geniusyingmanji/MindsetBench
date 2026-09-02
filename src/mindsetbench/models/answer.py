from __future__ import annotations

import re
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnswerType(StrEnum):
    NUMBER = "number"
    FRACTION = "fraction"
    PERCENTAGE = "percentage"
    CHOICE = "choice"
    LABEL = "label"
    BOOLEAN = "boolean"
    STRING = "string"


class AnswerPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: AnswerType
    value: str
    abs_tolerance: Decimal | None = None
    rel_tolerance: Decimal | None = None
    allow_affixes: bool = False
    case_sensitive: bool = False

    @field_validator("value", mode="before")
    @classmethod
    def stringify_value(cls, value: Any) -> str:
        return str(value).strip()


class AnswerSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parts: list[AnswerPart] = Field(min_length=1)
    separator: str = ";"

    @classmethod
    def from_legacy(
        cls,
        value: Any,
        answer_type: str | None = None,
        tolerance: float | Decimal | str | None = None,
    ) -> AnswerSpec:
        raw = str(value).strip()
        chunks = [part.strip() for part in re.split(r"[;；,，]", raw) if part.strip()]
        tolerances = _parse_legacy_tolerances(tolerance, chunks)
        parts: list[AnswerPart] = []
        for index, chunk in enumerate(chunks):
            inferred = _infer_type(chunk, answer_type)
            parts.append(
                AnswerPart(
                    type=inferred,
                    value=chunk,
                    abs_tolerance=tolerances[index] if inferred in _NUMERIC_TYPES else None,
                )
            )
        return cls(parts=parts)

    def legacy_value(self) -> str:
        return self.separator.join(part.value for part in self.parts)


_NUMERIC_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_FRACTION_RE = re.compile(r"^[+-]?\d+/[+-]?\d+$")
_NUMERIC_TYPES = {AnswerType.NUMBER, AnswerType.FRACTION, AnswerType.PERCENTAGE}


def _infer_type(value: str, declared: str | None) -> AnswerType:
    if value.endswith(("%", "％")):
        return AnswerType.PERCENTAGE
    if _FRACTION_RE.fullmatch(value):
        return AnswerType.FRACTION
    if _NUMERIC_RE.fullmatch(value):
        return AnswerType.NUMBER
    if declared == "mcq" or re.fullmatch(r"[A-Za-z]", value):
        return AnswerType.CHOICE
    if declared == "string" and re.fullmatch(r"[A-Za-z]+\d+", value):
        return AnswerType.LABEL
    return AnswerType.STRING


def _parse_legacy_tolerances(
    tolerance: float | Decimal | str | None,
    chunks: list[str],
) -> list[Decimal | None]:
    if tolerance is None:
        return [None] * len(chunks)
    if isinstance(tolerance, (int, float, Decimal)):
        parsed = Decimal(str(tolerance))
        return [parsed] * len(chunks)

    clauses = [part.strip() for part in re.split(r"[;；]", tolerance) if part.strip()]
    if len(clauses) == len(chunks):
        return [_parse_tolerance_clause(clause) for clause in clauses]

    matches = re.findall(r"(?:±|\+/-)\s*(\d+(?:\.\d+)?)", tolerance)
    numeric_indexes = [
        index for index, chunk in enumerate(chunks) if _infer_type(chunk, None) in _NUMERIC_TYPES
    ]
    result: list[Decimal | None] = [None] * len(chunks)
    if len(matches) == 1 and len(numeric_indexes) == 1:
        result[numeric_indexes[0]] = Decimal(matches[0])
    return result


def _parse_tolerance_clause(clause: str) -> Decimal | None:
    match = re.search(r"(?:±|\+/-)\s*(\d+(?:\.\d+)?)", clause)
    if match:
        return Decimal(match.group(1))
    if "精确" in clause or clause.casefold() == "exact":
        return Decimal("0")
    return None
