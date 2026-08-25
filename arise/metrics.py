from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoundJudgment:
    contradiction_expected: bool
    contradiction_detected: bool
    required_invalidations: frozenset[str]
    actual_invalidations: frozenset[str]
    conclusion_supported: bool
    tags_correct: int
    tags_total: int


def score(judgments: list[RoundJudgment]) -> dict[str, float]:
    expected = sum(j.contradiction_expected for j in judgments)
    detected = sum(
        j.contradiction_expected and j.contradiction_detected for j in judgments
    )
    required = {
        (round_index, claim)
        for round_index, j in enumerate(judgments)
        for claim in j.required_invalidations
    }
    actual = {
        (round_index, claim)
        for round_index, j in enumerate(judgments)
        for claim in j.actual_invalidations
    }
    intersection = required & actual
    precision = (
        len(intersection) / len(actual) if actual else (1.0 if not required else 0.0)
    )
    recall = len(intersection) / len(required) if required else 1.0
    revision_accuracy = (
        2 * precision * recall / (precision + recall) if precision + recall else 0.0
    )
    supported = sum(j.conclusion_supported for j in judgments)
    tags_correct = sum(j.tags_correct for j in judgments)
    tags_total = sum(j.tags_total for j in judgments)
    return {
        "contradiction_detection_rate": (
            round(detected / expected, 4) if expected else 1.0
        ),
        "belief_revision_accuracy": round(revision_accuracy, 4),
        "reasoning_drift_score": (
            round(1 - supported / len(judgments), 4) if judgments else 0.0
        ),
        "epistemic_tagging_precision": (
            round(tags_correct / tags_total, 4) if tags_total else 1.0
        ),
    }
