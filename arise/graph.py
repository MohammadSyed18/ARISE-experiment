from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict
from typing import Iterable

from .models import Claim, ClaimState, Evidence


class BeliefGraph:
    """Directed claim graph with explicit evidence and invalidation propagation."""

    def __init__(self) -> None:
        self.claims: dict[str, Claim] = {}
        self.evidence: dict[str, Evidence] = {}
        self.children: dict[str, set[str]] = defaultdict(set)
        self.events: list[dict[str, object]] = []

    def add_evidence(self, item: Evidence) -> None:
        if item.id in self.evidence:
            raise ValueError(f"duplicate evidence id: {item.id}")
        self.evidence[item.id] = item
        self.events.append(
            {"type": "evidence_added", "id": item.id, "round": item.round_seen}
        )

    def add_claim(self, claim: Claim) -> None:
        if claim.id in self.claims:
            raise ValueError(f"duplicate claim id: {claim.id}")
        missing = [parent for parent in claim.depends_on if parent not in self.claims]
        if missing:
            raise ValueError(f"unknown dependencies: {missing}")
        unknown_evidence = [
            item for item in claim.evidence_ids if item not in self.evidence
        ]
        if unknown_evidence:
            raise ValueError(f"unknown evidence: {unknown_evidence}")
        self.claims[claim.id] = claim
        for parent in claim.depends_on:
            self.children[parent].add(claim.id)
        if self._has_cycle(claim.id):
            del self.claims[claim.id]
            for parent in claim.depends_on:
                self.children[parent].discard(claim.id)
            raise ValueError("dependency edge creates a cycle")
        self.events.append(
            {"type": "claim_added", "id": claim.id, "round": claim.created_round}
        )

    def revise(
        self, old_id: str, replacement: Claim, reason_evidence_id: str
    ) -> list[str]:
        old = self._active(old_id)
        if reason_evidence_id not in self.evidence:
            raise KeyError(reason_evidence_id)
        if replacement.revision_of not in (None, old_id):
            raise ValueError("replacement.revision_of must reference the old claim")
        previous_revision = replacement.revision_of
        replacement.revision_of = old_id
        try:
            self.add_claim(replacement)
        except (ValueError, KeyError):
            replacement.revision_of = previous_revision
            raise
        old.state = ClaimState.REVISED
        old.invalidated_by = reason_evidence_id
        invalidated = self.invalidate_descendants(old_id, reason_evidence_id)
        self.events.append(
            {
                "type": "claim_revised",
                "from": old_id,
                "to": replacement.id,
                "reason": reason_evidence_id,
            }
        )
        return invalidated

    def invalidate_descendants(self, claim_id: str, reason: str) -> list[str]:
        queue = deque(self.children.get(claim_id, ()))
        changed: list[str] = []
        while queue:
            current = queue.popleft()
            claim = self.claims[current]
            if claim.state == ClaimState.ACTIVE:
                claim.state = ClaimState.INVALIDATED
                claim.invalidated_by = reason
                changed.append(current)
                queue.extend(self.children.get(current, ()))
        return changed

    def active_claims(self) -> Iterable[Claim]:
        return (
            claim for claim in self.claims.values() if claim.state == ClaimState.ACTIVE
        )

    def confidence_from_evidence(self, evidence_ids: list[str]) -> float:
        """Combine independent evidence using noisy-OR, with opposing evidence reducing confidence."""
        support_miss = 1.0
        opposition_miss = 1.0
        for evidence_id in dict.fromkeys(evidence_ids):
            evidence = self.evidence[evidence_id]
            if evidence.supports:
                support_miss *= 1 - evidence.confidence
            else:
                opposition_miss *= 1 - evidence.confidence
        support = 1 - support_miss
        opposition = 1 - opposition_miss
        return round(max(0.0, min(1.0, support * (1 - opposition))), 4)

    def snapshot(self) -> dict[str, object]:
        return {
            "claims": [claim.to_dict() for claim in self.claims.values()],
            "evidence": [
                {**asdict(item), "status": item.status.value}
                for item in self.evidence.values()
            ],
            "events": self.events,
        }

    def _active(self, claim_id: str) -> Claim:
        claim = self.claims[claim_id]
        if claim.state != ClaimState.ACTIVE:
            raise ValueError(f"claim {claim_id} is not active")
        return claim

    def _has_cycle(self, start: str) -> bool:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            for parent in self.claims[node].depends_on:
                if visit(parent):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        return visit(start)
