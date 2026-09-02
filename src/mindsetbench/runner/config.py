from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from mindsetbench.models.prompt import Condition


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    conditions: list[Condition] = Field(min_length=1)
    samples_per_item: int = Field(default=1, ge=1)
    seed: int = 0
    temperature: float = Field(default=0.0, ge=0.0)
    max_output_tokens: int = Field(default=2048, ge=1)
    concurrency: int = Field(default=4, ge=1)
    max_retries: int = Field(default=2, ge=0, le=10)
    request_timeout_seconds: float = Field(default=180.0, gt=0, le=3600)
