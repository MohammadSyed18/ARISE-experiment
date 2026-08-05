import json
import tempfile
import unittest
from pathlib import Path

from arise.runner import run_scenario


class RunnerTests(unittest.TestCase):
    def test_artifact_is_reproducible_and_fingerprinted(self) -> None:
        scenario = Path(__file__).parents[1] / "scenarios" / "drug_discovery.json"
        first = run_scenario(scenario)
        second = run_scenario(scenario)
        self.assertEqual(first, second)
        self.assertEqual(len(first["scenario_sha256"]), 64)
        self.assertEqual(first["rounds_evaluated"], 3)

    def test_invalid_forward_provenance_is_rejected(self) -> None:
        value = {"name": "invalid", "rounds": [{"claims": [{
            "id": "c1", "statement": "claim", "status": "inferred", "confidence": .5,
            "evidence_ids": ["later"]
        }]}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario.json"
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "unavailable provenance"):
                run_scenario(path)


if __name__ == "__main__":
    unittest.main()
