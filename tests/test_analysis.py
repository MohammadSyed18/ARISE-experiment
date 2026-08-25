import unittest
from copy import deepcopy
from pathlib import Path

from arise.analysis import (
    explain,
    graph_health,
    revision_impact,
    source_adjusted_confidence,
)
from arise.graph import BeliefGraph
from arise.models import Claim, Evidence, EpistemicStatus as Status
from arise.runner import run_scenario, run_data, apply_round
from arise.validation import validate_scenario, ScenarioError
from arise.benchmark import benchmark, paired_interval
from arise.report import render_report


class AnalysisTests(unittest.TestCase):
    def graph(self):
        graph = BeliefGraph()
        for identifier in ("e1", "e2"):
            graph.add_evidence(
                Evidence(identifier, "Measured", "same-lab", Status.MEASURED, 0.8)
            )
        graph.add_claim(Claim("a", "Root", Status.INFERRED, 0.8, ["e1", "e2"]))
        graph.add_claim(Claim("b", "Middle", Status.INFERRED, 0.7, depends_on=["a"]))
        graph.add_claim(
            Claim("c", "Conclusion", Status.SPECULATIVE, 0.6, depends_on=["b"])
        )
        return graph

    def test_provenance_and_impact_are_read_only(self):
        graph = self.graph()
        before = deepcopy(graph.snapshot())
        self.assertEqual(explain(graph, "c")["dependency_order"], ["a", "b", "c"])
        self.assertEqual(revision_impact(graph, "a")["would_invalidate"], ["b", "c"])
        self.assertEqual(graph_health(graph)["maximum_depth"], 3)
        self.assertEqual(graph.snapshot(), before)

    def test_source_grouping_avoids_double_counting_same_lab(self):
        graph = self.graph()
        result = source_adjusted_confidence(graph, ["e1", "e2", "e1"])
        self.assertEqual(result["confidence"], 0.8)
        self.assertEqual(result["independent_sources"], 1)

    def test_invalid_replacement_leaves_graph_unchanged(self):
        graph = self.graph()
        before = deepcopy(graph.snapshot())
        with self.assertRaises(ValueError):
            graph.revise(
                "a",
                Claim("new", "Bad revision", Status.INFERRED, 0.7, depends_on=["c"]),
                "e1",
            )
        self.assertEqual(graph.snapshot(), before)

    def test_round_failure_does_not_add_partial_evidence(self):
        graph = self.graph()
        before = deepcopy(graph.snapshot())
        bad = {
            "evidence": [
                {
                    "id": "new",
                    "statement": "New",
                    "source": "lab",
                    "status": "measured",
                    "confidence": 0.7,
                }
            ],
            "claims": [
                {
                    "id": "x",
                    "statement": "Bad",
                    "status": "inferred",
                    "confidence": 0.6,
                    "depends_on": ["missing"],
                }
            ],
        }
        with self.assertRaises(ValueError):
            apply_round(graph, bad, 2, policy="revision")
        self.assertEqual(graph.snapshot(), before)


class ScenarioTests(unittest.TestCase):
    path = Path(__file__).parents[1] / "scenarios/drug_discovery.json"

    def test_static_baseline_retains_invalid_beliefs(self):
        revision = run_scenario(self.path)
        static = run_scenario(self.path, policy="static")
        self.assertGreater(
            revision["metrics"]["belief_revision_accuracy"],
            static["metrics"]["belief_revision_accuracy"],
        )
        self.assertLess(
            revision["metrics"]["reasoning_drift_score"],
            static["metrics"]["reasoning_drift_score"],
        )
        self.assertEqual(revision["rounds"][1]["invalidated"], ["c2"])

    def test_schema_errors_have_round_context(self):
        import json

        raw = json.loads(self.path.read_text())
        raw["rounds"][0]["evidence"][0]["confidence"] = float("nan")
        with self.assertRaisesRegex(ScenarioError, "round 1"):
            validate_scenario(raw)
        raw["rounds"][0]["evidence"][0]["confidence"] = 0.5
        raw["rounds"][0]["claims"][0]["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(ScenarioError, "unknown evidence"):
            run_data(raw)

    def test_benchmark_seed_and_report_escaping(self):
        first = benchmark([self.path], seed=19, samples=100)
        self.assertEqual(first, benchmark([self.path], seed=19, samples=100))
        self.assertEqual(paired_interval([0.5], samples=100)["lower"], 0.5)
        result = run_scenario(self.path)
        result["graph"]["claims"][0]["statement"] = "<script>alert(1)</script>"
        html = render_report(result)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("Round 2", html)


if __name__ == "__main__":
    unittest.main()
