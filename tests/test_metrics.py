import unittest

from arise.metrics import RoundJudgment, score


class MetricTests(unittest.TestCase):
    def test_perfect_revision(self) -> None:
        result = score([RoundJudgment(True, True, frozenset({"c2"}), frozenset({"c2"}), True, 3, 3)])
        self.assertEqual(result["belief_revision_accuracy"], 1.0)
        self.assertEqual(result["reasoning_drift_score"], 0.0)


if __name__ == "__main__":
    unittest.main()

