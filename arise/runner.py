from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .graph import BeliefGraph
from .metrics import RoundJudgment, score
from .models import Claim, EpistemicStatus, Evidence


def run_scenario(path: Path) -> dict[str, Any]:
    scenario = json.loads(path.read_text())
    validate_scenario(scenario)
    fingerprint = hashlib.sha256(
        json.dumps(scenario, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    graph = BeliefGraph()
    judgments: list[RoundJudgment] = []

    for round_number, round_data in enumerate(scenario["rounds"], start=1):
        before = {claim.id for claim in graph.active_claims()}
        for raw in round_data.get("evidence", []):
            graph.add_evidence(Evidence(
                id=raw["id"], statement=raw["statement"], source=raw["source"],
                status=EpistemicStatus(raw["status"]), confidence=raw["confidence"],
                supports=raw.get("supports", True), round_seen=round_number,
            ))
        for raw in round_data.get("claims", []):
            graph.add_claim(_claim(raw, round_number))
        invalidated: list[str] = []
        for revision in round_data.get("revisions", []):
            invalidated.extend(graph.revise(
                revision["old_id"], _claim(revision["replacement"], round_number), revision["reason"],
            ))
        expected_invalidations = frozenset(round_data.get("expected_invalidations", []))
        judgments.append(RoundJudgment(
            contradiction_expected=bool(round_data.get("contradiction", False)),
            contradiction_detected=bool(round_data.get("revisions")),
            required_invalidations=expected_invalidations,
            actual_invalidations=frozenset(invalidated),
            conclusion_supported=all(
                parent in before or parent in graph.claims
                for claim in graph.active_claims() for parent in claim.depends_on
            ),
            tags_correct=sum(1 for raw in round_data.get("evidence", []) if raw["status"] in EpistemicStatus),
            tags_total=len(round_data.get("evidence", [])),
        ))
    return {
        "protocol_version": 1,
        "scenario": scenario["name"],
        "scenario_sha256": fingerprint,
        "rounds_evaluated": len(judgments),
        "metrics": score(judgments),
        "graph": graph.snapshot(),
    }


def validate_scenario(scenario: Any) -> None:
    if not isinstance(scenario, dict) or not isinstance(scenario.get("name"), str) or not scenario["name"].strip():
        raise ValueError("scenario requires a non-empty name")
    if not isinstance(scenario.get("rounds"), list) or not scenario["rounds"]:
        raise ValueError("scenario requires at least one round")
    evidence_ids: set[str] = set()
    claim_ids: set[str] = set()
    for number, round_data in enumerate(scenario["rounds"], start=1):
        if not isinstance(round_data, dict):
            raise ValueError(f"round {number} must be an object")
        for raw in round_data.get("evidence", []):
            required = {"id", "statement", "source", "status", "confidence"}
            if not required <= raw.keys():
                raise ValueError(f"round {number} evidence is missing required fields")
            if raw["id"] in evidence_ids:
                raise ValueError(f"duplicate evidence id: {raw['id']}")
            EpistemicStatus(raw["status"])
            if not 0 <= raw["confidence"] <= 1:
                raise ValueError("evidence confidence must be between 0 and 1")
            evidence_ids.add(raw["id"])
        for raw in round_data.get("claims", []):
            _validate_claim(raw, number, evidence_ids, claim_ids)
            claim_ids.add(raw["id"])
        for revision in round_data.get("revisions", []):
            if revision.get("old_id") not in claim_ids or revision.get("reason") not in evidence_ids:
                raise ValueError(f"round {number} revision references unknown claim or evidence")
            replacement = revision.get("replacement", {})
            _validate_claim(replacement, number, evidence_ids, claim_ids)
            claim_ids.add(replacement["id"])


def _validate_claim(raw: dict[str, Any], round_number: int, evidence_ids: set[str], claim_ids: set[str]) -> None:
    required = {"id", "statement", "status", "confidence"}
    if not required <= raw.keys():
        raise ValueError(f"round {round_number} claim is missing required fields")
    if raw["id"] in claim_ids:
        raise ValueError(f"duplicate claim id: {raw['id']}")
    EpistemicStatus(raw["status"])
    if not 0 <= raw["confidence"] <= 1:
        raise ValueError("claim confidence must be between 0 and 1")
    unknown_evidence = set(raw.get("evidence_ids", [])) - evidence_ids
    unknown_claims = set(raw.get("depends_on", [])) - claim_ids
    if unknown_evidence or unknown_claims:
        raise ValueError(f"round {round_number} claim references unavailable provenance")


def _claim(raw: dict[str, Any], round_number: int) -> Claim:
    return Claim(
        id=raw["id"], statement=raw["statement"], status=EpistemicStatus(raw["status"]),
        confidence=raw["confidence"], evidence_ids=raw.get("evidence_ids", []),
        depends_on=raw.get("depends_on", []), created_round=round_number,
    )
