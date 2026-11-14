"""Construction du contexte de rendu a partir d'un plan valide.

Toute information absente est rendue explicitement (NON DEFINI / NON VERIFIE)
au lieu d'etre inventee.
"""
from forge.config.spec import AGENTS

UNDEFINED = "NON DEFINI"
UNVERIFIED = "NON VERIFIE"

AGENT_INFO = {
    "codex": {"name": "Codex", "instructions": "AGENTS.md", "skills_dir": ".agents/skills"},
    "claude": {"name": "Claude Code", "instructions": "CLAUDE.md (importe AGENTS.md)", "skills_dir": ".claude/skills"},
    "copilot": {"name": "GitHub Copilot", "instructions": ".github/copilot-instructions.md", "skills_dir": UNDEFINED},
}
PROJECT_TYPE_LABELS = {
    "library": "bibliotheque", "cli": "outil en ligne de commande", "api": "API / service HTTP", "web": "application web",
}
COMMAND_LABELS = {
    "install": "Installation", "test": "Tests", "coverage": "Couverture", "lint": "Lint", "format": "Formatage",
    "typecheck": "Typage", "audit": "Audit des dependances", "build": "Build",
}


def _technologies(plan):
    versions = plan.resolution.versions
    return [
        {
            "id": t.id, "name": t.name, "category": t.category, "description": t.description, "docs": t.docs,
            "version": versions.get(t.id, ""), "package": t.package or "", "ecosystem": t.ecosystem or "",
            "dev": t.dev,
        }
        for t in plan.resolution.technologies
    ]


def _commands(plan, catalog_kinds=tuple(COMMAND_LABELS)):
    found = plan.resolution.commands
    listing, flat = [], {}
    for kind in catalog_kinds:
        values = found.get(kind, [])
        flat[kind] = " && ".join(values) if values else UNDEFINED
        if values:
            listing.append({"kind": kind, "label": COMMAND_LABELS.get(kind, kind), "commands": values})
    return listing, flat


def _dependencies(technologies):
    return [
        {"name": t["name"], "package": t["package"], "ecosystem": t["ecosystem"],
         "scope": "developpement" if t["dev"] else "execution", "status": UNVERIFIED}
        for t in technologies if t["package"]
    ]


def _tasks(plan, has_dependencies):
    """Taches initiales deduites de la configuration ; les charges restent a estimer."""
    tasks = [("Installer l'environnement et executer chaque commande documentee", "-", "P0")]
    if has_dependencies:
        tasks.append(("Verifier chaque dependance sur son registre officiel (lever les NON VERIFIE)", "T01", "P0"))
    tasks.append(("Configurer la CI GitHub Actions, les hooks et la protection de branche", "T01", "P0"))
    if plan.architecture["source"] == "manual":
        tasks.append(("Decomposer l'architecture definie manuellement en taches verifiables", "T01", "P1"))
    else:
        tasks.extend(("Mettre en place : " + item, "T01", "P1") for item in plan.architecture["suggested"])
    tasks.append(("Recette : tests, couverture, audits de securite et documentation a jour", "toutes", "P1"))
    return [{"id": "T%02d" % index, "title": title, "depends": depends, "priority": priority}
            for index, (title, depends, priority) in enumerate(tasks, start=1)]


def build_context(plan):
    spec = plan.spec
    technologies = _technologies(plan)
    commands, command_map = _commands(plan)
    agents = [dict(AGENT_INFO[a], id=a) for a in spec.agents]
    sections = {name: list(items) for name, items in plan.composition.sections.items()}
    return {
        "project": {
            "name": spec.name,
            "package_name": spec.package_name,
            "description": spec.description or UNDEFINED,
            "description_lines": spec.description.splitlines() if spec.description else [UNDEFINED],
            "type": spec.project_type,
            "type_label": PROJECT_TYPE_LABELS[spec.project_type],
            "security": spec.security,
        },
        "agents": agents,
        "agent_names": ", ".join(a["name"] for a in agents),
        "has": dict({a: a in spec.agents for a in AGENTS},
                    mcp=spec.options["mcp"], docker="docker" in plan.resolution.ids(),
                    hardened=spec.security == "hardened", dependencies=bool(_dependencies(technologies))),
        "technologies": technologies,
        "dependencies": _dependencies(technologies),
        "commands": commands,
        "command": command_map,
        "sections": sections,
        "architecture": {
            "manual": plan.architecture["manual"].splitlines(),
            "suggested": plan.architecture["suggested"],
            "is_manual": plan.architecture["source"] == "manual",
            "is_undefined": plan.architecture["source"] == "undefined",
        },
        "tasks": _tasks(plan, bool(_dependencies(technologies))),
        "skills": list(plan.composition.skills),
        "rules": list(plan.composition.rules),
        "warnings": [diag.message for diag in plan.diagnostics if diag.severity.value == "warning"],
        "status": {"undefined": UNDEFINED, "unverified": UNVERIFIED},
    }
