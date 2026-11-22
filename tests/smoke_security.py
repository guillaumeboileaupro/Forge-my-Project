"""Preuve que les controles de securite generes detectent de vrais problemes.

    python3 tests/smoke_security.py [python|node]

Pour chaque scenario, un projet est genere a partir d'un profil predefini,
un probleme est injecte (secret, code dangereux, dependance vulnerable), puis
les etapes du job concerne sont executees : l'etape attendue DOIT echouer.
Un scenario temoin sans injection doit reussir. Le faux secret est fabrique
a l'execution : aucun secret, meme factice, n'est stocke dans ce depot.
Necessite le reseau (PyPI, npm, GitHub).
"""
import json
import random
import shutil
import string
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smoke_generated import (commit_all, environment, generate, parse_workflow, profiles_by_id,  # noqa: E402
                             run_steps, runner_dir, write_project)


def fake_github_token():
    alphabet = string.ascii_letters + string.digits
    return "ghp" + "_" + "".join(random.SystemRandom().choice(alphabet) for _ in range(36))


def inject_secret(root, files):
    (root / "config.txt").write_text("token=%s\n" % fake_github_token(), encoding="utf-8")


def inject_shell_injection(root, files):
    package = next(p.split("/")[1] for p in files if p.startswith("src/") and p.endswith("__init__.py"))
    (root / "src" / package / "danger.py").write_text(
        '"""Code volontairement dangereux."""\n\nimport subprocess\n\n\n'
        "def run(command: str) -> int:\n    return subprocess.call(command, shell=True)\n", encoding="utf-8")


def inject_vulnerable_python_dependency(root, files):
    pyproject = root / "pyproject.toml"
    pyproject.write_text(pyproject.read_text(encoding="utf-8").replace(
        "dependencies = [\n", 'dependencies = [\n  "urllib3==1.24.1",\n', 1), encoding="utf-8")


def inject_vulnerable_npm_dependency(root, files):
    path = root / "package.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest.setdefault("dependencies", {})["lodash"] = "4.17.15"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def inject_eval(root, files):
    entry = "src/index.ts" if "src/index.ts" in files else "src/index.js"
    (root / entry).write_text("export function run(code: string): unknown {\n  return eval(code);\n}\n"
                              if entry.endswith(".ts") else "export function run(code) {\n  return eval(code);\n}\n",
                              encoding="utf-8")


def inject_dangerous_script(root, files):
    """Hors de src/ (non couvert par Bandit) : seul Semgrep, qui analyse tout le depot, doit le voir."""
    (root / "scripts" / "deploy_helper.py").write_text(
        '"""Script volontairement dangereux."""\n\nimport os\n\n\n'
        "def deploy(target: str) -> int:\n    return os.system(\"rsync -a dist/ \" + target)\n", encoding="utf-8")


def inject_vulnerable_image(root, files):
    """Image de base en fin de vie, aux vulnerabilites hautes et critiques connues."""
    (root / "Dockerfile").write_text("FROM python:3.6-slim\nCOPY src /app/src\n", encoding="utf-8")


def with_docker(profile):
    answers = dict(profile["answers"], technologies=list(profile["answers"]["technologies"]) + ["docker"])
    return dict(profile, id=profile["id"] + "-docker", answers=answers)


SCENARIOS = {
    "python": ("python-api-fastapi", [
        ("temoin", None, "security", None),
        ("secret", inject_secret, "security", "Secrets"),
        ("injection shell", inject_shell_injection, "security", "SAST Python"),
        ("dependance vulnerable", inject_vulnerable_python_dependency, "security", "Audit des dependances Python"),
        ("script dangereux hors src (Semgrep)", inject_dangerous_script, "security", "SAST multi-langage"),
    ]),
    "node": ("typescript-api-express", [
        ("temoin", None, "security", None),
        ("dependance vulnerable", inject_vulnerable_npm_dependency, "security", "Audit des dependances npm"),
        ("eval", inject_eval, "quality", "Lint"),
        ("eval (Semgrep)", inject_eval, "security", "SAST multi-langage"),
    ]),
    "docker": ("python-api-fastapi", [
        ("temoin sans Dockerfile", None, "security", None),
        ("image vulnerable", inject_vulnerable_image, "security", "Analyse de l'image conteneur"),
    ]),
}


def scenario(profile, label, inject, job, expected):
    answers, files = generate(profile, verify=False)
    root = Path(tempfile.mkdtemp(prefix="forge-security-"))
    try:
        write_project(files, root)
        if inject:
            inject(root, files)
        commit_all(root)
        env = environment(root, answers)
        steps = parse_workflow(files[".github/workflows/ci.yml"])[job]
        failed = run_steps(steps, root, env, "%s/%s" % (profile["id"], label), stop_after=expected)
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(runner_dir(root), ignore_errors=True)
    if expected is None and failed:
        raise SystemExit("Temoin en echec (%s) : etape %s" % (profile["id"], failed))
    if expected and not (failed or "").startswith(expected):
        raise SystemExit("Probleme NON DETECTE (%s) : attendu un echec de '%s', obtenu %r" % (label, expected, failed))
    print("[%s] %s : %s" % (profile["id"], label, "detecte par " + failed if failed else "PASS"), flush=True)


def main(argv=None):
    stacks = (argv if argv is not None else sys.argv[1:]) or sorted(SCENARIOS)
    profiles = profiles_by_id()
    for stack in stacks:
        profile_id, cases = SCENARIOS[stack]
        profile = with_docker(profiles[profile_id]) if stack == "docker" else profiles[profile_id]
        for label, inject, job, expected in cases:
            scenario(profile, label, inject, job, expected)
    return 0


if __name__ == "__main__":
    sys.exit(main())
