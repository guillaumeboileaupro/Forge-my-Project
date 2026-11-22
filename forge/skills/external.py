"""Recherche et copie des skills externes (T10).

Recherche : catalogues reconnus (catalogs/skills/sources.json) et, si la CLI
gh est authentifiee, recherche de code GitHub. Les resultats sont des
CANDIDATS : rien n'est copie sans approbation explicite, enregistree dans la
configuration (`external_skills`) avec le commit exact examine et l'empreinte
de l'arborescence du skill. Un skill dont l'empreinte a change depuis son
approbation est refuse (erreur bloquante) ; aucun script n'est copie ni execute.
"""
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from forge.skills import bundle as b
from forge.skills.cache import request_key
from forge.skills.github import GhCliClient, REPOSITORY
from forge.skills.my_skills import fetch_snapshot, load_skill
from forge.verification.http import FetchError

KEYWORD = re.compile(r"^[a-z0-9][a-z0-9-]{1,39}$")


@dataclass
class Candidate:
    repository: str
    commit: str
    path: str  # dossier parent du skill
    name: str
    description: str
    recognized: bool
    source: str
    score: int
    digest: str = ""
    copied_files: list = field(default_factory=list)
    ignored_files: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def approval(self):
        """Valeur a ajouter a `external_skills` si l'utilisateur approuve ce candidat."""
        return {"repository": self.repository, "commit": self.commit, "path": self.path, "name": self.name,
                "digest": self.digest}

    def as_dict(self):
        return dict(self.__dict__, approval=self.approval())


@dataclass
class SearchResult:
    candidates: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    degraded: bool = False  # une source n'a pas repondu : resultat partiel, jamais mis en cache
    cache_age: int = None  # secondes depuis la recherche reelle si le resultat vient du cache


def keywords_for_plan(plan):
    words = {plan.spec.project_type, *plan.resolution.ids()}
    return sorted(w for w in words if KEYWORD.fullmatch(w))


def _hits(keywords, text):
    text = text.lower()
    return sum(1 for word in keywords if re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(word), text))


def _score(keywords, name, description):
    """Mot-cle dans le nom : 2 points ; dans la description : 1 point. Calcul pur et deterministe."""
    return 2 * _hits(keywords, name.replace("-", " ")) + _hits(keywords, description)


def _rank_key(candidate):
    """Source reconnue d'abord, puis score decroissant ; egalites departagees sans dependre du reseau."""
    return (not candidate.recognized, -candidate.score, candidate.name, candidate.repository, candidate.path)


def _candidate(snapshot, base_path, name, client, policy, keywords, recognized, source):
    files = snapshot.entries[name]
    copied = [rel for rel, mode, size in files if b.classify_entry(rel, mode, size, policy) is None]
    ignored = ["%s (%s)" % (rel, b.classify_entry(rel, mode, size, policy)) for rel, mode, size in files if rel not in copied]
    if "SKILL.md" not in copied:
        return None
    meta = b.parse_frontmatter(client.get_text(snapshot.repository, "%s/%s/SKILL.md" % (base_path, name), snapshot.commit))
    description = meta.get("description", "")
    score = _score(keywords, name, description)
    if not score:
        return None
    notes = [] if recognized else ["Source non reconnue : examen manuel complet requis avant approbation"]
    if meta.get("name") != name:
        notes.append("En-tete SKILL.md invalide : sera rejete a la copie")
    digest = snapshot.digest(name)
    if not digest:
        return None  # sans empreinte, l'approbation ne pourrait pas etre controlee
    return Candidate(snapshot.repository, snapshot.commit, base_path, name, description, recognized, source, score,
                     digest, sorted(copied), sorted(ignored), notes)


def _attempt(function, *args):
    """(resultat, None) ou (None, erreur) : une source en echec n'interrompt pas les autres."""
    try:
        return function(*args), None
    except FetchError as exc:
        return None, exc


def _code_search(client, word):
    return (client.get_json("/search/code?q=filename:SKILL.md+%s&per_page=5" % word) or {}).get("items", [])


def _github_targets(responses, known):
    """Dossiers de skills uniques a examiner, dans l'ordre des mots-cles puis des reponses."""
    targets, seen = [], set()
    for items in responses:
        for item in items or ():
            repository = (item.get("repository") or {}).get("full_name", "")
            parts = (item.get("path") or "").split("/")
            if not REPOSITORY.fullmatch(repository) or repository in known or len(parts) < 3 or parts[-1] != "SKILL.md":
                continue
            name, base_path = parts[-2], "/".join(parts[:-2])
            if b.SKILL_NAME.fullmatch(name) and (repository, base_path, name) not in seen:
                seen.add((repository, base_path, name))
                targets.append((repository, base_path, name))
    return targets


