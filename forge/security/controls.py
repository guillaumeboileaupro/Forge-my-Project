"""Controles de securite des projets generes (T13).

Decrit le job CI `security` (secrets, SAST, audit des dependances, SBOM) a
partir de catalogs/security/tools.json, et la couverture de chaque controle.
Un controle impossible pour la pile choisie est NON VERIFIE (avertissement),
jamais omis silencieusement. Aucun contournement n'est genere : pas de
`continue-on-error`, pas de `|| true`, pas d'exclusion implicite. Seule exception :
un avis npm precis, justifie et date dans le catalogue (npm_audit_exceptions), applique
par scripts/security/npm_audit_gate.py et affiche dans SECURITY.md.
"""
import datetime
import json
import re
from pathlib import Path

from forge import CATALOGS_DIR
from forge import diagnostics as d

SHA256 = re.compile(r"^[0-9a-f]{64}$")
VERSION = re.compile(r"^\d+(\.\d+){1,3}$")
GHSA = re.compile(r"GHSA(-[23456789cfghjmpqrvwx]{4}){3}")
NPM_NAME = re.compile(r"(@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*")
SAFE_TEXT = re.compile(r"[A-Za-z0-9 ,.;:()/_+-]{10,300}")  # rendu dans un script : ni guillemet ni accolade
MAX_EXCEPTION_DAYS = 90
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
    for item in data.get("npm_audit_exceptions", []):
        _check_npm_exception(item)
    _check_e10_tools(data)
    return data


def _check_e10_tools(data):
    """Semgrep (PyPI) et Trivy (release officielle + empreinte) epingles ; seuils connus (E10)."""
    semgrep, trivy = data.get("semgrep", {}), data.get("trivy", {})
    if semgrep.get("package") != "semgrep" or not VERSION.fullmatch(semgrep.get("version", "")):
        raise SecurityCatalogError("Semgrep : paquet ou version non epingles")
    if trivy.get("repository") != "aquasecurity/trivy" or not VERSION.fullmatch(trivy.get("version", "")) \
            or not SHA256.fullmatch(trivy.get("sha256", "")):
        raise SecurityCatalogError("Trivy : depot, version ou empreinte SHA-256 invalide")
    if trivy.get("asset") != "trivy_%s_Linux-64bit.tar.gz" % trivy["version"]:
        raise SecurityCatalogError("Trivy : nom d'archive incoherent avec la version")
    if data.get("semgrep_severity") != {"strict": "ERROR", "hardened": "WARNING"} \
            or data.get("image_severity") != {"strict": "high", "hardened": "medium"}:
        raise SecurityCatalogError("Seuils Semgrep ou image : valeurs attendues (aucun assouplissement)")


def _check_npm_exception(item):
    """Exception d'audit npm : un avis GHSA, un paquet, une justification et une expiration <= 90 j."""
    if not isinstance(item, dict) or set(item) != {"id", "package", "added", "expires", "reason"}:
        raise SecurityCatalogError("Exception npm : champs attendus id, package, added, expires, reason")
    if not GHSA.fullmatch(item["id"]) or not NPM_NAME.fullmatch(item["package"]):
        raise SecurityCatalogError("Exception npm : identifiant GHSA ou paquet invalide")
    if not SAFE_TEXT.fullmatch(item["reason"]):
        raise SecurityCatalogError("Exception npm %s : justification absente ou caracteres interdits" % item["id"])
    try:
        added, expires = (datetime.date.fromisoformat(item[k]) for k in ("added", "expires"))
    except (TypeError, ValueError) as exc:
        raise SecurityCatalogError("Exception npm %s : date invalide" % item["id"]) from exc
    if not 0 < (expires - added).days <= MAX_EXCEPTION_DAYS:
        raise SecurityCatalogError("Exception npm %s : expiration entre 1 et %d jours apres l'ajout"
                                   % (item["id"], MAX_EXCEPTION_DAYS))


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


SEMGREP_ENV = '"$RUNNER_TEMP/forge-semgrep"'


def _semgrep_step(tool, severity):
    """SAST multi-langage : regles locales .semgrep/forge.yml, sans telemetrie ni regle telechargee."""
    return {"name": "SAST multi-langage (Semgrep %s, regles locales, severite >= %s)" % (tool["version"], severity),
            "lines": [
                "python3 -m venv %s" % SEMGREP_ENV,
                '%s/bin/python -m pip install --disable-pip-version-check -q "semgrep==%s"' % (SEMGREP_ENV, tool["version"]),
                '%s/bin/semgrep scan --config .semgrep/forge.yml --metrics=off --disable-version-check '
                '--json --output "$RUNNER_TEMP/semgrep.json" .' % SEMGREP_ENV,
                'python3 scripts/security/semgrep_gate.py "$RUNNER_TEMP/semgrep.json" %s' % severity,
            ]}


