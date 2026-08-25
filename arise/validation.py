"""Scenario parsing with contextual errors and reference checks before execution."""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

from .models import EpistemicStatus


class ScenarioError(ValueError):
    pass


def _text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScenarioError(f"{context}: expected nonempty text")
    return value


def _list(value: Any, context: str) -> list:
    if not isinstance(value, list):
        raise ScenarioError(f"{context}: expected a list")
    return value


def _record(value: Any, context: str) -> dict:
    if not isinstance(value, dict):
        raise ScenarioError(f"{context}: expected an object")
    return value


def _confidence(value: Any, context: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or not 0 <= value <= 1
    ):
        raise ScenarioError(f"{context}: confidence must be finite and between 0 and 1")


def _common(raw: dict, context: str) -> None:
    for key in ("id", "statement"):
        _text(raw.get(key), f"{context}.{key}")
    if raw.get("status") not in [item.value for item in EpistemicStatus]:
        raise ScenarioError(f"{context}.status: unknown epistemic status")
    _confidence(raw.get("confidence"), context)


def validate_scenario(value: Any) -> dict:
    """Validate without mutating caller input; dependency order is explicit in the format."""
    scenario = deepcopy(_record(value, "scenario"))
    _text(scenario.get("name"), "scenario.name")
    rounds = _list(scenario.get("rounds"), "scenario.rounds")
    if not 1 <= len(rounds) <= 1000:
        raise ScenarioError("scenario.rounds: expected 1..1000 rounds")
    evidence_ids: set[str] = set()
    claim_ids: set[str] = set()
    active: set[str] = set()
    parents: dict[str, set[str]] = {}

    def claim(raw: Any, context: str) -> str:
        raw = _record(raw, context)
        _common(raw, context)
        identifier = raw["id"]
        if identifier in claim_ids:
            raise ScenarioError(f"{context}: duplicate claim {identifier}")
        dependencies = _list(raw.get("depends_on", []), f"{context}.depends_on")
        attached = _list(raw.get("evidence_ids", []), f"{context}.evidence_ids")
        for dependency in dependencies:
            _text(dependency, context)
            if dependency not in active:
                raise ScenarioError(
                    f"{context}: unknown or inactive dependency {dependency}"
                )
        for identifier_e in attached:
            _text(identifier_e, context)
            if identifier_e not in evidence_ids:
                raise ScenarioError(f"{context}: unknown evidence {identifier_e}")
        if len(set(dependencies)) != len(dependencies) or len(set(attached)) != len(
            attached
        ):
            raise ScenarioError(f"{context}: duplicate reference")
        claim_ids.add(identifier)
        active.add(identifier)
        parents[identifier] = set(dependencies)
        return identifier

    for number, data in enumerate(rounds, 1):
        context = f"round {number}"
        _record(data, context)
        if "contradiction" in data and type(data["contradiction"]) is not bool:
            raise ScenarioError(f"{context}.contradiction: expected boolean")
        for raw in _list(data.get("evidence", []), context + ".evidence"):
            _record(raw, context + ".evidence")
            _common(raw, context + ".evidence")
            _text(raw.get("source"), context + ".evidence.source")
            if "expected_status" in raw and raw["expected_status"] not in [
                item.value for item in EpistemicStatus
            ]:
                raise ScenarioError(f"{context}: invalid expected_status")
            if type(raw.get("supports", True)) is not bool:
                raise ScenarioError(f"{context}.evidence.supports: expected boolean")
            if raw["id"] in evidence_ids:
                raise ScenarioError(f"{context}: duplicate evidence {raw['id']}")
            evidence_ids.add(raw["id"])
        for raw in _list(data.get("claims", []), context + ".claims"):
            claim(raw, context + ".claim")
        for revision in _list(data.get("revisions", []), context + ".revisions"):
            _record(revision, context + ".revision")
            old = _text(revision.get("old_id"), context + ".revision.old_id")
            reason = _text(revision.get("reason"), context + ".revision.reason")
            if old not in active or reason not in evidence_ids:
                raise ScenarioError(
                    f"{context}: revision requires an active claim and known evidence"
                )
            affected = {old}
            while True:
                expanded = affected | {
                    identifier
                    for identifier, dependencies in parents.items()
                    if dependencies & affected
                }
                if expanded == affected:
                    break
                affected = expanded
            replacement = _record(revision.get("replacement"), context + ".replacement")
            if any(item in affected for item in replacement.get("depends_on", [])):
                raise ScenarioError(
                    f"{context}: replacement depends on the claim being invalidated"
                )
            active.difference_update(affected)
            claim(replacement, context + ".replacement")
        expected = _list(
            data.get("expected_invalidations", []), context + ".expected_invalidations"
        )
        if any(
            not isinstance(identifier, str) or identifier not in claim_ids
            for identifier in expected
        ):
            raise ScenarioError(
                f"{context}: expected invalidation references an unknown claim"
            )
    return scenario
