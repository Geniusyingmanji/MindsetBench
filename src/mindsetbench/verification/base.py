from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VerificationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    passed: bool
    expected: str
    actual: str
    detail: str | None = None


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    checks: list[VerificationCheck] = Field(default_factory=list)
    verifier: str

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)
