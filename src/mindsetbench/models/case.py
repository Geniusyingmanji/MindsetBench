from __future__ import annotations

from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mindsetbench.models.answer import AnswerSpec


class Split(StrEnum):
    UNASSIGNED = "unassigned"
    DEV = "dev"
    CALIBRATION = "calibration"
    TEST = "test"
    # Execution/format sanity material: verified and runnable, but the target shares the
    # source's formal representation, so it must not be reported as transfer distance.
    SANITY = "sanity"


class Paradigm(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    P5 = "P5"
    P6 = "P6"
    P7 = "P7"
    P8 = "P8"
    P9 = "P9"


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str
    problem: str
    solution: str
    answer: str


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str
    problem: str
    answer: AnswerSpec
    answer_format: str | None = None
    answer_type: str = "string"
    tolerance: Decimal | None = None
    tolerance_note: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_answer(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        answer = normalized.get("answer")
        if answer is not None and not isinstance(answer, dict):
            normalized["answer"] = AnswerSpec.from_legacy(
                answer,
                normalized.get("answer_type"),
                normalized.get("tolerance"),
            ).model_dump(mode="json")
        tolerance = normalized.get("tolerance")
        if isinstance(tolerance, str):
            try:
                normalized["tolerance"] = Decimal(tolerance)
            except InvalidOperation:
                normalized["tolerance_note"] = tolerance
                normalized["tolerance"] = None
        return normalized


class Mapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objects: dict[str, str]
    shared_relations: list[str]
    varied: list[str] = Field(default_factory=list)
    added_relations: list[str] = Field(default_factory=list)
    removed_relations: list[str] = Field(default_factory=list)
    adaptation_required: list[str] = Field(default_factory=list)


class Lure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem: str
    solution: str | None = None
    answer: AnswerSpec | None = None
    why_surface_similar: str
    why_structurally_different: str
    wrong_schema_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_answer(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        answer = normalized.get("answer")
        if answer is not None and not isinstance(answer, dict):
            normalized["answer"] = AnswerSpec.from_legacy(answer).model_dump(mode="json")
        return normalized


class CopyProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: AnswerSpec
    derivation: str


class OracleMindset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    insight: str
    when_to_use: str


class Hints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_name: str
    oracle_mindset: OracleMindset | None = None
    false_mindset: OracleMindset | None = None


class VerificationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entrypoint: str | None = None
    method: str | None = None
    legacy_note: str | None = None


class CasePromptView(BaseModel):
    """Material available to prompt builders. Target gold is intentionally absent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    level: int
    paradigm: Paradigm
    schema_id: str
    schema_name: str
    hints: Hints
    source: Source
    target_problem: str
    answer_format: str | None
    mapping_objects: dict[str, str]
    shared_relations: list[str]
    lure: Lure | None
    chain: str | None
    hop: int | None


class CaseGoldView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    target_answer: AnswerSpec
    copy_probe_answer: AnswerSpec | None
    lure_answer: AnswerSpec | None


class Case(BaseModel):
    """Canonical case model with a compatibility layer for the original JSONL files."""

    model_config = ConfigDict(extra="forbid")

    id: str
    version: str = "0.1"
    split: Split = Split.UNASSIGNED
    paradigm: Paradigm = Paradigm.P1
    thread: str
    schema_id: str | None = None
    schema_name: str
    level: int = Field(ge=0, le=4)
    source: Source
    target: Target
    mapping: Mapping
    lure: Lure | None
    copy_probe: CopyProbe | None = None
    hints: Hints | None = None
    verification: VerificationSpec | None = None
    provenance: str | dict[str, Any]
    verified: str | None = None
    chain: str | None = None
    hop: int | None = None
    method: str | None = None
    derivation: Any | None = None
    history_note: Any | None = None

    @model_validator(mode="after")
    def fill_compatibility_defaults(self) -> Case:
        if self.schema_id is None:
            self.schema_id = self.chain or self.id
        if self.hints is None:
            self.hints = Hints(schema_name=self.schema_name)
        if self.verification is None:
            self.verification = VerificationSpec(legacy_note=self.verified)
        return self

    @property
    def thread_code(self) -> str:
        return self.thread.split("-", 1)[0]

    def prompt_view(self) -> CasePromptView:
        assert self.schema_id is not None
        return CasePromptView(
            id=self.id,
            level=self.level,
            paradigm=self.paradigm,
            schema_id=self.schema_id,
            schema_name=self.schema_name,
            hints=self.hints,
            source=self.source,
            target_problem=self.target.problem,
            answer_format=self.target.answer_format,
            mapping_objects=self.mapping.objects,
            shared_relations=self.mapping.shared_relations,
            lure=self.lure,
            chain=self.chain,
            hop=self.hop,
        )

    def gold_view(self) -> CaseGoldView:
        return CaseGoldView(
            id=self.id,
            target_answer=self.target.answer,
            copy_probe_answer=self.copy_probe.answer if self.copy_probe else None,
            lure_answer=self.lure.answer if self.lure else None,
        )
