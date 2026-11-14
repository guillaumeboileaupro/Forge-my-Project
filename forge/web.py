"""Cas d'usage exposes a l'interface locale, independants du transport HTTP.

Chaque fonction retourne (statut HTTP, corps en octets, type de contenu, nom de
telechargement ou None), dans l'ordre attendu par server.Handler.reply.
Toute entree est revalidee ici : le navigateur n'est jamais une source de
confiance. Le reseau n'est utilise que si `verify` ou `skills` est demande.
"""
import json

from forge import diagnostics as d
from forge.config.catalog import load_catalog
from forge.config.spec import AGENTS, OPTIONS, PROJECT_TYPES, SECURITY_LEVELS, SpecError
from forge.diagnostics import ForgeError
from forge.generator.archive import build_zip
from forge.generator.context import AGENT_INFO, PROJECT_TYPE_LABELS
from forge.pipeline import run

JSON = "application/json; charset=utf-8"
REQUEST_FIELDS = {"config", "verify", "skills"}


def _json(status, payload):
    return status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), JSON, None


def catalog_payload():
    catalog = load_catalog()
    technologies = [
        {
            "id": t.id, "name": t.name, "category": t.category, "description": t.description, "docs": t.docs,
            "package": t.package, "versions": list(t.supported_versions), "preferred": t.preferred_version,
            "requires": [list(options) for options in t.requires], "conflicts": list(t.conflicts),
        }
        for t in catalog.technologies.values()
    ]
    categories = [{"id": c.id, "label": c.label, "min": c.min, "max": c.max} for c in catalog.categories.values()]
    return _json(200, {
        "categories": categories,
        "technologies": technologies,
        "agents": [{"id": a, "name": AGENT_INFO[a]["name"]} for a in AGENTS],
        "project_types": [{"id": p, "label": PROJECT_TYPE_LABELS[p]} for p in PROJECT_TYPES],
        "security_levels": list(SECURITY_LEVELS),
        "options": sorted(OPTIONS),
    })


def _parse_request(raw):
    try:
        body = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SpecError("JSON invalide") from exc
    if not isinstance(body, dict) or set(body) - REQUEST_FIELDS or "config" not in body:
        raise SpecError("Requete invalide : champs config, verify, skills")
    verify, skills = body.get("verify", False), body.get("skills", False)
    if not isinstance(verify, bool) or not isinstance(skills, bool):
        raise SpecError("verify et skills doivent etre booleens")
    return body["config"], verify, skills


def _execute(raw):
    config, verify, skills = _parse_request(raw)
    return run(config, verify=verify, skills=skills)


def _failure(exc):
    if isinstance(exc, ForgeError):
        return _json(422, {"ok": False, "error": str(exc), "diagnostics": [x.as_dict() for x in exc.diagnostics]})
    return _json(400, {"ok": False, "error": str(exc), "diagnostics": []})


def plan_payload(raw):
    """Apercu : diagnostics, rapports et contenu des fichiers (aucune ecriture)."""
    try:
        result = _execute(raw)
    except (ForgeError, ValueError) as exc:
        return _failure(exc)
    payload = result.as_dict()
    payload["contents"] = result.files
    return _json(200, payload)


def archive_payload(raw):
    """Repete tous les controles avant de produire l'archive ; refuse toute erreur."""
    try:
        result = _execute(raw)
        if d.has_errors(result.diagnostics):
            raise ForgeError("Erreurs bloquantes", [x for x in result.diagnostics if x.severity is d.Severity.ERROR])
        name = result.plan.spec.name
        content = build_zip(name, result.files)
    except (ForgeError, ValueError) as exc:
        return _failure(exc)
    return 200, content, "application/zip", name + ".zip"
