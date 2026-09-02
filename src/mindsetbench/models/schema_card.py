from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mindsetbench.models.case import Paradigm


class SchemaCard(BaseModel):
    """Authoring contract shared by all cases that instantiate one schema."""

    model_config = ConfigDict(extra="forbid")

    schema_id: str = Field(min_length=1)
    paradigm: Paradigm
    thread: str = Field(min_length=1)
    name: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    required_relations: list[str] = Field(min_length=1)
    invalid_variants: list[str] = Field(min_length=1)
    level_plan: dict[str, str]
    copy_probe: str = Field(min_length=1)
    lure: str = Field(min_length=1)
    verifier: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_all_levels(self) -> SchemaCard:
        expected = {f"L{level}" for level in range(5)}
        if set(self.level_plan) != expected:
            raise ValueError(f"level_plan must contain exactly {sorted(expected)}")
        return self

    @property
    def thread_code(self) -> str:
        return self.thread.split("-", 1)[0]
