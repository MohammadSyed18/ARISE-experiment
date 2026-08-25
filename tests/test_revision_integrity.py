import unittest
from arise.graph import BeliefGraph
from arise.models import Claim, ClaimState, Evidence, EpistemicStatus
from arise.metrics import RoundJudgment, score


class RevisionIntegrity(unittest.TestCase):
    def test_invalid_replacement_leaves_original_active(self):
        graph = BeliefGraph()
        graph.add_evidence(
            Evidence("e", "observation", "source", EpistemicStatus.MEASURED, 0.8)
        )
        old = Claim("a", "original", EpistemicStatus.INFERRED, 0.5)
        graph.add_claim(old)
        replacement = Claim(
            "b", "revision", EpistemicStatus.INFERRED, 0.6, depends_on=["missing"]
        )
        before = list(graph.events)
        with self.assertRaises(ValueError):
            graph.revise("a", replacement, "e")
        self.assertEqual(old.state, ClaimState.ACTIVE)
        self.assertIsNone(old.invalidated_by)
        self.assertIsNone(replacement.revision_of)
        self.assertEqual(graph.events, before)

    def test_duplicate_evidence_is_not_independent_support(self):
        graph = BeliefGraph()
        graph.add_evidence(
            Evidence("e", "observation", "source", EpistemicStatus.MEASURED, 0.8)
        )
        self.assertEqual(graph.confidence_from_evidence(["e", "e"]), 0.8)

    def test_metrics_do_not_match_invalidations_across_rounds(self):
        rounds = [
            RoundJudgment(False, False, frozenset({"a"}), frozenset(), True, 1, 1),
            RoundJudgment(False, False, frozenset(), frozenset({"a"}), True, 1, 1),
        ]
        self.assertEqual(score(rounds)["belief_revision_accuracy"], 0)
