"""Selection et recuperation des skills du depot my-skills (T09).

Les skills retenus sont ceux recommandes par les regles locales (selection
deterministe). Le depot est lu a un commit precis (provenance), en lecture
seule ; seuls des fichiers texte sont copies.
"""
from dataclasses import dataclass

from forge.skills import bundle as b
from forge.skills.github import SHA, check_repository, default_client
from forge.verification.http import FetchError


@dataclass(frozen=True)
class Snapshot:
    repository: str
    commit: str
    entries: dict  # nom du skill -> liste de (chemin relatif, mode, taille)


def fetch_snapshot(client, repository, ref, base_path):
    check_repository(repository, ref)
    commit = (client.get_json("/repos/%s/commits/%s" % (repository, ref)) or {}).get("sha", "")
    if not SHA.fullmatch(commit):
        raise FetchError("Commit introuvable pour " + ref)
    tree = client.get_json("/repos/%s/git/trees/%s?recursive=1" % (repository, commit)) or {}
    if tree.get("truncated"):
        raise FetchError("Arborescence tronquee par l'API GitHub")
    prefix = base_path.strip("/") + "/"
    entries = {}
    for item in tree.get("tree", []):
        path = item.get("path", "")
        if item.get("type") != "blob" or not path.startswith(prefix):
            continue
        name, _, rel = path[len(prefix):].partition("/")
        if b.SKILL_NAME.fullmatch(name) and rel:
            entries.setdefault(name, []).append((rel, item.get("mode"), item.get("size")))
    return Snapshot(repository, commit, entries)


def _load_skill(name, snapshot, client, base_path, policy):
    record = b.SkillRecord(name, snapshot.repository, snapshot.commit, "copie")
    total = 0
    for rel, mode, size in sorted(snapshot.entries[name]):
        reason = b.classify_entry(rel, mode, size, policy)
        if reason is None and total + size > policy["max_skill_bytes"]:
            reason = "taille totale du skill depassee"
        if reason:
            record.notes.append("%s ignore : %s" % (rel, reason))
            continue
        record.files[rel] = client.get_text(snapshot.repository, "%s/%s/%s" % (base_path, name, rel), snapshot.commit)
        total += size
    if not b.validate_skill(record):
        record.status, record.files = "rejete", {}
    return record


def collect_skills(names, agents, client=None, config=None):
    """Recupere les skills demandes ; une indisponibilite produit des avertissements, pas d'echec."""
    config = config or b.load_copy_policy()
    source, policy = config["my_skills"], config["copy"]
    result = b.SkillBundle()
    if not names:
        return result
    try:
        client = client or default_client()
        snapshot = fetch_snapshot(client, source["repository"], source["ref"], source["path"])
    except FetchError as exc:
        for name in names:
            result.records.append(b.SkillRecord(name, source["repository"], "", "NON VERIFIE", notes=[str(exc)]))
    else:
        for name in names:
            if name not in snapshot.entries:
                result.records.append(b.SkillRecord(name, source["repository"], snapshot.commit, "absent"))
                continue
            try:
                record = _load_skill(name, snapshot, client, source["path"], policy)
            except FetchError as exc:
                record = b.SkillRecord(name, source["repository"], snapshot.commit, "NON VERIFIE", notes=[str(exc)])
            result.records.append(record)
            if record.status == "copie":
                b.place(record, agents, result)
    for record in result.records:
        result.diagnostics.extend(b.record_diagnostics(record))
    result.files["docs/SKILLS.md"] = b.provenance_document(result, agents)
    return result


def skills_for_plan(plan, client=None, config=None):
    """Adaptateur pour generate(..., skills=...)."""
    return collect_skills(list(plan.composition.skills), plan.spec.agents, client, config)
