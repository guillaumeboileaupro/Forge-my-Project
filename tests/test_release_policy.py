"""Politique de maintenance et de releases (E05) : controles documentaires executes par la CI.

Verifie le format du changelog, la coherence des statuts E01-E18 entre TODO.md et
docs/ROADMAP_2026.md, leurs dependances, la couverture des jalons et l'alignement de la
liste de controle des releases sur les vrais jobs CI.
"""
import datetime
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"TODO", "IN PROGRESS", "BLOCKED", "DONE"}
TASKS = ["E%02d" % n for n in range(1, 19)]
SUBLOT = re.compile(r"^(E\d\d)([a-z])$")  # sous-lot d'une tache, ex. E17a : memes controles que la tache
SECTIONS = {"Ajoute", "Modifie", "Deprecie", "Supprime", "Corrige", "Securite"}
VERSION = re.compile(r"^## \[(\d+)\.(\d+)\.(\d+)\] - (\d{4}-\d{2}-\d{2})$")


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def task_rows(text, columns):
    """{ID: cellules} pour les lignes E01-E18 (et leurs sous-lots E17a...) d'un tableau a `columns` colonnes."""
    rows = {}
    for line in text.splitlines():
        if re.match(r"^\| E\d\d[a-z]? \|", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != columns:
                raise AssertionError("%s : %d colonnes au lieu de %d" % (cells[0], len(cells), columns))
            if cells[0] in rows:
                raise AssertionError("%s en double" % cells[0])
            rows[cells[0]] = cells
    return rows


def ci_jobs():
    """Noms affiches des jobs CI (nom explicite, sinon identifiant)."""
    jobs, current = [], None
    workflow = read(".github/workflows/ci.yml").split("\njobs:\n", 1)[1]
    for line in workflow.splitlines():
        job = re.match(r"^  ([A-Za-z0-9_-]+):$", line)
        if job:
            current = job.group(1)
            jobs.append(current)
        name = re.match(r"^    name: (.+)$", line)
        if name and current:
            jobs[-1] = name.group(1).strip()
    return jobs


class ChangelogTests(unittest.TestCase):
    def test_keep_a_changelog_format(self):
        lines = read("CHANGELOG.md").splitlines()
        self.assertEqual(lines[0], "# Changelog")
        headers = [l for l in lines if l.startswith("## ")]
        self.assertEqual(headers[0], "## [Unreleased]", "Unreleased doit preceder les versions")
        versions = []
        for header in headers[1:]:
            match = VERSION.match(header)
            self.assertIsNotNone(match, "en-tete de version invalide : " + header)
            date = datetime.date.fromisoformat(match.group(4))
            self.assertLessEqual(date, datetime.date.today(), "version datee dans le futur : " + header)
            versions.append(tuple(int(match.group(i)) for i in (1, 2, 3)))
        self.assertEqual(versions, sorted(versions, reverse=True), "versions en ordre decroissant")
        self.assertEqual(len(versions), len(set(versions)), "version en double")
        for line in lines:
            if line.startswith("### "):
                self.assertIn(line[4:].strip(), SECTIONS, "rubrique inconnue : " + line)


class TaskTrackingTests(unittest.TestCase):
    def setUp(self):
        self.todo = task_rows(read("TODO.md"), 10)
        self.roadmap = task_rows(read("docs/ROADMAP_2026.md"), 10)

    def ids(self):
        return TASKS + sorted(set(self.todo) - set(TASKS))

    def test_every_task_is_tracked_in_both_documents(self):
        self.assertEqual(sorted(self.todo), sorted(self.roadmap))
        self.assertEqual(sorted(t for t in self.todo if t in TASKS), TASKS)
        for task in set(self.todo) - set(TASKS):
            match = SUBLOT.match(task)
            self.assertIsNotNone(match, "identifiant de tache invalide : " + task)
            self.assertIn(match.group(1), TASKS, task + " : tache parente inconnue")

    def test_sublots_never_outrun_their_parent(self):
        for task in set(self.todo) - set(TASKS):
            parent = SUBLOT.match(task).group(1)
            raw = self.todo[task][3]
            self.assertNotIn(parent, [d.strip() for d in raw.split(",")], task + " ne peut dependre de sa parente")
            if self.todo[parent][8] == "DONE":
                self.assertEqual(self.todo[task][8], "DONE", "%s DONE avant son sous-lot %s" % (parent, task))

    def test_statuses_are_valid_and_identical(self):
        for task in self.ids():
            todo, roadmap = self.todo[task][8], self.roadmap[task][8]
            self.assertIn(todo, STATUSES, task)
            self.assertEqual(todo, roadmap, "%s : TODO.md=%s, ROADMAP=%s" % (task, todo, roadmap))

    def test_dependencies_exist_and_done_tasks_have_done_dependencies(self):
        for task in self.ids():
            raw = self.todo[task][3]
            deps = [] if raw == "-" else [d.strip() for d in raw.split(",")]
            self.assertEqual(deps, [] if self.roadmap[task][4] == "-" else
                             [d.strip() for d in self.roadmap[task][4].split(",")], task)
            for dep in deps:
                self.assertIn(dep, self.ids(), "%s depend d'une tache inconnue %s" % (task, dep))
                if self.todo[task][8] in ("IN PROGRESS", "DONE"):
                    self.assertNotEqual(self.todo[dep][8], "TODO", "%s demarre avant %s" % (task, dep))
                if self.todo[task][8] == "DONE":
                    self.assertEqual(self.todo[dep][8], "DONE", "%s termine avant %s" % (task, dep))

    def test_agent_time_is_never_recorded_as_human_time(self):
        for task in self.ids():
            human = self.todo[task][6]
            self.assertNotRegex(human, r"(?i)claude|codex|agent|IA", task)
            if self.todo[task][7] not in ("-", "non calculable"):
                self.assertNotIn(human, ("-", "non renseigne"), "%s : ecart sans temps humain" % task)


class ReleasePlanTests(unittest.TestCase):
    def test_every_task_belongs_to_a_milestone(self):
        plan = read("docs/RELEASES.md")
        for version in ("## v1.0.0", "## v1.1.0", "## v2.0.0"):
            self.assertIn(version, plan)
        for task in sorted(task_rows(read("TODO.md"), 10)):  # taches et sous-lots
            self.assertRegex(plan, r"\b%s\b" % task, task + " absente du plan des releases")

    def test_release_checklist_names_the_real_ci_jobs(self):
        policy = read("docs/MAINTENANCE.md")
        section = policy.split("## 6.")[1].split("## 7.")[0]
        jobs = ci_jobs()
        self.assertTrue(jobs, "aucun job CI lu")
        for job in jobs:
            self.assertIn("`%s`" % job, section, "job CI absent de la liste de controle : " + job)
        self.assertIn("Les %d jobs CI" % len(jobs), section)

    def test_no_release_claimed_without_changelog_entry(self):
        plan, changelog = read("docs/RELEASES.md"), read("CHANGELOG.md")
        published = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.M)
        if not published:
            self.assertIn("Aucune version n'est publiee", plan)


if __name__ == "__main__":
    unittest.main()
