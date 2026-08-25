from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .graph import BeliefGraph
from .analysis import graph_health
from .metrics import RoundJudgment, score
from .models import Claim, ClaimState, EpistemicStatus, Evidence
from .validation import validate_scenario


def run_scenario(path: Path, *, policy: str = "revision") -> dict[str, Any]:
    return run_data(json.loads(path.read_text()), policy=policy)


def apply_round(
    graph: BeliefGraph, data: dict, number: int, *, policy: str
) -> tuple[BeliefGraph, list[str]]:
    """Stage a complete round on a copy so a failed revision cannot alter its input."""
    if policy not in {"revision", "static"}:
        raise ValueError("policy must be revision or static")
    candidate = deepcopy(graph)
    for raw in data.get("evidence", []):
        candidate.add_evidence(
            Evidence(
                id=raw["id"],
                statement=raw["statement"],
                source=raw["source"],
                status=EpistemicStatus(raw["status"]),
                confidence=raw["confidence"],
                supports=raw.get("supports", True),
                round_seen=number,
            )
        )
    for raw in data.get("claims", []):
        candidate.add_claim(_claim(raw, number))
    invalidated: list[str] = []
    for revision in data.get("revisions", []):
        replacement = _claim(revision["replacement"], number)
        if policy == "revision":
            invalidated.extend(
                candidate.revise(revision["old_id"], replacement, revision["reason"])
            )
        else:
            # Keep prior beliefs while admitting the same new candidate claim.
            candidate.add_claim(replacement)
    return candidate, invalidated


def run_data(value: dict, *, policy: str = "revision") -> dict[str, Any]:
    if policy not in {"revision", "static"}:
        raise ValueError("policy must be revision or static")
    scenario = validate_scenario(value)
    graph = BeliefGraph()
    judgments: list[RoundJudgment] = []
    trace = []
    expected_inactive: set[str] = set()
    for number, data in enumerate(scenario["rounds"], start=1):
        previous_events = len(graph.events)
        graph, invalidated = apply_round(graph, data, number, policy=policy)
        expected = frozenset(data.get("expected_invalidations", []))
        expected_inactive.update(expected)
        expected_inactive.update(
            revision["old_id"] for revision in data.get("revisions", [])
        )
        supported = all(
            claim.id not in expected_inactive
            and all(
                graph.claims[parent].state == ClaimState.ACTIVE
                for parent in claim.depends_on
            )
            for claim in graph.active_claims()
        )
        judgments.append(
            RoundJudgment(
                contradiction_expected=data.get("contradiction", False),
                contradiction_detected=policy == "revision"
                and bool(data.get("revisions")),
                required_invalidations=expected,
                actual_invalidations=frozenset(invalidated),
                conclusion_supported=supported,
                # Tag checking measures consistency with optional independent labels.
                tags_correct=sum(
                    raw["status"] == raw.get("expected_status", raw["status"])
                    for raw in data.get("evidence", [])
                ),
                tags_total=len(data.get("evidence", [])),
            )
        )
        trace.append(
            {
                "round": number,
                "invalidated": sorted(set(invalidated)),
                "expected_invalidations": sorted(expected),
                "supported": supported,
                "health": graph_health(graph),
                "events": deepcopy(graph.events[previous_events:]),
            }
        )
    return {
        "scenario": scenario["name"],
        "policy": policy,
        "metrics": score(judgments),
        "graph": graph.snapshot(),
        "rounds": trace,
        "evaluation_notes": "Revision instructions and invalidation labels are supplied by scenarios. Missing expected_status labels measure schema consistency, not independent tagging accuracy.",
    }


def _claim(raw: dict[str, Any], round_number: int) -> Claim:
    return Claim(
        id=raw["id"],
        statement=raw["statement"],
        status=EpistemicStatus(raw["status"]),
        confidence=raw["confidence"],
        evidence_ids=raw.get("evidence_ids", []),
        depends_on=raw.get("depends_on", []),
        created_round=round_number,
    )
