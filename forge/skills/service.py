"""Assemblage des skills d'un plan : my-skills + skills externes approuves."""
from forge.diagnostics import ForgeError
from forge.skills import bundle as b
from forge.skills import external
from forge.skills.cache import SearchCache, ttl_from_config
from forge.skills.github import default_client
from forge.skills.my_skills import collect_skills


def skills_for_plan(plan, client=None, config=None):
    config = config or b.load_copy_policy()
    client = client or default_client()
    agents = plan.spec.agents
    result = b.SkillBundle()
    collect_skills(list(plan.composition.skills), agents, client, config, result)
    external.collect_approved(plan.spec.external_skills, agents, client, config, result)
    copied = [r.name for r in result.records if r.status == "copie"]
    if len(set(copied)) != len(copied):
        raise ForgeError("Deux skills copies portent le meme nom : approbation a corriger")
    for record in result.records:
        result.diagnostics.extend(b.record_diagnostics(record))
    result.files["docs/SKILLS.md"] = b.provenance_document(result, agents)
    return result


def search_for_plan(plan, client=None, config=None, refresh=False):
    """Candidats externes pour l'interface ; l'utilisateur approuve ensuite explicitement.

    Les candidats sont mis en cache (`search.cache_ttl_seconds`) ; `refresh` force une recherche reelle.
    """
    config = config or b.load_copy_policy()
    cache = SearchCache(ttl_from_config(config))
    return external.search(external.keywords_for_plan(plan), client or default_client(), config, cache, refresh)


def verify_approvals(approvals, client=None, config=None):
    """Controle en ligne des approbations (empreinte inchangee, etat amont), sans copie."""
    return external.verify_approvals(approvals, client or default_client(), config or b.load_copy_policy())
