"""E07 : fusion automatique a trois voies et garde-fous d'ecriture."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forge.filesystem import workflow, writer
from forge.filesystem.merge import three_way_merge


class MergeAlgorithmTests(unittest.TestCase):
    def test_simple_generated_change(self):
        result = three_way_merge("a\nb\n", "a\nb\n", "a\nB\n")
        self.assertTrue(result.clean)
        self.assertEqual(result.content, "a\nB\n")

    def test_independent_concurrent_changes(self):
        result = three_way_merge("a\nb\nc\n", "A\nb\nc\n", "a\nb\nC\n")
        self.assertTrue(result.clean)
        self.assertEqual(result.content, "A\nb\nC\n")

    def test_same_lines_conflict(self):
        result = three_way_merge("a\nb\n", "a\nlocal\n", "a\ngenere\n")
        self.assertFalse(result.clean)
        self.assertEqual(len(result.conflicts), 1)
        self.assertIn("local", result.conflicts[0]["current"])


class WorkflowMergeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.env = mock.patch.dict(os.environ, {"FORGE_WRITE_ROOT": str(self.root)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.dest = self.root / "project"
        self.path = "README.md"
        self.base = "titre\nligne\nfin\n"
        workflow._BASES.clear()
        initial = {self.path: self.base}
        compared = workflow.compare_destination(str(self.dest), initial)
        workflow.write_destination(str(self.dest), initial, initial, compared["token"], {}, True)
        (self.dest / self.path).write_text("titre local\nligne\nfin\n")
        self.files = {self.path: "titre\nligne\nfin generee\n"}

    def test_clean_merge_is_proposed_then_explicitly_applied(self):
        compared = workflow.compare_destination(str(self.dest), self.files)
        entry = compared["entries"][0]
        self.assertEqual(entry["auto_merge"], "titre local\nligne\nfin generee\n")
        self.assertIn("titre local", entry["diff"])
        report = workflow.write_destination(str(self.dest), self.files, self.files, compared["token"],
                                            {self.path: {"action": "auto"}}, True)
        self.assertEqual((self.dest / self.path).read_text(), entry["auto_merge"])
        self.assertEqual(report["summary"]["merged"], 1)
        self.assertTrue((self.dest / report["backup"] / self.path).is_file())

    def test_absent_base_requires_manual_resolution(self):
        workflow._BASES.clear()
        compared = workflow.compare_destination(str(self.dest), self.files)
        entry = compared["entries"][0]
        self.assertFalse(entry["base_available"])
        self.assertIsNone(entry["auto_merge"])
        with self.assertRaises(workflow.DecisionError):
            workflow.write_destination(str(self.dest), self.files, self.files, compared["token"],
                                       {self.path: {"action": "auto"}}, True)

    def test_overlapping_change_requires_manual_resolution(self):
        generated = {self.path: "titre genere\nligne\nfin\n"}
        compared = workflow.compare_destination(str(self.dest), generated)
        entry = compared["entries"][0]
        self.assertTrue(entry["base_available"])
        self.assertIsNone(entry["auto_merge"])
        self.assertTrue(entry["merge_conflicts"])

    def test_base_and_destination_are_revalidated(self):
        compared = workflow.compare_destination(str(self.dest), self.files)
        workflow._BASES.clear()
        with self.assertRaises(workflow.StaleValidation):
            workflow.write_destination(str(self.dest), self.files, self.files, compared["token"],
                                       {self.path: {"action": "auto"}}, True)
        workflow._BASES[str(self.dest)] = {self.path: self.base}
        (self.dest / self.path).write_text("concurrent\n")
        with self.assertRaises(workflow.StaleValidation):
            workflow.write_destination(str(self.dest), self.files, self.files, compared["token"],
                                       {self.path: {"action": "auto"}}, True)

    def test_merged_secret_is_refused(self):
        secret_current = "titre local ghp_" + "a" * 36 + "\nligne\nfin\n"
        (self.dest / self.path).write_text(secret_current)
        compared = workflow.compare_destination(str(self.dest), self.files)
        self.assertIsNotNone(compared["entries"][0]["auto_merge"])
        with self.assertRaises(ValueError):
            workflow.write_destination(str(self.dest), self.files, self.files, compared["token"],
                                       {self.path: {"action": "auto"}}, True)

    def test_write_failure_rolls_back_auto_merge(self):
        compared = workflow.compare_destination(str(self.dest), self.files)
        before = (self.dest / self.path).read_bytes()
        with mock.patch.object(writer, "_commit", side_effect=OSError(28, "full")), self.assertRaises(writer.WriteFailure):
            workflow.write_destination(str(self.dest), self.files, self.files, compared["token"],
                                       {self.path: {"action": "auto"}}, True)
        self.assertEqual((self.dest / self.path).read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
