"""Execute la CI generee pour des profils predefinis (preuve que les pipelines passent).

    python3 tests/smoke_generated.py [--verify] [profil ...]

Pour chaque profil : rendu via le moteur, ecriture dans un dossier temporaire
(jamais dans un projet existant), environnement isole (venv Python / npm local),
puis execution, dans l'ordre, des etapes `run` du workflow genere.
Necessite le reseau (PyPI, npm). Sortie non nulle au premier echec.
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

RUN_BLOCK = re.compile(r"^        run: \|\n          (.+)$", re.M)
DEFAULT_PROFILES = ()  # vide : tous les profils predefinis


def workflow_commands(workflow):
    return RUN_BLOCK.findall(workflow)


def write_project(files, root):
    for path, content in files.items():
        target = resolve_inside(root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def environment(root, answers):
    env = dict(os.environ)
    if "python" in answers["technologies"]:
        try:
            venv.EnvBuilder(with_pip=True).create(root / ".venv")
        except subprocess.CalledProcessError:
            if not shutil.which("uv"):  # interpreteur sans ensurepip (ex. Python gere par uv)
                raise
            subprocess.run(["uv", "venv", "--clear", "--seed", "--python", sys.executable, str(root / ".venv")], check=True)
        env["PATH"] = str(root / ".venv" / "bin") + os.pathsep + env["PATH"]
        env["VIRTUAL_ENV"] = str(root / ".venv")
    return env


def smoke(profile, verify):
    answers = dict(profile["answers"], name="smoke-" + profile["id"][:40])
    if "python" in answers["technologies"]:
        current = "%d.%d" % sys.version_info[:2]
        answers["versions"] = dict(answers["versions"], python=current)
    result = run(answers, verify=verify)
    if not result.as_dict()["ok"]:
        raise SystemExit("Generation refusee pour %s : %s" % (profile["id"], result.as_dict()["diagnostics"]))
    root = Path(tempfile.mkdtemp(prefix="forge-smoke-"))
    try:
        write_project(result.files, root)
        env = environment(root, answers)
        for command in workflow_commands(result.files[".github/workflows/ci.yml"]):
            print("[%s] $ %s" % (profile["id"], command), flush=True)
            completed = subprocess.run(["bash", "-eo", "pipefail", "-c", command], cwd=root, env=env, check=False)
            if completed.returncode:
                raise SystemExit("Echec de l'etape '%s' pour %s (code %d)" % (command, profile["id"], completed.returncode))
        print("[%s] PASS" % profile["id"], flush=True)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("profiles", nargs="*", default=list(DEFAULT_PROFILES))
    parser.add_argument("--verify", action="store_true", help="verification en ligne et versions epinglees")
    args = parser.parse_args(argv)
    profiles = {p["id"]: p for p in load_predefined(load_catalog())}
    for profile_id in args.profiles or sorted(profiles):
        smoke(profiles[profile_id], args.verify)
    return 0


if __name__ == "__main__":
    sys.exit(main())
