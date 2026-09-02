from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Condition(StrEnum):
    TARGET_ONLY = "target-only"
    RANDOM_SOURCE = "random-source"
    WITH_LURE = "with-lure"
    WITH_SOURCE = "with-source"
    H1_SOURCE_PROBLEM = "h1-source-problem"
    H2_SCHEMA_NAME = "h2-schema-name"
    H3_ORACLE_MINDSET = "h3-oracle-mindset"
    H3_FALSE_MINDSET = "h3-false-mindset"
    H4_SOURCE_SOLUTION = "h4-source-solution"
    H5_MAPPING = "h5-mapping"
    WITH_SKILL = "with-skill"
    HOP_TRANSFER = "hop-transfer"
    PREFIX_TRANSFER = "prefix-transfer"


class PromptContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_case_id: str | None = None
    reference_problem: str | None = None
    reference_solution: str | None = None
    reference_answer: str | None = None
    skill_library: str | None = None
    prefix_material: list[str] = Field(default_factory=list)


class PromptArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    condition: Condition
    system: str
    user: str
    template_version: str
    prompt_sha256: str
    metadata: dict[str, str | int | None] = Field(default_factory=dict)
