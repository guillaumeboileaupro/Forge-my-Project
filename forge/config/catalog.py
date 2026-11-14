"""Chargement et validation du catalogue externe des technologies.

Le catalogue est une donnee versionnee (catalogs/technologies/*.json) : il est
valide integralement avant usage et n'est jamais execute.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from forge import CATALOGS_DIR
from forge.config import versions

SCHEMA_VERSION = 1
TECH_ID = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
ECOSYSTEMS = {"pypi", "npm"}
# Noms de packages acceptes par PyPI (PEP 508) et npm (scope optionnel).
PACKAGE_NAMES = {
    "pypi": re.compile(r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$"),
    "npm": re.compile(r"^(@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*$"),
}
TECH_FIELDS = {
    "id", "name", "description", "ecosystem", "package", "dev", "versions", "requires",
    "conflicts", "constraints", "commands", "docs", "companions",
}


class CatalogError(ValueError):
    pass


@dataclass(frozen=True)
class Technology:
    id: str
    name: str
    category: str
    description: str
    docs: str
    ecosystem: str | None = None
    package: str | None = None
    dev: bool = False
    preferred_version: str | None = None
    supported_versions: tuple = ()
    eol_product: str | None = None
    requires: tuple = ()  # chaque element est un tuple d'alternatives
    conflicts: tuple = ()
    constraints: dict = field(default_factory=dict)
    commands: dict = field(default_factory=dict)
    companions: tuple = ()  # (package, alternatives declenchantes) installes avec la technologie


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    min: int
    max: int


@dataclass(frozen=True)
class Catalog:
    categories: dict
    technologies: dict
    required_commands: tuple
    command_kinds: tuple

    def get(self, tech_id):
        return self.technologies.get(tech_id)

    def by_category(self, category):
        return [t for t in self.technologies.values() if t.category == category]


def _require(condition, message):
    if not condition:
        raise CatalogError(message)


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError("Catalogue illisible %s : %s" % (Path(path).name, exc)) from exc


def _string_list(value, where):
    _require(isinstance(value, list) and all(isinstance(v, str) for v in value), where + " : liste de chaines attendue")
    return tuple(value)


def _parse_requires(raw, where):
    _require(isinstance(raw, list), where + " : requires doit etre une liste")
    result = []
    for item in raw:
        options = (item,) if isinstance(item, str) else _string_list(item, where)
        _require(options, where + " : alternative vide")
        result.append(options)
    return tuple(result)


def _parse_versions(raw, where):
    if raw is None:
        return None, (), None
    _require(isinstance(raw, dict), where + " : versions doit etre un objet")
    supported = _string_list(raw.get("supported"), where + ".supported")
    preferred = raw.get("preferred")
    for value in supported + (preferred,):
        try:
            versions.parse(value)
        except ValueError as exc:
            raise CatalogError("%s : %s" % (where, exc)) from exc
    _require(preferred in supported, where + " : version preferee absente des versions supportees")
    eol = raw.get("eol_product")
    _require(eol is None or isinstance(eol, str) and TECH_ID.fullmatch(eol), where + " : eol_product invalide")
    return preferred, supported, eol


def _parse_technology(raw, category, command_kinds):
    _require(isinstance(raw, dict), "Technologie invalide dans " + category)
    tech_id = raw.get("id")
    _require(isinstance(tech_id, str) and TECH_ID.fullmatch(tech_id), "Identifiant de technologie invalide : %r" % (tech_id,))
    where = "technologie " + tech_id
    unknown = set(raw) - TECH_FIELDS
    _require(not unknown, where + " : champ inconnu " + ", ".join(sorted(unknown)))
    for key in ("name", "description", "docs"):
        _require(isinstance(raw.get(key), str) and raw[key].strip(), where + " : " + key + " requis")
    _require(raw["docs"].startswith("https://"), where + " : la documentation doit etre une URL https officielle")
    ecosystem, package = raw.get("ecosystem"), raw.get("package")
    _require(ecosystem is None or ecosystem in ECOSYSTEMS, where + " : ecosysteme inconnu")
    if ecosystem:
        _require(isinstance(package, str) and PACKAGE_NAMES[ecosystem].fullmatch(package), where + " : nom de package invalide")
    else:
        _require(package is None, where + " : package sans ecosysteme")
    commands = raw.get("commands", {})
    _require(isinstance(commands, dict), where + " : commands doit etre un objet")
    for kind, command in commands.items():
        _require(kind in command_kinds, where + " : type de commande inconnu " + kind)
        _require(isinstance(command, str) and command.strip() and "\n" not in command, where + " : commande invalide")
    constraints = raw.get("constraints", {})
    _require(isinstance(constraints, dict), where + " : constraints doit etre un objet")
    for target, constraint in constraints.items():
        try:
            versions.parse_constraint(constraint)
        except ValueError as exc:
            raise CatalogError("%s : %s" % (where, exc)) from exc
    preferred, supported, eol = _parse_versions(raw.get("versions"), where)
    dev = raw.get("dev", False)
    _require(isinstance(dev, bool), where + " : dev doit etre booleen")
    return Technology(
        id=tech_id, name=raw["name"], category=category, description=raw["description"], docs=raw["docs"],
        ecosystem=ecosystem, package=package, dev=dev, preferred_version=preferred,
        supported_versions=supported, eol_product=eol,
        requires=_parse_requires(raw.get("requires", []), where),
        conflicts=_string_list(raw.get("conflicts", []), where + ".conflicts"),
        constraints=dict(constraints), commands=dict(commands),
        companions=_parse_companions(raw.get("companions", []), where, ecosystem),
    )


def _parse_companions(raw, where, ecosystem):
    _require(isinstance(raw, list), where + " : companions doit etre une liste")
    _require(not raw or ecosystem, where + " : companions sans ecosysteme")
    result = []
    for item in raw:
        _require(isinstance(item, dict) and set(item) <= {"package", "when_any"}, where + " : compagnon invalide")
        package = item.get("package")
        _require(isinstance(package, str) and PACKAGE_NAMES[ecosystem].fullmatch(package), where + " : package compagnon invalide")
        result.append((package, _string_list(item.get("when_any", []), where + ".when_any")))
    return tuple(result)


def _check_references(technologies):
    for tech in technologies.values():
        referenced = [t for options in tech.requires for t in options]
        referenced += list(tech.conflicts) + list(tech.constraints)
        referenced += [t for _, when in tech.companions for t in when]
        for ref in referenced:
            _require(ref in technologies, "technologie %s : reference inconnue %s" % (tech.id, ref))
        for target in tech.constraints:
            _require(technologies[target].supported_versions, "technologie %s : %s n'a pas de versions" % (tech.id, target))


def load_catalog(directory=None):
    directory = Path(directory or CATALOGS_DIR / "technologies")
    meta = _read_json(directory / "categories.json")
    _require(meta.get("schema_version") == SCHEMA_VERSION, "categories.json : schema_version non supporte")
    command_kinds = _string_list(meta.get("command_kinds"), "command_kinds")
    required = _string_list(meta.get("required_commands", []), "required_commands")
    _require(set(required) <= set(command_kinds), "required_commands inconnues")
    categories = {}
    for cat_id, raw in meta.get("categories", {}).items():
        _require(isinstance(raw, dict) and isinstance(raw.get("min"), int) and isinstance(raw.get("max"), int), "categorie invalide " + cat_id)
        _require(0 <= raw["min"] <= raw["max"], "bornes invalides pour " + cat_id)
        categories[cat_id] = Category(cat_id, str(raw.get("label", cat_id)), raw["min"], raw["max"])
    technologies = {}
    for path in sorted(directory.glob("*.json")):
        if path.name == "categories.json":
            continue
        data = _read_json(path)
        _require(data.get("schema_version") == SCHEMA_VERSION, path.name + " : schema_version non supporte")
        category = data.get("category")
        _require(category in categories, path.name + " : categorie inconnue")
        for raw in data.get("technologies", []):
            tech = _parse_technology(raw, category, command_kinds)
            _require(tech.id not in technologies, "technologie dupliquee : " + tech.id)
            technologies[tech.id] = tech
    _check_references(technologies)
    return Catalog(categories, technologies, required, command_kinds)
