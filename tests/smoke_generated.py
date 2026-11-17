"""Execute la CI generee pour des profils predefinis (preuve que les pipelines passent).

    python3 tests/smoke_generated.py [--verify] [profil ...]

Pour chaque profil : rendu via le moteur, ecriture dans un dossier temporaire
(jamais dans un projet existant), depot Git local avec un commit (Gitleaks
analyse l'historique), environnement isole (venv Python / npm local), puis
execution, job par job et dans l'ordre, des etapes `run` du workflow genere.
Les etapes `uses` (checkout, setup-*, upload-artifact) sont fournies par
l'environnement local. Necessite le reseau (PyPI, npm, GitHub). Sortie non
nulle au premier echec.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forge.config.catalog import load_catalog  # noqa: E402
from forge.config.profiles import load_predefined  # noqa: E402
from forge.generator.paths import resolve_inside  # noqa: E402
from forge.pipeline import run  # noqa: E402

JOB = re.compile(r"^  ([a-z][a-z0-9-]*):$")
STEP = re.compile(r"^      - name: (.+)$")
RUN_LINE = "          "
GIT_ENV = {"GIT_AUTHOR_NAME": "forge-smoke", "GIT_AUTHOR_EMAIL": "smoke@localhost",
           "GIT_COMMITTER_NAME": "forge-smoke", "GIT_COMMITTER_EMAIL": "smoke@localhost"}


def parse_workflow(text):
    """Retourne {job: [(nom d'etape, [lignes du bloc run])]} ; les etapes `uses` sont ignorees."""
    jobs, job, step, in_run = {}, None, None, False
    for line in text.splitlines():
        if JOB.match(line):
            job, in_run = JOB.match(line).group(1), False
            jobs[job] = []
        elif job and STEP.match(line):
            step, in_run = STEP.match(line).group(1), False
        elif job and line.strip() == "run: |":
            jobs[job].append((step, []))
            in_run = True
        elif in_run and line.startswith(RUN_LINE):
            jobs[job][-1][1].append(line[len(RUN_LINE):])
        else:
            in_run = False
    return jobs


def generate(profile, verify, name=None):
    answers = dict(profile["answers"], name=name or "smoke-" + profile["id"][:40])
    if "python" in answers["technologies"]:
        answers["versions"] = dict(answers["versions"], python="%d.%d" % sys.version_info[:2])
    result = run(answers, verify=verify)
    if not result.as_dict()["ok"]:
        raise SystemExit("Generation refusee pour %s : %s" % (profile["id"], result.as_dict()["diagnostics"]))
    return answers, result.files


def write_project(files, root):
    for path, content in files.items():
        target = resolve_inside(root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        if path.startswith((".githooks/", "scripts/hooks/")):
            target.chmod(0o755)


def commit_all(root, message="smoke"):
    env = dict(os.environ, **GIT_ENV)
    if not (root / ".git").exists():
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", message], cwd=root, check=True, env=env)


def environment(root, answers):
    env = dict(os.environ, RUNNER_TEMP=str(root / ".runner"))
    # Evenement GitHub de Forge-my-Project : etranger au depot genere (job attribution).
    for key in ("GITHUB_EVENT_NAME", "GITHUB_EVENT_PATH"):
        env.pop(key, None)
    (root / ".runner").mkdir(exist_ok=True)
    if "python" in answers["technologies"]:
        target = root / ".runner" / "venv"
        try:
            venv.EnvBuilder(with_pip=True).create(target)
        except subprocess.CalledProcessError:
            if not shutil.which("uv"):  # interpreteur sans ensurepip fiable (ex. Python gere par uv)
                raise
            subprocess.run(["uv", "venv", "--clear", "--seed", "--python", sys.executable, str(target)], check=True)
        env["PATH"] = str(target / "bin") + os.pathsep + env["PATH"]
        env["VIRTUAL_ENV"] = str(target)
    return env


def run_steps(steps, root, env, label, stop_after=None):
    """Execute les etapes ; retourne le nom de la premiere etape en echec, ou None."""
    for name, lines in steps:
        print("[%s] %s" % (label, name), flush=True)
        script = "\n".join(lines)
        if subprocess.run(["bash", "-eo", "pipefail", "-c", script], cwd=root, env=env, check=False).returncode:
            return name
        if stop_after and name.startswith(stop_after):
            return None
    return None


def smoke(profile, verify):
    answers, files = generate(profile, verify)
    root = Path(tempfile.mkdtemp(prefix="forge-smoke-"))
    try:
        write_project(files, root)
        commit_all(root)
        env = environment(root, answers)
        for job, steps in parse_workflow(files[".github/workflows/ci.yml"]).items():
            failed = run_steps(steps, root, env, "%s/%s" % (profile["id"], job))
            if failed:
                raise SystemExit("Echec de l'etape '%s' (job %s) pour %s" % (failed, job, profile["id"]))
        for hook in ("pre-commit", "pre-push"):  # hooks Git generes, avec les outils reels installes
            print("[%s] hook %s" % (profile["id"], hook), flush=True)
            if subprocess.run([str(root / ".githooks" / hook)], cwd=root, env=env, check=False).returncode:
                raise SystemExit("Echec du hook %s pour %s" % (hook, profile["id"]))
        print("[%s] PASS" % profile["id"], flush=True)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def profiles_by_id():
    return {p["id"]: p for p in load_predefined(load_catalog())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("profiles", nargs="*")
    parser.add_argument("--verify", action="store_true", help="verification en ligne et versions epinglees")
    args = parser.parse_args(argv)
    profiles = profiles_by_id()
    for profile_id in args.profiles or sorted(profiles):
        smoke(profiles[profile_id], args.verify)
    return 0


if __name__ == "__main__":
    sys.exit(main())
