"""Controles de securite des projets generes (T13).

Decrit le job CI `security` (secrets, SAST, audit des dependances, SBOM) a
partir de catalogs/security/tools.json, et la couverture de chaque controle.
Un controle impossible pour la pile choisie est NON VERIFIE (avertissement),
jamais omis silencieusement. Aucun contournement n'est genere : pas de
`continue-on-error`, pas de `|| true`, pas d'exclusion implicite.
"""
import json
import re
from pathlib import Path

from forge import CATALOGS_DIR
from forge import diagnostics as d

SHA256 = re.compile(r"^[0-9a-f]{64}$")
VERSION = re.compile(r"^\d+(\.\d+){1,3}$")
TOOLS_ENV = '"$RUNNER_TEMP/forge-security"'


class SecurityCatalogError(ValueError):
    pass


def load_security_tools(path=None):
    data = json.loads(Path(path or CATALOGS_DIR / "security" / "tools.json").read_text(encoding="utf-8"))
    gitleaks = data.get("gitleaks", {})
    if data.get("schema_version") != 1:
        raise SecurityCatalogError("catalogs/security/tools.json : schema_version non supporte")
    if not SHA256.fullmatch(gitleaks.get("sha256", "")) or not VERSION.fullmatch(gitleaks.get("version", "")):
        raise SecurityCatalogError("Gitleaks : version ou empreinte SHA-256 invalide")
    if gitleaks.get("asset") != "gitleaks_%s_linux_x64.tar.gz" % gitleaks["version"]:
        raise SecurityCatalogError("Gitleaks : nom d'archive incoherent avec la version")
    for name, version in data.get("pypi", {}).items():
        if not VERSION.fullmatch(version):
            raise SecurityCatalogError("Outil %s : version non epinglee" % name)
    if set(data.get("pypi", {})) != {"bandit", "pip-audit", "cyclonedx-bom"}:
        raise SecurityCatalogError("Outils Python attendus : bandit, pip-audit, cyclonedx-bom")
    return data


def _gitleaks_step(tool):
    url = "https://github.com/%s/releases/download/v%s/%s" % (tool["repository"], tool["version"], tool["asset"])
    return {"name": "Secrets (Gitleaks %s, historique complet)" % tool["version"], "lines": [
        'curl -sSfL -o "$RUNNER_TEMP/gitleaks.tar.gz" ' + url,
        'echo "%s  $RUNNER_TEMP/gitleaks.tar.gz" | sha256sum --check --strict' % tool["sha256"],
        'tar -xzf "$RUNNER_TEMP/gitleaks.tar.gz" -C "$RUNNER_TEMP" gitleaks',
        '"$RUNNER_TEMP/gitleaks" git --redact --exit-code 1 --no-banner .',
    ]}


def _python_steps(tools, severity):
    pins = " ".join('"%s==%s"' % item for item in sorted(tools["pypi"].items()))
    return [
        {"name": "Installation du projet", "lines": [
            "python -m pip install --upgrade pip",
            'python -m pip install -e ".[dev]"',
        ]},
        {"name": "Outils de securite Python (environnement isole, versions epinglees)", "lines": [
            "python -m venv %s" % TOOLS_ENV,
            '%s/bin/python -m pip install %s' % (TOOLS_ENV, pins),
        ]},
        {"name": "SAST Python (Bandit, severite >= %s)" % severity, "lines": [
            '%s/bin/bandit -r src -q --severity-level %s --confidence-level medium' % (TOOLS_ENV, severity),
        ]},
        {"name": "Audit des dependances Python (pip-audit, toute vulnerabilite connue)", "lines": [
            'python -m pip freeze --exclude-editable > "$RUNNER_TEMP/requirements-audit.txt"',
            '%s/bin/pip-audit --strict --no-deps --disable-pip -r "$RUNNER_TEMP/requirements-audit.txt"' % TOOLS_ENV,
        ]},
        {"name": "SBOM Python (CycloneDX)", "lines": [
            '%s/bin/cyclonedx-py environment --of JSON -o sbom-python.cdx.json "$(command -v python)"' % TOOLS_ENV,
        ]},
    ]


def _node_steps(level):
    return [
        {"name": "Installation des dependances npm", "lines": [
            "if [ -f package-lock.json ]; then npm ci; else npm install; fi",
        ]},
        {"name": "Audit des dependances npm (severite >= %s)" % level, "lines": ["npm audit --audit-level=%s" % level]},
        {"name": "SBOM npm (CycloneDX)", "lines": ["npm sbom --sbom-format cyclonedx > sbom-npm.cdx.json"]},
    ]


def _controls(plan, tools, severity, level):
    ids = plan.resolution.ids()
    python, node = "python" in ids, "node" in ids
    rows = [{"control": "Secrets", "tool": "Gitleaks %s" % tools["gitleaks"]["version"], "where": "CI (job security)", "status": "CONFIGURE"}]
    if python:
        rows += [
            {"control": "SAST Python", "tool": "Bandit %s (>= %s)" % (tools["pypi"]["bandit"], severity), "where": "CI (job security)", "status": "CONFIGURE"},
            {"control": "Dependances Python", "tool": "pip-audit %s" % tools["pypi"]["pip-audit"], "where": "CI (job security)", "status": "CONFIGURE"},
            {"control": "SBOM Python", "tool": "CycloneDX %s" % tools["pypi"]["cyclonedx-bom"], "where": "CI (artefact sbom)", "status": "CONFIGURE"},
        ]
    if node:
        sast = "eslint" in ids
        rows += [
            {"control": "SAST JavaScript/TypeScript", "tool": "eslint-plugin-security (--max-warnings 0)" if sast else "aucun",
             "where": "CI (job quality, lint)" if sast else "-", "status": "CONFIGURE" if sast else "NON VERIFIE"},
            {"control": "Dependances npm", "tool": "npm audit (>= %s)" % level, "where": "CI (job security)", "status": "CONFIGURE"},
            {"control": "SBOM npm", "tool": "npm sbom (CycloneDX)", "where": "CI (artefact sbom)", "status": "CONFIGURE"},
        ]
    if "docker" in ids:
        rows.append({"control": "Image conteneur", "tool": "aucun", "where": "-", "status": "NON VERIFIE"})
    rows.append({"control": "Actions GitHub", "tool": "epinglees par SHA, permissions contents: read", "where": "CI", "status": "CONFIGURE"})
    return rows


def security_context(plan, tools=None):
    tools = tools or load_security_tools()
    severity = tools["sast_severity"][plan.spec.security]
    level = tools["npm_audit_level"][plan.spec.security]
    ids = plan.resolution.ids()
    steps = [_gitleaks_step(tools["gitleaks"])]
    if "python" in ids:
        steps += _python_steps(tools, severity)
    if "node" in ids:
        steps += _node_steps(level)
    sboms = [name for name, present in (("sbom-python.cdx.json", "python" in ids), ("sbom-npm.cdx.json", "node" in ids)) if present]
    return {"steps": steps, "sboms": sboms, "controls": _controls(plan, tools, severity, level)}


def security_diagnostics(plan):
    """Controles non executables pour la pile choisie : NON VERIFIE explicite."""
    ids = plan.resolution.ids()
    found = []
    if "node" in ids and "eslint" not in ids:
        found.append(d.warning("security-sast-unverified",
                               "SAST JavaScript/TypeScript NON VERIFIE : selectionner ESLint (eslint-plugin-security)", "eslint"))
    if "docker" in ids:
        found.append(d.warning("security-image-unverified",
                               "Analyse de l'image conteneur NON VERIFIE : aucun scanner d'image configure", "docker"))
    return found
