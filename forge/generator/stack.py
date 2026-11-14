"""Contexte des fichiers de pile : manifestes, configurations d'outils et CI (T12).

Les versions de packages ne sont fixees que si la verification en ligne les a
confirmees (PASS) ; sinon le manifeste reste non contraint et la dependance
est signalee NON VERIFIE dans docs/DEPENDENCIES.md.
"""
import json
import re
from pathlib import Path

from forge import CATALOGS_DIR
from forge.diagnostics import Status
from forge.security.controls import security_context

ACTION_SHA = re.compile(r"^[0-9a-f]{40}$")
# L'audit des dependances est execute par le job security (forge/security) : pas de doublon.
CI_KINDS = ("install", "format", "lint", "typecheck", "test", "build")
CI_LABELS = {
    "install": "Installation des dependances", "format": "Formatage", "lint": "Lint", "typecheck": "Typage",
    "test": "Tests et couverture", "audit": "Audit des dependances", "build": "Build",
}
# Etape d'installation Node en CI : reproductible (npm ci) des que le lockfile est versionne.
NODE_CI_INSTALL = "if [ -f package-lock.json ]; then npm ci; else npm install; fi"
EXCLUDED_CATEGORIES = {"deployment"}  # le deploiement n'est jamais execute par la CI generee


class CiCatalogError(ValueError):
    pass


def load_ci_catalog(path=None):
    data = json.loads(Path(path or CATALOGS_DIR / "ci" / "actions.json").read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise CiCatalogError("catalogs/ci/actions.json : schema_version non supporte")
    for key, action in data.get("actions", {}).items():
        if not ACTION_SHA.fullmatch(action.get("sha", "")) or not re.fullmatch(r"actions/[a-z-]+", action.get("repository", "")):
            raise CiCatalogError("Action %s : depot ou SHA complet invalide" % key)
    threshold = data.get("coverage_threshold")
    if not isinstance(threshold, int) or not 0 <= threshold <= 100:
        raise CiCatalogError("coverage_threshold invalide")
    return data


def _verified_version(verification, ecosystem, package):
    if verification is None:
        return None
    status, details = verification.package_status(ecosystem, package)
    return details.get("version") if status is Status.PASS else None


def _packages(plan, ecosystem, verification):
    """Retourne (execution, developpement) : listes de (package, version verifiee ou None)."""
    ids = plan.resolution.ids()
    runtime, dev = [], []
    for tech in plan.resolution.technologies:
        if tech.ecosystem != ecosystem:
            continue
        entries = [(tech.package, tech.dev)]
        entries += [(package, True) for package, when in tech.companions if not when or ids.intersection(when)]
        for package, is_dev in entries:
            item = (package, _verified_version(verification, ecosystem, package))
            (dev if is_dev else runtime).append(item)
    return runtime, dev


def _pep508(item):
    package, version = item
    return package + (">=" + version if version else "")


def _npm_range(version):
    return "^" + version if version else "latest"


def _node_scripts(plan):
    """Scripts npm deduits des commandes Node du catalogue (npx/node), hors deploiement."""
    scripts = {}
    for kind in ("test", "lint", "format", "typecheck", "build"):
        commands = []
        for tech in plan.resolution.technologies:
            command = tech.commands.get(kind, "")
            if tech.category not in EXCLUDED_CATEGORIES and command.startswith(("npx ", "node ")):
                commands.append(command[4:] if command.startswith("npx ") else command)
        if commands:
            scripts[kind] = " && ".join(commands)
    return scripts


def _python(plan, verification, threshold):
    if "python" not in plan.resolution.ids():
        return None
    ids = plan.resolution.ids()
    runtime, dev = _packages(plan, "pypi", verification)
    version = plan.resolution.versions["python"]
    return {
        "version": version,
        "target": "py" + version.replace(".", ""),
        "runtime": [_pep508(i) for i in runtime],
        "dev": [_pep508(i) for i in dev],
        "has_tests": bool(ids & {"pytest", "unittest"}),
        "coverage": "pytest-cov" in ids,
        "ruff": "ruff" in ids,
        "mypy": "mypy" in ids,
        "threshold": threshold,
    }


def _node(plan, verification, threshold):
    ids = plan.resolution.ids()
    if "node" not in ids:
        return None
    runtime, dev = _packages(plan, "npm", verification)
    manifest = {
        "name": plan.spec.name,
        "version": "0.1.0",
        "private": True,
        "type": "module",
        "engines": {"node": ">=" + plan.resolution.versions["node"]},
        "scripts": _node_scripts(plan),
    }
    if runtime:
        manifest["dependencies"] = {name: _npm_range(v) for name, v in sorted(runtime)}
    if dev:
        manifest["devDependencies"] = {name: _npm_range(v) for name, v in sorted(dev)}
    return {
        "version": plan.resolution.versions["node"],
        "typescript": "typescript" in ids,
        "package_json": json.dumps(manifest, indent=2),
        "threshold": threshold,
    }


def _ci_steps(plan):
    steps = []
    for kind in CI_KINDS:
        for tech in plan.resolution.technologies:
            command = tech.commands.get(kind)
            if not command or tech.category in EXCLUDED_CATEGORIES:
                continue
            if kind == "install" and tech.id == "node":
                command = NODE_CI_INSTALL
            steps.append({"name": "%s (%s)" % (CI_LABELS[kind], tech.name), "lines": [command]})
    return steps


def stack_context(plan, verification=None, ci_catalog=None):
    ci_catalog = ci_catalog or load_ci_catalog()
    threshold = ci_catalog["coverage_threshold"]
    return {
        "python": _python(plan, verification, threshold),
        "node": _node(plan, verification, threshold),
        "ci": {
            "actions": ci_catalog["actions"],
            "verified_at": ci_catalog["verified_at"],
            "steps": _ci_steps(plan),
        },
        "security": security_context(plan),
    }