def _run_search(keywords, client, config, out, workers):
    """Recherches paralleles en trois phases ; `map` conserve l'ordre des taches, pas celui des reponses."""
    policy, catalogs = config["copy"], config["external_catalogs"]
    use_github = bool(config["search"].get("github_code_search"))
    gh = use_github and isinstance(client, GhCliClient)
    if use_github and not gh:
        out.notes.append("Recherche de code GitHub NON VERIFIEE : necessite la CLI gh authentifiee")
    words = keywords[:3] if gh else []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        # 1. Arborescences des catalogues reconnus et recherches de code GitHub.
        snapshots = list(pool.map(lambda c: _attempt(fetch_snapshot, client, c["repository"], c["ref"], c["path"]),
                                  catalogs))
        searches = list(pool.map(lambda w: _attempt(_code_search, client, w), words))
        # 2. Arborescences des depots trouves par la recherche GitHub.
        known = {c["repository"] for c in catalogs} | {config["my_skills"]["repository"]}
        for word, (_, exc) in zip(words, searches):
            if exc:
                out.notes.append("Recherche GitHub NON VERIFIEE (%s) : %s" % (word, exc))
                out.degraded = True
        targets = _github_targets([items for items, _ in searches], known)
        found = list(pool.map(lambda t: _attempt(fetch_snapshot, client, t[0], "HEAD", t[1]), targets))
        # 3. En-tetes SKILL.md de chaque skill retenu.
        jobs = []
        for catalog, (snapshot, exc) in zip(catalogs, snapshots):
            if exc:
                out.notes.append("%s NON VERIFIE : %s" % (catalog["repository"], exc))
                out.degraded = True
                continue
            jobs += [(snapshot, catalog["path"], name, True, catalog["label"]) for name in sorted(snapshot.entries)]
        for (repository, base_path, name), (snapshot, exc) in zip(targets, found):
            if exc:
                out.notes.append("%s : %s" % (repository, exc))
                out.degraded = True
            elif name in snapshot.entries:
                jobs.append((snapshot, base_path, name, False, "recherche GitHub"))
        results = pool.map(lambda j: _attempt(_candidate, j[0], j[1], j[2], client, policy, keywords, j[3], j[4]), jobs)
        for job, (candidate, exc) in zip(jobs, results):
            if exc:
                out.notes.append("%s/%s NON VERIFIE : %s" % (job[0].repository, job[2], exc))
                out.degraded = True
            elif candidate:
                out.candidates.append(candidate)


def _workers(config):
    value = config["search"].get("max_workers", 4)
    return max(1, min(value, 8)) if isinstance(value, int) and not isinstance(value, bool) else 4


def search(keywords, client, config, cache=None, refresh=False):
    """Retourne des candidats tries par pertinence. Aucun fichier n'est copie.

    `cache` (SearchCache) : un resultat complet et non expire est reutilise sauf si `refresh`.
    """
    out = SearchResult()
    keywords = sorted({k for k in keywords if KEYWORD.fullmatch(k)})
    if not keywords:
        out.notes.append("Aucun mot-cle exploitable")
        return out
    key = request_key(keywords, config, getattr(client, "name", type(client).__name__))
    if cache and not refresh:
        hit = cache.get(key)
        restored = hit and _restore(hit[0])
        if restored:
            restored.cache_age = hit[1]
            return restored
    _run_search(keywords, client, config, out, _workers(config))
    unique = {(c.repository, c.path, c.name): c for c in out.candidates}
    out.candidates = sorted(unique.values(), key=_rank_key)[:config["search"]["max_candidates"]]
    if cache and not out.degraded:
        cache.put(key, {"candidates": [dict(c.__dict__) for c in out.candidates], "notes": out.notes})
    return out


def _restore(data):
    """Reconstruit un resultat mis en cache ; toute entree mal formee est ignoree (None)."""
    try:
        candidates = [Candidate(**item) for item in data["candidates"]]
        notes = [str(n) for n in data["notes"]]
    except (KeyError, TypeError):
        return None
    if not all(isinstance(c.repository, str) and REPOSITORY.fullmatch(c.repository) and isinstance(c.name, str)
               and b.SKILL_NAME.fullmatch(c.name) and isinstance(c.digest, str) and b.DIGEST.fullmatch(c.digest)
               for c in candidates):
        return None
    return SearchResult(candidates, notes)


