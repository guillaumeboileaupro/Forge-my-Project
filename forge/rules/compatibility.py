"""Controle des selections de technologies contre le catalogue (T06).

Produit des diagnostics ; une erreur bloque la generation, un avertissement
demande une confirmation. Aucune dependance n'est ajoutee implicitement :
une dependance manquante est signalee, pas corrigee en silence.
"""
from dataclasses import dataclass

from forge import diagnostics as d
from forge.config import versions


@dataclass(frozen=True)
class Resolution:
    technologies: tuple  # objets Technology dans l'ordre du catalogue
    versions: dict  # id -> version retenue
    commands: dict  # type -> liste de commandes
    diagnostics: tuple

    @property
    def ok(self):
        return not d.has_errors(self.diagnostics)

    def ids(self):
        return {t.id for t in self.technologies}


def _known(spec, catalog, out):
    known = []
    for tech_id in spec.technologies:
        tech = catalog.get(tech_id)
        if tech is None:
            out.append(d.error("unknown-technology", "Technologie absente du catalogue : " + tech_id, tech_id))
        else:
            known.append(tech)
    order = list(catalog.technologies)
    return sorted(known, key=lambda t: order.index(t.id))


def _check_cardinality(selected, catalog, out):
    for category in catalog.categories.values():
        count = sum(1 for t in selected if t.category == category.id)
        if count < category.min:
            out.append(d.error("category-min", "%s : au moins %d choix requis" % (category.label, category.min), category.id))
        if count > category.max:
            out.append(d.error("category-max", "%s : au plus %d choix" % (category.label, category.max), category.id))


def _check_relations(selected, out):
    ids = {t.id for t in selected}
    for tech in selected:
        for options in tech.requires:
            if not ids.intersection(options):
                out.append(d.error("missing-requirement", "%s requiert %s" % (tech.name, " ou ".join(options)), tech.id))
        for other in tech.conflicts:
            if other in ids and tech.id < other:
                out.append(d.error("conflict", "%s est incompatible avec %s" % (tech.id, other), tech.id))


def _resolve_versions(spec, selected, out):
    chosen = {}
    ids = {t.id for t in selected}
    for tech_id in spec.versions:
        if tech_id not in ids:
            out.append(d.error("version-unselected", "Version fournie pour une technologie non selectionnee : " + tech_id, tech_id))
    for tech in selected:
        if not tech.supported_versions:
            if tech.id in spec.versions:
                out.append(d.warning("version-unmanaged", "Version de %s non geree par le catalogue : a verifier" % tech.name, tech.id))
            continue
        version = spec.versions.get(tech.id, tech.preferred_version)
        if version not in tech.supported_versions:
            out.append(d.error("version-unsupported", "%s %s non supporte (supportees : %s)" % (
                tech.name, version, ", ".join(tech.supported_versions)), tech.id))
        chosen[tech.id] = version
    return chosen


def _check_constraints(selected, chosen, out):
    for tech in selected:
        for target, constraint in tech.constraints.items():
            version = chosen.get(target)
            if version and not versions.satisfies(version, constraint):
                out.append(d.error("version-constraint", "%s requiert %s %s (choisi : %s)" % (
                    tech.name, target, constraint, version), tech.id))


def _collect_commands(selected, catalog, out):
    commands = {}
    for kind in catalog.command_kinds:
        found = [t.commands[kind] for t in selected if kind in t.commands]
        if found:
            commands[kind] = found
    for kind in catalog.required_commands:
        if kind not in commands:
            out.append(d.warning("unknown-command", "Aucune commande '%s' connue pour cette selection" % kind, kind))
    return commands


def resolve(spec, catalog):
    """Valide la selection d'un ProjectSpec et calcule versions et commandes."""
    out = []
    selected = _known(spec, catalog, out)
    _check_cardinality(selected, catalog, out)
    _check_relations(selected, out)
    chosen = _resolve_versions(spec, selected, out)
    _check_constraints(selected, chosen, out)
    commands = _collect_commands(selected, catalog, out)
    return Resolution(tuple(selected), chosen, commands, tuple(out))
