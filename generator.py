"""Générateur de projet : pas d'installation ni d'execution de commandes."""
import io
import json
import re
import zipfile

OPTIONS = {
    "language": {"python", "typescript"},
    "agent": {"codex", "claude", "copilot", "agnostic"},
    "deployment": {"none", "docker", "s3ns", "outscale"},
    "security": {"strict", "hardened"},
}
NAME = re.compile(r"^[a-z][a-z0-9-]{1,48}[a-z0-9]$")

def validate(data):
    if not isinstance(data, dict):
        raise ValueError("Configuration JSON attendue")
    name = data.get("name")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError("Nom de projet invalide (3-50 caracteres, minuscules, chiffres, tirets)")
    config = {"name": name}
    for key, allowed in OPTIONS.items():
        value = data.get(key)
        if not isinstance(value, str) or value not in allowed:
            raise ValueError("Option invalide : " + key)
        config[key] = value
    description = data.get("description", "")
    if not isinstance(description, str) or len(description) > 500:
        raise ValueError("Description invalide")
    config["description"] = description.strip().replace("\n", " ")
    config["one_pr"] = data.get("one_pr", True) is True
    return config

def skill(name, description, rules):
    return "---\nname: " + name + "\ndescription: " + description + "\n---\n\n# " + name + "\n\n" + rules + "\n"

def build(config):
    c = validate(config)
    py = c["language"] == "python"
    cmd = "python3 -m unittest discover -s tests -v" if py else "npm test"
    files = {}
    def add(path, content):
        files[path] = content.strip() + "\n"
    add("README.md", "# " + c["name"] + "\n\n" + (c["description"] or "Projet genere par Forge-my-Project.") + "\n\n## Tests\n\n`" + cmd + "`\n")
    add("AGENTS.md", """# Instructions agent

## Objectif
%s

## Architecture
Lire docs/ARCHITECTURE.md. Preferer des modules petits et des interfaces explicites.

## Conventions
Changements minimaux, tests de non-regression, pas de code mort.
Une seule PR ouverte a la fois : %s.
Ne jamais inventer une API, un nom de package ou une commande.

## Commandes
Tests : `%s`

## Pieges communs
- Ne jamais exposer de secret ou de token.
- Ne pas contourner les audits de securite.
- Ne pas installer de dependance non verifiee.
- Ne pas annoncer des tests passes sans les avoir executes.

## Definition of Done
- Fonctionnalite verifiee et documentee.
- Tests applicables passes.
- Dependencies et licences verifiees.
- Scans de vulnerabilites sans alerte critique/haute non resolue.
- CI verte et revue de la PR terminee.
""" % (c["description"] or "Developper un projet fiable.", "oui" if c["one_pr"] else "non", cmd))
    add("docs/ARCHITECTURE.md", "# Architecture\n\nLangage : " + c["language"] + "\n\nAgent : " + c["agent"] + "\n\nDeploiement : " + c["deployment"] + "\n\nDecisions a valider avant implementation.\n")
    add("docs/DEVELOPMENT.md", "# Developpement\n\nExecuter : `" + cmd + "`\n\nFaire une PR, relire les differences, verifier la CI et la securite avant fusion.\n")
    add("docs/DEPENDENCIES.md", "# Dependances\n\nVerifier l'existence sur PyPI ou npm, la version, les APIs, la licence et les CVE a partir des sources officielles. Verrouiller les versions avec un lockfile et interdire les packages fictifs.\n")
    add("docs/MCP.md", "# MCP\n\nLes serveurs MCP sont a selectionner selon les besoins reels. Ne jamais integrer de token dans Git. Appliquer les permissions minimales et demander confirmation pour les actions destructrices.\n")
    add("SECURITY.md", "# Securite\n\nAucun secret commite. Revue SAST, SCA, secrets et dependances. Refuser les vulnérabilités critiques/hautes non resolues. Signaler les failles via un canal prive. Aucune garantie d'absence totale de vulnerabilites.\n")
    add(".github/pull_request_template.md", "## Changement\n\n## Tests executes\n\n## Impact securite\n\n## Documentation\n\n- [ ] Definition of Done verifiee\n")
    add(".agents/skills/security-audit/SKILL.md", skill("security-audit", "Verifier les controles de securite avant la PR.", "Rechercher secrets, injections, acces excessifs, composants vulnerables et mesures correctives. Ne jamais masquer une alerte."))
    add(".agents/skills/package-verification/SKILL.md", skill("package-verification", "Valider toute nouvelle dependance.", "Consulter le registre officiel, verifier le nom exact, les versions et les imports documentes, la licence et les CVE avant ajout. Ne pas imaginer d'API."))
    add(".agents/skills/definition-of-done/SKILL.md", skill("definition-of-done", "Verifier les criteres de fin.", "Valider commandes, tests, rapport CI, revue, audit et documentation. Signaler tout controle non execute comme NON VERIFIE."))
    add(".githooks/pre-commit", "#!/bin/sh\nset -eu\nif git diff --cached --name-only | grep -Eq '(^|/)(\\.env|id_rsa|.*\\.pem)$'; then echo 'Fichier sensible dans index' >&2; exit 1; fi\n")
    add(".github/workflows/ci.yml", """name: CI
on:
  push:
  pull_request:
permissions:
  contents: read
jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - name: Notice
        run: |
          echo 'CI template: configure actions pinned by full SHA and stack-specific scans before activation'
          exit 1
""")
    if py:
        add("pyproject.toml", "[project]\nname = \"" + c["name"] + "\"\nversion = \"0.1.0\"\nrequires-python = \">=3.11\"\ndependencies = []\n")
        add("src/" + c["name"].replace("-", "_") + "/__init__.py", '"""Package principal."""')
        add("tests/test_smoke.py", "import unittest\n\nclass SmokeTest(unittest.TestCase):\n    def test_smoke(self):\n        self.assertTrue(True)\n\nif __name__ == '__main__':\n    unittest.main()\n")
    else:
        add("package.json", json.dumps({"name": c["name"], "version": "0.1.0", "private": True, "type": "module", "scripts": {"test": "node --test"}, "devDependencies": {}}, indent=2))
        add("src/index.js", "export function health() { return 'ok'; }")
        add("tests/index.test.js", "import { test } from 'node:test';\nimport { strict as assert } from 'node:assert';\nimport { health } from '../src/index.js';\ntest('health', () => assert.equal(health(), 'ok'));")
    if c["deployment"] != "none":
        add("docs/DEPLOYMENT.md", "# Deploiement " + c["deployment"] + "\n\nInfrastructure, auth, images et secrets a definir et verifier avant activation.\n")
    return files

def generate(config):
    c = validate(config)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as z:
        for path, content in sorted(build(c).items()):
            z.writestr(c["name"] + "/" + path, content)
    return stream.getvalue()