MODIFIED = "modifie depuis son approbation (empreinte differente) : examiner puis approuver a nouveau"


def _approved_snapshot(client, repository, commit, path):
    snapshot = fetch_snapshot(client, repository, commit, path)
    if snapshot.commit != commit:
        raise FetchError("Commit different de celui approuve")
    return snapshot


def check_approval(snapshot, name, digest):
    """Retourne None si le skill est intact, sinon la raison du refus."""
    if name not in snapshot.entries:
        return "absent du commit approuve"
    if snapshot.digest(name) != digest:
        return MODIFIED
    return None


UPSTREAM_NOTES = {
    "inchange": "Version amont actuelle identique a l'approbation",
    "modifie": "Modifie en amont depuis l'approbation (%s) : la version approuvee est copiee ; "
               "examiner la nouvelle version avant de l'approuver",
    "absent": "Retire en amont depuis l'approbation (%s) : la version approuvee est copiee ; verifier pourquoi",
    "NON VERIFIE": "Etat amont NON VERIFIE : %s",
}


def upstream_state(client, repository, path, name, digest, ref):
    """Compare l'approbation a la version actuelle de la branche suivie : (etat, detail)."""
    try:
        snapshot = fetch_snapshot(client, repository, ref, path)
    except FetchError as exc:
        return "NON VERIFIE", str(exc)
    detail = "%s@%s" % (ref, snapshot.commit[:12])
    if name not in snapshot.entries:
        return "absent", detail
    return ("inchange" if snapshot.digest(name) == digest else "modifie"), detail


def upstream_message(state, detail):
    text = UPSTREAM_NOTES[state]
    return text % detail if "%s" in text else text


def tracked_refs(config):
    """Branche suivie par depot : celle du catalogue reconnu, sinon la branche par defaut (HEAD)."""
    return {c["repository"]: c["ref"] for c in config["external_catalogs"]}


def collect_approved(approvals, agents, client, config, result):
    """Copie les skills approuves, au commit et a l'empreinte approuves, avec les memes controles.

    Juste avant la copie, la branche suivie est relue : un changement amont depuis
    l'approbation est signale (la version approuvee reste la seule copiee).
    """
    policy = config["copy"]
    refs = tracked_refs(config)
    for repository, commit, path, name, digest in approvals:
        source = "%s (approuve%s)" % (repository, "" if repository in refs else ", source non reconnue")
        try:
            snapshot = _approved_snapshot(client, repository, commit, path)
            problem = check_approval(snapshot, name, digest)
            if problem:
                record = b.SkillRecord(name, source, commit, "absent" if name not in snapshot.entries else "modifie",
                                       notes=[problem])
            else:
                record = load_skill(name, snapshot, client, path, policy)
        except FetchError as exc:
            record = b.SkillRecord(name, source, commit, "NON VERIFIE", notes=[str(exc)])
        record.source = source
        if record.status == "copie":
            state, detail = upstream_state(client, repository, path, name, digest, refs.get(repository, "HEAD"))
            record.upstream = state
            record.notes.append(upstream_message(state, detail))
        result.records.append(record)
        if record.status == "copie":
            b.place(record, agents, result)
    return result


def verify_approvals(approvals, client, config=None):
    """Controle en ligne des approbations (import, reprise) sans rien copier.

    Statuts : PASS (intact), FAIL (absent ou modifie), NON VERIFIE (inaccessible).
    `upstream` indique en plus l'etat de la branche suivie (inchange, modifie, absent, NON VERIFIE).
    """
    checks, refs = [], tracked_refs(config) if config else {}
    for repository, commit, path, name, digest in approvals:
        item = {"repository": repository, "commit": commit, "path": path, "name": name, "digest": digest}
        try:
            problem = check_approval(_approved_snapshot(client, repository, commit, path), name, digest)
        except FetchError as exc:
            checks.append(dict(item, status="NON VERIFIE", message=str(exc)))
            continue
        state, detail = upstream_state(client, repository, path, name, digest, refs.get(repository, "HEAD"))
        checks.append(dict(item, status="FAIL" if problem else "PASS", message=problem or "Empreinte identique",
                           upstream=state, upstream_message=upstream_message(state, detail)))
    return checks

