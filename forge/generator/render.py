"""Rendu deterministe d'un plan en fichiers texte (sans ecriture disque)."""
from forge import TEMPLATES_DIR
from forge.diagnostics import ForgeError
from forge.generator.context import build_context
from forge.generator.paths import resolve_inside
from forge.generator.template import TemplateError, render


def render_plan(plan, templates_dir=TEMPLATES_DIR):
    """Retourne {chemin relatif: contenu}. Refuse un plan contenant des erreurs."""
    if not plan.ok:
        raise ForgeError("Plan invalide : generation bloquee", [x for x in plan.diagnostics if x.severity.value == "error"])
    context = build_context(plan)
    files = {}
    for path, (template, rule_id) in plan.files.items():
        source = resolve_inside(templates_dir, template).read_text(encoding="utf-8")
        try:
            files[path] = render(source, context)
        except TemplateError as exc:
            raise ForgeError("Template %s (regle %s) : %s" % (template, rule_id, exc)) from exc
    return files
