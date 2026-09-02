from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mindsetbench.models.prompt import Condition, PromptArtifact


class PartGrade(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int
    correct: bool
    predicted: str | None
    expected: str
    reason: str | None = None


class GradeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correct: bool
    extracted: str | None
    normalized_parts: list[str] = Field(default_factory=list)
    part_results: list[PartGrade] = Field(default_factory=list)
    expected_part_count: int | None = Field(default=None, ge=0)
    parsed_part_count: int | None = Field(default=None, ge=0)
    parse_error: str | None = None
    matched_copy_probe: bool = False
    matched_lure_answer: bool = False


class ModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str
    prompt: PromptArtifact
    temperature: float = 0.0
    max_output_tokens: int = 2048
    seed: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int = 0
    provider_request_id: str | None = None
    finish_reason: str | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class TrialRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: str
    case_id: str
    schema_id: str
    level: int
    paradigm: str
    model: str
    condition: Condition
    sample_index: int
    seed: int | None
    prompt: PromptArtifact
    response: ModelResponse
    grade: GradeResult
    has_copy_probe: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
