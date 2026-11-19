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
    manifest["scripts"]["test:e2e"] = _node_e2e_script(manifest["scripts"])
    return {
        "version": plan.resolution.versions["node"],
        "typescript": "typescript" in ids,
        "package_json": json.dumps(manifest, indent=2),
        "threshold": threshold,
    }


NODE_E2E = "node --test e2e/*.e2e.mjs"
PYTHON_E2E = {"pytest": 'python -m pytest e2e -o addopts=""', "unittest": "python -m unittest discover -s e2e -v"}
E2E_NOT_APPLICABLE = {
    "web": "Navigateur : NON APPLICABLE tant qu'aucune interface n'existe (squelette sans code metier).",
    "api": "HTTP : NON APPLICABLE tant qu'aucun serveur ni aucune route n'existe (squelette sans code metier).",
    "cli": "Ligne de commande : NON APPLICABLE tant qu'aucune commande n'est declaree (squelette sans code metier).",
    "library": "Parcours utilisateur : sans objet pour une bibliotheque ; le temoin verifie le paquet livre.",
}


def _node_e2e_script(scripts):
    """Le temoin E2E Node s'execute sur le livrable : apres le build s'il existe."""
    return ("npm run build && " + NODE_E2E) if "build" in scripts else NODE_E2E


def _e2e(plan):
    """Socle de bout en bout (E08) avec les outils deja retenus : aucune dependance ajoutee,
    aucun scenario metier. NON APPLICABLE explicite quand aucun lanceur n'est disponible."""
    ids = plan.resolution.ids()
    steps, commands, reasons, runner = [], [], [], None
    if "python" in ids:
        runner = next((name for name in ("pytest", "unittest") if name in ids), None)
        if runner:
            commands.append(PYTHON_E2E[runner])
            steps += [{"name": "Installation du livrable (non editable)", "lines": ['python -m pip install ".[dev]"']},
                      {"name": "Bout en bout Python (%s, paquet installe)" % runner, "lines": [PYTHON_E2E[runner]]}]
        else:
            reasons.append("Python : NON APPLICABLE, aucun lanceur de tests retenu (pytest ou unittest).")
    if "node" in ids:
        commands.append("npm run test:e2e")
        steps += [{"name": "Installation des dependances (Node.js)", "lines": [NODE_CI_INSTALL]},
                  {"name": "Bout en bout Node.js (node --test, livrable)", "lines": ["npm run test:e2e"]}]
    return {
        "applicable": bool(steps),
        "python": runner is not None,
        "node": "node" in ids,
        "commands": commands,
        "steps": steps,
        "not_applicable": reasons + [E2E_NOT_APPLICABLE[plan.spec.project_type]],
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


HOOK_KINDS = {"pre_commit": ("format", "lint"), "pre_push": ("typecheck", "test")}


def _hook_steps(plan, kinds):
    """Etapes des hooks Git : outils Python directs, scripts npm pour Node (une etape par type)."""
    steps, npm_kinds = [], []
    for kind in kinds:
        for tech in plan.resolution.technologies:
            command = tech.commands.get(kind, "")
            if not command or tech.category in EXCLUDED_CATEGORIES:
                continue
            if command.startswith(("npx ", "node ")):
                if kind not in npm_kinds:
                    npm_kinds.append(kind)
                    steps.append({
                        "label": "%s (npm run %s)" % (CI_LABELS[kind], kind),
                        "guard": '[ -d node_modules ] || fail "dependances npm absentes : executer npm install"',
                        "command": "npm run --silent %s" % kind,
                    })
                continue
            tool = command.split()[0]
            steps.append({
                "label": "%s (%s)" % (CI_LABELS[kind], tech.name),
                "guard": 'command -v %s >/dev/null 2>&1 || fail "%s introuvable : activer l\'environnement du projet"' % (tool, tool),
                "command": command,
            })
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
        "hooks": {stage: _hook_steps(plan, kinds) for stage, kinds in HOOK_KINDS.items()},
        "e2e": _e2e(plan),
    }
