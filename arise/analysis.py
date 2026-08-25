"""Inspectable provenance, dependency health, and counterfactual impact."""

from __future__ import annotations

from collections import deque
from math import isfinite
from .graph import BeliefGraph
from .models import ClaimState


def dependency_order(graph: BeliefGraph) -> list[str]:
    indegree = {
        identifier: len(set(claim.depends_on))
        for identifier, claim in graph.claims.items()
    }
    ready = deque(
        sorted(identifier for identifier, count in indegree.items() if count == 0)
    )
    ordered = []
    while ready:
        identifier = ready.popleft()
        ordered.append(identifier)
        for child in sorted(graph.children.get(identifier, ())):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if len(ordered) != len(graph.claims):
        raise ValueError("claim graph contains a cycle or missing dependency")
    return ordered


def explain(graph: BeliefGraph, identifier: str) -> dict:
    if identifier not in graph.claims:
        raise KeyError(identifier)
    ancestors: set[str] = set()
    queue = deque([identifier])
    while queue:
        current = queue.popleft()
        if current in ancestors:
            continue
        ancestors.add(current)
        queue.extend(graph.claims[current].depends_on)
    ordered = [item for item in dependency_order(graph) if item in ancestors]
    evidence_ids = sorted(
        {item for claim_id in ordered for item in graph.claims[claim_id].evidence_ids}
    )
    sources: dict[str, list[str]] = {}
    for evidence_id in evidence_ids:
        item = graph.evidence[evidence_id]
        sources.setdefault(item.source, []).append(evidence_id)
    inactive = [
        item for item in ordered if graph.claims[item].state != ClaimState.ACTIVE
    ]
    return {
        "claim": graph.claims[identifier].to_dict(),
        "dependency_order": ordered,
        "evidence_ids": evidence_ids,
        "sources": sources,
        "inactive_dependencies": [item for item in inactive if item != identifier],
        "unsupported_roots": [
            item
            for item in ordered
            if not graph.claims[item].evidence_ids and not graph.claims[item].depends_on
        ],
        "revisions": [
            event.copy()
            for event in graph.events
            if event.get("type") == "claim_revised"
            and (event.get("from") in ancestors or event.get("to") in ancestors)
        ],
    }


def revision_impact(graph: BeliefGraph, identifier: str) -> dict:
    """Preview a revision without changing claims or appending events."""
    if identifier not in graph.claims:
        raise KeyError(identifier)
    seen = {identifier}
    queue = deque(sorted(graph.children.get(identifier, ())))
    descendants = []
    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        descendants.append(current)
        queue.extend(sorted(graph.children.get(current, ())))
    active = [
        item for item in descendants if graph.claims[item].state == ClaimState.ACTIVE
    ]
    leaves = [item for item in active if not graph.children.get(item)]
    return {
        "claim_id": identifier,
        "descendants": descendants,
        "would_invalidate": active,
        "affected_conclusions": leaves,
    }


def source_adjusted_confidence(graph: BeliefGraph, evidence_ids: list[str]) -> dict:
    """Group correlated evidence by source, taking the strongest item per polarity.

    This is a sensitivity heuristic rather than a calibrated probability model.
    """
    groups: dict[str, dict[str, float]] = {}
    for identifier in dict.fromkeys(evidence_ids):
        evidence = graph.evidence[identifier]
        if not isfinite(evidence.confidence):
            raise ValueError("nonfinite evidence confidence")
        group = groups.setdefault(evidence.source, {"support": 0.0, "opposition": 0.0})
        key = "support" if evidence.supports else "opposition"
        group[key] = max(group[key], evidence.confidence)
    miss = 1.0
    unopposed = 1.0
    for group in groups.values():
        miss *= 1 - group["support"]
        unopposed *= 1 - group["opposition"]
    return {
        "confidence": round((1 - miss) * unopposed, 4),
        "independent_sources": len(groups),
        "groups": groups,
    }


def graph_health(graph: BeliefGraph) -> dict:
    ordered = dependency_order(graph)
    depths = {}
    for identifier in ordered:
        depths[identifier] = 1 + max(
            (depths[parent] for parent in graph.claims[identifier].depends_on),
            default=0,
        )
    active = list(graph.active_claims())
    stale = [
        claim.id
        for claim in active
        if any(
            graph.claims[parent].state != ClaimState.ACTIVE
            for parent in claim.depends_on
        )
    ]
    return {
        "claims": len(graph.claims),
        "active": len(active),
        "evidence": len(graph.evidence),
        "edges": sum(len(set(claim.depends_on)) for claim in graph.claims.values()),
        "maximum_depth": max(depths.values(), default=0),
        "stale_active_claims": stale,
        "unsupported_active_roots": [
            claim.id
            for claim in active
            if not claim.depends_on and not claim.evidence_ids
        ],
    }
