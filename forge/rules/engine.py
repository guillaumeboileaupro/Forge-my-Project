"""Moteur de regles (T07) : selection et composition deterministe des regles.

Les regles sont des donnees externes (catalogs/rules/*.json). Les regles
obligatoires s'appliquent toujours ; les autres dependent de conditions
declaratives sur la configuration. Aucune regle n'est executee.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from forge import CATALOGS_DIR, TEMPLATES_DIR
from forge import diagnostics as d
from forge.config.spec import AGENTS, PROJECT_TYPES, SECURITY_LEVELS, OPTIONS
from forge.generator.paths import PathError, resolve_inside, safe_relative_path

SCHEMA_VERSION = 1
RULE_ID = re.compile(r"^[a-z][a-z0-9-]{0,59}$")
SKILL_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SECTIONS = (
    "architecture", "conventions", "testing", "security", "dependencies",
    "workflow", "pitfalls", "deployment", "dod",
)
CONDITIONS = {"technologies_all", "technologies_any", "agents_any", "project_types", "security", "options"}
RULE_FIELDS = {"schema_version", "id", "description", "mandatory", "priority", "when", "files", "sections", "skills"}
FILE_FIELDS = {"path", "template", "override"}


class RuleError(ValueError):
    pass


@dataclass(frozen=True)
class FileSpec:
    path: str
    template: str
    override: bool = False


@dataclass(frozen=True)
class Rule:
    id: str
    description: str
    mandatory: bool
    priority: int
    when: dict
    files: tuple
    sections: dict
    skills: tuple


@dataclass
class Composition:
    rules: list = field(default_factory=list)  # ids appliques, ordre deterministe
    files: dict = field(default_factory=dict)  # chemin -> (template, id de regle)
    sections: dict = field(default_factory=lambda: {name: [] for name in SECTIONS})
    skills: list = field(default_factory=list)
    diagnostics: list = field(default_factory=list)


def _require(condition, message):
    if not condition:
        raise RuleError(message)


def _ids(value, where, allowed=None):
    _require(isinstance(value, list) and value and all(isinstance(v, str) for v in value), where + " : liste non vide attendue")
    if allowed is not None:
        unknown = set(value) - set(allowed)
        _require(not unknown, where + " : valeur inconnue " + ", ".join(sorted(unknown)))
    return tuple(value)


def _parse_when(raw, where, catalog):
    _require(isinstance(raw, dict), where + " : when doit etre un objet")
    _require(not set(raw) - CONDITIONS, where + " : condition inconnue " + ", ".join(sorted(set(raw) - CONDITIONS)))
    when = {}
    for key in ("technologies_all", "technologies_any"):
        if key in raw:
            when[key] = _ids(raw[key], where + "." + key, catalog.technologies)
    if "agents_any" in raw:
        when["agents_any"] = _ids(raw["agents_any"], where + ".agents_any", AGENTS)
    if "project_types" in raw:
        when["project_types"] = _ids(raw["project_types"], where + ".project_types", PROJECT_TYPES)
    if "security" in raw:
        when["security"] = _ids(raw["security"], where + ".security", SECURITY_LEVELS)
    if "options" in raw:
        options = raw["options"]
        _require(isinstance(options, dict) and options and not set(options) - set(OPTIONS)
                 and all(isinstance(v, bool) for v in options.values()), where + " : options invalides")
        when["options"] = dict(options)
    return when


def _parse_files(raw, where, templates_dir):
    _require(isinstance(raw, list), where + " : files doit etre une liste")
    files = []
    for item in raw:
        _require(isinstance(item, dict) and not set(item) - FILE_FIELDS, where + " : entree de fichier invalide")
        try:
            path = safe_relative_path(item.get("path"))
            template = safe_relative_path(item.get("template"))
            source = resolve_inside(templates_dir, template)
        except PathError as exc:
            raise RuleError("%s : %s" % (where, exc)) from exc
        _require(template.endswith(".tmpl") and source.is_file(), where + " : template introuvable " + template)
        override = item.get("override", False)
        _require(isinstance(override, bool), where + " : override doit etre booleen")
        files.append(FileSpec(path, template, override))
    return tuple(files)


def _parse_sections(raw, where):
    _require(isinstance(raw, dict) and not set(raw) - set(SECTIONS), where + " : section inconnue")
    sections = {}
    for name, items in raw.items():
        _require(isinstance(items, list) and all(isinstance(i, str) and i.strip() and "\n" not in i for i in items),
                 where + "." + name + " : liste de phrases attendue")
        sections[name] = tuple(i.strip() for i in items)
    return sections


def parse_rule(raw, catalog, templates_dir=TEMPLATES_DIR):
    _require(isinstance(raw, dict), "Regle invalide")
    _require(raw.get("schema_version") == SCHEMA_VERSION, "Regle : schema_version non supporte")
    rule_id = raw.get("id")
    _require(isinstance(rule_id, str) and RULE_ID.fullmatch(rule_id), "Identifiant de regle invalide : %r" % (rule_id,))
    where = "regle " + rule_id
    _require(not set(raw) - RULE_FIELDS, where + " : champ inconnu " + ", ".join(sorted(set(raw) - RULE_FIELDS)))
    _require(isinstance(raw.get("description"), str) and raw["description"].strip(), where + " : description requise")
    mandatory, priority = raw.get("mandatory", False), raw.get("priority", 50)
    _require(isinstance(mandatory, bool), where + " : mandatory doit etre booleen")
    _require(isinstance(priority, int) and not isinstance(priority, bool) and 0 <= priority <= 100, where + " : priorite 0-100")
    when = _parse_when(raw.get("when", {}), where, catalog)
    _require(not (mandatory and when), where + " : une regle obligatoire ne peut pas etre conditionnelle")
    skills = raw.get("skills", [])
    _require(isinstance(skills, list) and all(isinstance(s, str) and SKILL_NAME.fullmatch(s) for s in skills), where + " : skills invalides")
    return Rule(rule_id, raw["description"].strip(), mandatory, priority, when,
                _parse_files(raw.get("files", []), where, templates_dir),
                _parse_sections(raw.get("sections", {}), where), tuple(skills))


def load_rules(catalog, directory=None, templates_dir=TEMPLATES_DIR):
    directory = Path(directory or CATALOGS_DIR / "rules")
    rules = []
    for path in sorted(directory.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuleError("Regle illisible %s : %s" % (path.name, exc)) from exc
        rules.append(parse_rule(raw, catalog, templates_dir))
    _require(len({r.id for r in rules}) == len(rules), "Identifiant de regle duplique")
    _require(any(r.mandatory for r in rules), "Aucune regle de base obligatoire")
    return sorted(rules, key=lambda r: (r.priority, r.id))


def matches(rule, spec, technology_ids):
    when = rule.when
    if "technologies_all" in when and not set(when["technologies_all"]) <= technology_ids:
        return False
    if "technologies_any" in when and not technology_ids.intersection(when["technologies_any"]):
        return False
    if "agents_any" in when and not set(spec.agents).intersection(when["agents_any"]):
        return False
    if "project_types" in when and spec.project_type not in when["project_types"]:
        return False
    if "security" in when and spec.security not in when["security"]:
        return False
    return all(spec.options.get(k) == v for k, v in when.get("options", {}).items())


def _add_files(rule, composition):
    for item in rule.files:
        current = composition.files.get(item.path)
        if current is None or item.override:
            composition.files[item.path] = (item.template, rule.id)
        else:
            composition.diagnostics.append(d.error(
                "file-conflict", "%s produit par %s et %s sans override" % (item.path, current[1], rule.id), item.path))


def compose(rules, spec, technology_ids):
    """Applique les regles pertinentes dans l'ordre (priorite, id)."""
    composition = Composition()
    for rule in rules:
        if not (rule.mandatory or matches(rule, spec, technology_ids)):
            continue
        composition.rules.append(rule.id)
        _add_files(rule, composition)
        for name, items in rule.sections.items():
            target = composition.sections[name]
            target.extend(i for i in items if i not in target)
        composition.skills.extend(s for s in rule.skills if s not in composition.skills)
    return composition
