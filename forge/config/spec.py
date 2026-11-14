"""Schema versionne de la configuration d'entree du moteur (ProjectSpec).

Independant de l'interface : toute valeur est revalidee ici. Les textes libres
sont des donnees, jamais des commandes ni des modeles.
"""
import re
from dataclasses import dataclass, field

from forge.config import versions

SCHEMA_VERSION = 1
NAME = re.compile(r"^[a-z][a-z0-9-]{1,48}[a-z0-9]$")
TECH_ID = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
AGENTS = ("codex", "claude", "copilot")
SECURITY_LEVELS = ("strict", "hardened")
PROJECT_TYPES = ("library", "cli", "api", "web")
OPTIONS = {"mcp": False}
FIELDS = {
    "schema_version", "name", "description", "project_type", "architecture", "technologies",
    "versions", "agents", "security", "options",
}
MAX_TECHNOLOGIES = 30


class SpecError(ValueError):
    pass


@dataclass(frozen=True)
class ProjectSpec:
    name: str
    description: str
    project_type: str
    technologies: tuple
    agents: tuple
    security: str = "strict"
    architecture: str = ""
    versions: dict = field(default_factory=dict)
    options: dict = field(default_factory=lambda: dict(OPTIONS))

    @property
    def package_name(self):
        return self.name.replace("-", "_")


def _text(data, key, limit):
    value = data.get(key, "")
    if not isinstance(value, str) or len(value) > limit:
        raise SpecError("%s invalide (texte de %d caracteres maximum)" % (key, limit))
    # Normalise les espaces et retire les caracteres de controle.
    lines = ["".join(ch for ch in line if ch.isprintable()).rstrip() for line in value.strip().splitlines()]
    return "\n".join(lines)


def _choice(data, key, allowed, default=None):
    value = data.get(key, default)
    if value not in allowed:
        raise SpecError("Option invalide : %s (valeurs : %s)" % (key, ", ".join(allowed)))
    return value


def _unique_ids(data, key, pattern, limit):
    value = data.get(key, [])
    if not isinstance(value, list) or len(value) > limit:
        raise SpecError("%s doit etre une liste d'au plus %d elements" % (key, limit))
    for item in value:
        if not isinstance(item, str) or not pattern.fullmatch(item):
            raise SpecError("%s : identifiant invalide %r" % (key, item))
    if len(set(value)) != len(value):
        raise SpecError("%s : doublon" % key)
    return tuple(value)


def _versions(data):
    value = data.get("versions", {})
    if not isinstance(value, dict):
        raise SpecError("versions doit etre un objet")
    for tech_id, version in value.items():
        if not isinstance(tech_id, str) or not TECH_ID.fullmatch(tech_id):
            raise SpecError("versions : identifiant invalide")
        try:
            versions.parse(version)
        except ValueError as exc:
            raise SpecError("versions.%s : %s" % (tech_id, exc)) from exc
    return dict(value)


def _options(data):
    value = data.get("options", {})
    if not isinstance(value, dict) or set(value) - set(OPTIONS):
        raise SpecError("options invalides (autorisees : %s)" % ", ".join(OPTIONS))
    merged = dict(OPTIONS, **value)
    if not all(isinstance(v, bool) for v in merged.values()):
        raise SpecError("options : valeurs booleennes attendues")
    return merged


def parse_spec(data):
    """Valide un dictionnaire (JSON) et retourne un ProjectSpec immuable."""
    if not isinstance(data, dict):
        raise SpecError("Configuration JSON attendue")
    unknown = set(data) - FIELDS
    if unknown:
        raise SpecError("Champ inconnu : " + sorted(unknown)[0])
    if data.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        raise SpecError("schema_version non supporte")
    name = data.get("name")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise SpecError("Nom de projet invalide (3-50 caracteres, minuscules, chiffres, tirets)")
    agents = _unique_ids(data, "agents", TECH_ID, len(AGENTS))
    if not agents or set(agents) - set(AGENTS):
        raise SpecError("agents : au moins un agent parmi " + ", ".join(AGENTS))
    technologies = _unique_ids(data, "technologies", TECH_ID, MAX_TECHNOLOGIES)
    if not technologies:
        raise SpecError("technologies : au moins une technologie requise")
    return ProjectSpec(
        name=name,
        description=_text(data, "description", 2000),
        project_type=_choice(data, "project_type", PROJECT_TYPES),
        technologies=technologies,
        agents=tuple(a for a in AGENTS if a in agents),
        security=_choice(data, "security", SECURITY_LEVELS, "strict"),
        architecture=_text(data, "architecture", 4000),
        versions=_versions(data),
        options=_options(data),
    )
