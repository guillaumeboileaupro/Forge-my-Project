"""Graphe du plan reel pour l'apercu E16 : technologies -> regles -> fichiers.

Uniquement des elements du plan calcule par le moteur : aucune dependance n'est
deduite cote navigateur. Chaque fichier genere apparait exactement une fois.
"""
from forge.rules.engine import PACKAGE_PLACEHOLDER


def plan_graph(result):
    plan = result.plan
    composition = plan.composition
    technologies = [{"id": t.id, "name": t.name, "category": t.category} for t in plan.resolution.technologies]
    rules = [dict(composition.details[rule_id], id=rule_id, technologies=list(composition.triggers[rule_id]))
             for rule_id in composition.rules]
    produced = {path.replace(PACKAGE_PLACEHOLDER, plan.spec.package_name): rule_id
                for path, (_, rule_id) in plan.files.items()}
    files = [{"path": path, "rule": produced.get(path), "origin": "rule" if path in produced else "skills"}
             for path in sorted(result.files)]
    return {"technologies": technologies, "rules": rules, "files": files}
