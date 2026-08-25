import json, tempfile, unittest
from copy import deepcopy
from pathlib import Path
from hashlib import sha256
from arise.archive import (
    create_archive,
    verify_archive,
    save_archive,
    load_archive,
    compare_archives,
    canonical,
)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.scenario = json.loads(
            (
                Path(__file__).parents[1] / "scenarios/sensor_calibration.json"
            ).read_text()
        )

    def test_roundtrip_and_read_only_replay(self):
        archive = create_archive(self.scenario)
        before = deepcopy(archive)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.json"
            save_archive(path, archive)
            self.assertEqual(load_archive(path), archive)
        result = verify_archive(archive)
        result["scenario"] = "modified"
        self.assertEqual(archive, before)

    def test_digest_and_recomputed_digest_cannot_hide_changed_results(self):
        archive = create_archive(self.scenario)
        archive["payload"]["result"]["scenario"] = "wrong"
        with self.assertRaisesRegex(ValueError, "digest"):
            verify_archive(archive)
        archive["sha256"] = sha256(canonical(archive["payload"])).hexdigest()
        with self.assertRaisesRegex(ValueError, "replay"):
            verify_archive(archive)

    def test_policy_comparison_shows_revision_changes(self):
        report = compare_archives(
            create_archive(self.scenario),
            create_archive(self.scenario, policy="static"),
        )
        self.assertTrue(report["same_scenario"])
        self.assertTrue(report["changed_claims"])
