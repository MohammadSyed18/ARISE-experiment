from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from math import isfinite
from typing import Any


class EpistemicStatus(StrEnum):
    MEASURED = "measured"
    INFERRED = "inferred"
    SPECULATIVE = "speculative"


class ClaimState(StrEnum):
    ACTIVE = "active"
    REVISED = "revised"
    INVALIDATED = "invalidated"


@dataclass(frozen=True)
class Evidence:
    id: str
    statement: str
    source: str
    status: EpistemicStatus
    confidence: float
    supports: bool = True
    round_seen: int = 0

    def __post_init__(self) -> None:
        if (
            not isinstance(self.id, str)
            or not self.id.strip()
            or not isinstance(self.statement, str)
            or not self.statement.strip()
        ):
            raise ValueError("id and statement must be nonempty strings")
        if not isinstance(self.status, EpistemicStatus):
            raise ValueError("status must be an EpistemicStatus")
        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not isfinite(self.confidence)
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")


@dataclass
class Claim:
    id: str
    statement: str
    status: EpistemicStatus
    confidence: float
    evidence_ids: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    state: ClaimState = ClaimState.ACTIVE
    revision_of: str | None = None
    invalidated_by: str | None = None
    created_round: int = 0

    def __post_init__(self) -> None:
        if (
            not isinstance(self.id, str)
            or not self.id.strip()
            or not isinstance(self.statement, str)
            or not self.statement.strip()
        ):
            raise ValueError("id and statement must be nonempty strings")
        if not isinstance(self.status, EpistemicStatus):
            raise ValueError("status must be an EpistemicStatus")
        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not isfinite(self.confidence)
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be between 0 and 1")
        if self.id in self.depends_on:
            raise ValueError("claim cannot depend on itself")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        value["state"] = self.state.value
        return value
