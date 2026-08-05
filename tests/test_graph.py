import unittest

from arise.graph import BeliefGraph
from arise.models import Claim, ClaimState, EpistemicStatus, Evidence


class BeliefGraphTests(unittest.TestCase):
    def test_revision_invalidates_downstream_claims(self) -> None:
        graph = BeliefGraph()
        graph.add_evidence(Evidence("e1", "initial", "lab", EpistemicStatus.MEASURED, .8))
        graph.add_evidence(Evidence("e2", "counter", "lab", EpistemicStatus.MEASURED, .9, False))
        graph.add_claim(Claim("c1", "parent", EpistemicStatus.INFERRED, .7, ["e1"]))
        graph.add_claim(Claim("c2", "child", EpistemicStatus.SPECULATIVE, .5, depends_on=["c1"]))
        invalidated = graph.revise(
            "c1", Claim("c3", "replacement", EpistemicStatus.INFERRED, .85, ["e2"]), "e2"
        )
        self.assertEqual(invalidated, ["c2"])
        self.assertEqual(graph.claims["c2"].state, ClaimState.INVALIDATED)

    def test_noisy_or_confidence_accounts_for_opposition(self) -> None:
        graph = BeliefGraph()
        graph.add_evidence(Evidence("a", "support", "x", EpistemicStatus.MEASURED, .8))
        graph.add_evidence(Evidence("b", "oppose", "y", EpistemicStatus.MEASURED, .5, False))
        self.assertEqual(graph.confidence_from_evidence(["a", "b"]), .4)


if __name__ == "__main__":
    unittest.main()

