"""Generation historique, rendue depuis des templates texte externes."""
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

from forge.config.legacy import validate

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates" / "legacy"
TOKEN = re.compile(r"{{\s*([a-z_]+)\s*}}")


def render_template(relative_path, values=None):
    """Charge un template connu et remplace ses marqueurs en un seul passage."""
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Chemin de template invalide")
    source = (TEMPLATES_DIR / Path(*relative.parts)).read_text(encoding="utf-8")
    context = values or {}

    def replace(match):
        key = match.group(1)
        if key not in context:
            raise ValueError("Variable de template inconnue : " + key)
        return str(context[key])

    return TOKEN.sub(replace, source).strip() + "\n"


def skill(name, description, rules):
    return render_template(
        "skills/SKILL.md.tmpl",
        {"name": name, "description": description, "rules": rules},
    )


def build(config):
    """Retourne le contrat historique ``{chemin: contenu}`` sans ecrire."""
    current = validate(config)
    python_project = current["language"] == "python"
    command = "python3 -m unittest discover -s tests -v" if python_project else "npm test"
    values = {
        **current,
        "command": command,
        "description_or_default": current["description"] or "Projet genere par Forge-my-Project.",
        "objective_or_default": current["description"] or "Developper un projet fiable.",
        "one_pr_label": "oui" if current["one_pr"] else "non",
        "package_name": current["name"].replace("-", "_"),
    }
    files = {
        "README.md": render_template("README.md.tmpl", values),
        "AGENTS.md": render_template("AGENTS.md.tmpl", values),
        "docs/ARCHITECTURE.md": render_template("docs/ARCHITECTURE.md.tmpl", values),
        "docs/DEVELOPMENT.md": render_template("docs/DEVELOPMENT.md.tmpl", values),
        "docs/DEPENDENCIES.md": render_template("docs/DEPENDENCIES.md.tmpl"),
        "docs/MCP.md": render_template("docs/MCP.md.tmpl"),
        "SECURITY.md": render_template("SECURITY.md.tmpl"),
        ".github/pull_request_template.md": render_template("pull_request_template.md.tmpl"),
        ".agents/skills/security-audit/SKILL.md": skill(
            "security-audit",
            "Verifier les controles de securite avant la PR.",
            "Rechercher secrets, injections, acces excessifs, composants vulnerables et mesures correctives. Ne jamais masquer une alerte.",
        ),
        ".agents/skills/package-verification/SKILL.md": skill(
            "package-verification",
            "Valider toute nouvelle dependance.",
            "Consulter le registre officiel, verifier le nom exact, les versions et les imports documentes, la licence et les CVE avant ajout. Ne pas imaginer d'API.",
        ),
        ".agents/skills/definition-of-done/SKILL.md": skill(
            "definition-of-done",
            "Verifier les criteres de fin.",
            "Valider commandes, tests, rapport CI, revue, audit et documentation. Signaler tout controle non execute comme NON VERIFIE.",
        ),
        ".githooks/pre-commit": render_template("hooks/pre-commit.tmpl"),
        ".github/workflows/ci.yml": render_template("ci/ci.yml.tmpl"),
    }
    if python_project:
        files.update(
            {
                "pyproject.toml": render_template("python/pyproject.toml.tmpl", values),
                "src/%s/__init__.py" % values["package_name"]: render_template("python/__init__.py.tmpl"),
                "tests/test_smoke.py": render_template("python/test_smoke.py.tmpl"),
            }
        )
    else:
        files.update(
            {
                "package.json": json.dumps(
                    {
                        "name": current["name"],
                        "version": "0.1.0",
                        "private": True,
                        "type": "module",
                        "scripts": {"test": "node --test"},
                        "devDependencies": {},
                    },
                    indent=2,
                )
                + "\n",
                "src/index.js": render_template("javascript/index.js.tmpl"),
                "tests/index.test.js": render_template("javascript/index.test.js.tmpl"),
            }
        )
    if current["deployment"] != "none":
        files["docs/DEPLOYMENT.md"] = render_template("docs/DEPLOYMENT.md.tmpl", values)
    return files


def generate(config):
    """Construit en memoire un ZIP borne a la racine du projet valide."""
    current = validate(config)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in sorted(build(current).items()):
            archive.writestr(current["name"] + "/" + path, content)
    return stream.getvalue()
