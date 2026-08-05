from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .graph import BeliefGraph
from .metrics import RoundJudgment, score
from .models import Claim, EpistemicStatus, Evidence


def run_scenario(path: Path) -> dict[str, Any]:
    scenario = json.loads(path.read_text())
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
    return {"scenario": scenario["name"], "metrics": score(judgments), "graph": graph.snapshot()}


def _claim(raw: dict[str, Any], round_number: int) -> Claim:
    return Claim(
        id=raw["id"], statement=raw["statement"], status=EpistemicStatus(raw["status"]),
        confidence=raw["confidence"], evidence_ids=raw.get("evidence_ids", []),
        depends_on=raw.get("depends_on", []), created_round=round_number,
    )

