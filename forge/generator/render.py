"""Rendu deterministe d'un plan en fichiers texte (sans ecriture disque)."""
from forge import TEMPLATES_DIR
from forge.diagnostics import ForgeError
from forge.generator.context import build_context
from forge.generator.paths import resolve_inside
from forge.generator.template import TemplateError, render
from forge.planner.plan import build_plan


def _errors(diagnostics):
    return [x for x in diagnostics if x.severity.value == "error"]


def render_plan(plan, templates_dir=TEMPLATES_DIR, verification=None):
    """Retourne {chemin relatif: contenu}. Refuse un plan ou une verification en erreur."""
    if not plan.ok:
        raise ForgeError("Plan invalide : generation bloquee", _errors(plan.diagnostics))
    if verification is not None and not verification.ok:
        raise ForgeError("Verification en echec : generation bloquee", _errors(verification.diagnostics))
    context = build_context(plan, verification)
    files = {}
    for path, (template, rule_id) in plan.files.items():
        source = resolve_inside(templates_dir, template).read_text(encoding="utf-8")
        try:
            files[path] = render(source, context)
        except TemplateError as exc:
            raise ForgeError("Template %s (regle %s) : %s" % (template, rule_id, exc)) from exc
    return files


def generate(data, catalog=None, rules=None, templates_dir=TEMPLATES_DIR):
    """Valide, planifie et rend les documents, sans reseau ni ecriture. Retourne (plan, fichiers)."""
    plan = build_plan(data, catalog, rules)
    return plan, render_plan(plan, templates_dir)