def _image_step(tool, level):
    """Image conteneur : construite et analysee seulement si un Dockerfile existe ; sinon NON VERIFIE visible."""
    url = "https://github.com/%s/releases/download/v%s/%s" % (tool["repository"], tool["version"], tool["asset"])
    return {"name": "Analyse de l'image conteneur (Trivy %s, severite >= %s)" % (tool["version"], level), "lines": [
        "if [ -f Dockerfile ]; then",
        '  curl -sSfL -o "$RUNNER_TEMP/trivy.tar.gz" ' + url,
        '  echo "%s  $RUNNER_TEMP/trivy.tar.gz" | sha256sum --check --strict' % tool["sha256"],
        '  tar -xzf "$RUNNER_TEMP/trivy.tar.gz" -C "$RUNNER_TEMP" trivy',
        "  docker build -t forge-image-scan:ci .",
        '  "$RUNNER_TEMP/trivy" image --scanners vuln --format json --output "$RUNNER_TEMP/trivy.json" forge-image-scan:ci',
        '  python3 scripts/security/image_scan_gate.py "$RUNNER_TEMP/trivy.json" %s' % level,
        "else",
        '  echo "::warning::Analyse d\'image NON VERIFIE : aucun Dockerfile, aucune image a analyser"',
        "fi",
    ]}


def _node_steps(level):
    return [
        {"name": "Installation des dependances npm", "lines": [
            "if [ -f package-lock.json ]; then npm ci; else npm install; fi",
        ]},
        {"name": "Audit des dependances npm (severite >= %s)" % level, "lines": [
            'npm audit --audit-level=%s --json > "$RUNNER_TEMP/npm-audit.json" '
            '|| python3 scripts/security/npm_audit_gate.py "$RUNNER_TEMP/npm-audit.json" %s' % (level, level),
        ]},
        {"name": "SBOM npm (CycloneDX)", "lines": ["npm sbom --sbom-format cyclonedx > sbom-npm.cdx.json"]},
    ]


def _npm_audit_tool(level, exceptions):
    if not exceptions:
        return "npm audit (>= %s)" % level
    listed = ", ".join("%s (%s, expire le %s)" % (e["id"], e["package"], e["expires"]) for e in exceptions)
    return "npm audit (>= %s) ; exceptions datees : %s" % (level, listed)


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
            {"control": "Dependances npm", "tool": _npm_audit_tool(level, tools.get("npm_audit_exceptions", [])),
             "where": "CI (job security)", "status": "CONFIGURE"},
            {"control": "SBOM npm", "tool": "npm sbom (CycloneDX)", "where": "CI (artefact sbom)", "status": "CONFIGURE"},
        ]
    semgrep = tools["semgrep_severity"][plan.spec.security]
    rows.append({"control": "SAST multi-langage", "tool": "Semgrep %s, regles locales .semgrep/forge.yml (>= %s)"
                 % (tools["semgrep"]["version"], semgrep), "where": "CI (job security)", "status": "CONFIGURE"})
    if "docker" in ids:
        rows.append({"control": "Image conteneur", "tool": "Trivy %s (>= %s), des qu'un Dockerfile existe"
                     % (tools["trivy"]["version"], tools["image_severity"][plan.spec.security]),
                     "where": "CI (job security)", "status": "NON VERIFIE tant qu'aucun Dockerfile n'existe"})
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
    steps.append(_semgrep_step(tools["semgrep"], tools["semgrep_severity"][plan.spec.security]))
    if "docker" in ids:
        steps.append(_image_step(tools["trivy"], tools["image_severity"][plan.spec.security]))
    sboms = [name for name, present in (("sbom-python.cdx.json", "python" in ids), ("sbom-npm.cdx.json", "node" in ids)) if present]
    return {"steps": steps, "sboms": sboms, "controls": _controls(plan, tools, severity, level),
            "npm_exceptions": tools.get("npm_audit_exceptions", [])}


def security_diagnostics(plan):
    """Controles non executables pour la pile choisie : NON VERIFIE explicite."""
    ids = plan.resolution.ids()
    found = []
    if "node" in ids and "eslint" not in ids:
        found.append(d.warning("security-sast-unverified",
                               "SAST JavaScript/TypeScript NON VERIFIE : selectionner ESLint (eslint-plugin-security)", "eslint"))
    if "docker" in ids:
        found.append(d.warning("security-image-unverified",
                               "Analyse de l'image conteneur NON VERIFIE tant qu'aucun Dockerfile n'existe "
                               "(Trivy configure dans le job security)", "docker"))
    return found
