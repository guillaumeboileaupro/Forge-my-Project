"""E07 : fusion automatique a trois voies et garde-fous d'ecriture."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forge.filesystem import bases, workflow, writer
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
        self.env = mock.patch.dict(os.environ, {"FORGE_WRITE_ROOT": str(self.root),
                                                "FORGE_STATE_DIR": str(self.root / "state")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.dest = self.root / "project"
        self.path = "README.md"
        self.base = "titre\nligne\nfin\n"
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
        bases.forget(str(self.dest))
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
        bases.forget(str(self.dest))
        with self.assertRaises(workflow.StaleValidation):
            workflow.write_destination(str(self.dest), self.files, self.files, compared["token"],
                                       {self.path: {"action": "auto"}}, True)
        bases.record(str(self.dest), {self.path: self.base})
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

    def write(self, files, decisions):
        compared = workflow.compare_destination(str(self.dest), files)
        return workflow.write_destination(str(self.dest), files, files, compared["token"], decisions, True)

    def test_base_survives_a_server_restart(self):
        # Le magasin est sur disque : un nouveau processus (cle HMAC differente) retrouve la base.
        with mock.patch.object(workflow, "_KEY", os.urandom(32)):
            entry = workflow.compare_destination(str(self.dest), self.files)["entries"][0]
        self.assertTrue(entry["base_available"])
        self.assertEqual(entry["auto_merge"], "titre local\nligne\nfin generee\n")

    def test_tampered_or_foreign_base_is_ignored(self):
        store = bases.store_dir() / (bases._digest(str(self.dest)) + ".json")
        store.write_text(store.read_text().replace("titre\\nligne", "titre\\nLIGNE"))  # empreinte fausse
        entry = workflow.compare_destination(str(self.dest), self.files)["entries"][0]
        self.assertFalse(entry["base_available"])
        other = self.root / "autre"
        store.write_text('{"schema_version": 1, "destination": "%s", "files": {}}' % other)
        self.assertEqual(bases.load(str(self.dest), [self.path]), {})

    def test_store_is_private(self):
        store = bases.store_dir()
        self.assertEqual(store.stat().st_mode & 0o777, 0o700)
        for item in store.iterdir():
            self.assertEqual(item.stat().st_mode & 0o777, 0o600)

    def test_concurrent_change_after_compare_blocks_auto_merge(self):
        compared = workflow.compare_destination(str(self.dest), self.files)
        (self.dest / self.path).write_text("modifie entre-temps\n")
        with self.assertRaises(workflow.StaleValidation):
            workflow.write_destination(str(self.dest), self.files, self.files, compared["token"],
                                       {self.path: {"action": "auto"}}, True)
        self.assertEqual((self.dest / self.path).read_text(), "modifie entre-temps\n")

    def test_permissions_of_user_file_are_kept_on_auto_merge(self):
        os.chmod(self.dest / self.path, 0o600)
        self.write(self.files, {self.path: {"action": "auto"}})
        self.assertEqual((self.dest / self.path).stat().st_mode & 0o777, 0o600)

    def test_generated_script_stays_executable_with_user_mode(self):
        hook = ".githooks/pre-commit"
        (self.dest / ".githooks").mkdir()
        (self.dest / hook).write_text("#!/bin/sh\nexit 1\n")
        os.chmod(self.dest / hook, 0o640)
        self.write({hook: "#!/bin/sh\nexit 0\n"}, {hook: {"action": "replace"}})
        self.assertEqual((self.dest / hook).stat().st_mode & 0o777, 0o750)

    def test_rollback_restores_bytes_and_mode_after_partial_write(self):
        other = "docs/NOTES.md"
        (self.dest / "docs").mkdir()
        (self.dest / other).write_text("notes\n")
        os.chmod(self.dest / self.path, 0o600)
        before = (self.dest / self.path).read_bytes()
        files = dict(self.files, **{other: "notes generees\n"})
        compared = workflow.compare_destination(str(self.dest), files)
        real, calls = writer._commit, []

        def failing(dir_fd, name, data, mode):
            if data == b"notes generees\n":  # cible NOTES (pas sa sauvegarde) : README est deja ecrit
                raise OSError(28, "disque plein")
            calls.append((name, bytes(data)))
            return real(dir_fd, name, data, mode)

        with mock.patch.object(writer, "_commit", failing), self.assertRaises(writer.WriteFailure) as caught:
            workflow.write_destination(str(self.dest), files, files, compared["token"],
                                       {self.path: {"action": "auto"}, other: {"action": "replace"}}, True)
        self.assertIn(("README.md", b"titre local\nligne\nfin generee\n"), calls)  # fusion ecrite puis annulee
        self.assertEqual(caught.exception.report["status"], "restored")
        self.assertEqual((self.dest / self.path).read_bytes(), before)
        self.assertEqual((self.dest / self.path).stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.dest / other).read_text(), "notes\n")
        # Echec : la base n'est pas remplacee par le contenu non ecrit.
        self.assertEqual(bases.load(str(self.dest), [self.path]), {self.path: self.base})

    def test_successful_write_records_new_base(self):
        report = self.write(self.files, {self.path: {"action": "auto"}})
        self.assertEqual(report["merge_bases"], "enregistrees")
        self.assertEqual(bases.load(str(self.dest), [self.path]), self.files)

    def test_kept_file_keeps_previous_base(self):
        self.write(self.files, {self.path: {"action": "keep"}})
        self.assertEqual(bases.load(str(self.dest), [self.path]), {self.path: self.base})


class MergeRegressionTests(unittest.TestCase):
    def test_identical_change_on_both_sides_is_applied_once(self):
        result = three_way_merge("a\nb\nc\n", "a\nX\nb\nc\n", "a\nX\nb\nc\nd\n")
        self.assertEqual(result.content, "a\nX\nb\nc\nd\n")
        result = three_way_merge("a\nb\nc\n", "a\nZ\nc\n", "a\nZ\nc\nd\n")
        self.assertEqual(result.content, "a\nZ\nc\nd\n")

    def test_conflict_reports_base_lines_and_both_sides(self):
        result = three_way_merge("a\nb\nc\n", "a\nlocal\nc\n", "a\ngenere\nc\n")
        self.assertEqual(result.conflicts, ({"base_start": 2, "base_end": 2, "current": "local\n",
                                              "generated": "genere\n"},))

    def test_adjacent_edit_and_insertion_is_a_conflict_not_a_guess(self):
        result = three_way_merge("a\nb\n", "a\nB\n", "a\nb\nc\n")
        self.assertFalse(result.clean)


if __name__ == "__main__":
    unittest.main()
