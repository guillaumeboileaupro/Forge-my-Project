"""Choix de versions npm compatibles entre elles (peerDependencies).

Pour les packages npm selectionnes, cherche la combinaison de versions stables
la plus recente (ordre de priorite donne) telle que chaque peerDependency
declaree entre ces packages soit satisfaite. Recherche bornee avec retour
arriere : au-dela de la borne ou sur une plage illisible, NON VERIFIE.
"""
from forge.diagnostics import Status
from forge.verification import semver
from forge.verification.checks import Check, npm_url
from forge.verification.http import FetchError

MAX_CANDIDATES = 80
MAX_STEPS = 50000


class _Budget(Exception):
    pass


def _metadata(name, fetch):
    try:
        response = fetch(npm_url(name))
    except FetchError:
        return None
    return response.data if response.status == 200 and isinstance(response.data, dict) else None


def _candidates(meta, wanted):
    if wanted:
        return [wanted] if wanted in (meta.get("versions") or {}) else []
    latest = semver.parse_stable((meta.get("dist-tags") or {}).get("latest", ""))
    versions = semver.stable_versions(meta)
    if latest:
        versions = [v for v in versions if semver.parse_stable(v) <= latest]
    return versions[:MAX_CANDIDATES]


def _peers(meta, version):
    return ((meta.get("versions") or {}).get(version) or {}).get("peerDependencies") or {}


def _compatible(name, version, other, other_version, metas):
    """Contrainte binaire : peerDependencies declarees dans les deux sens."""
    mine = _peers(metas[name], version).get(other)
    if mine and not semver.satisfies(other_version, mine):
        return False
    theirs = _peers(metas[other], other_version).get(name)
    return not theirs or semver.satisfies(version, theirs)


def _search(order, candidates, metas):
    """Retour arriere avec filtrage en avant des domaines (detection immediate des impasses)."""
    steps = [0]

    def assign(index, domains, chosen):
        if index == len(order):
            return dict(chosen)
        name = order[index]
        for version in domains[name]:
            steps[0] += 1
            if steps[0] > MAX_STEPS:
                raise _Budget()
            pruned = {}
            for other in order[index + 1:]:
                pruned[other] = [v for v in domains[other] if _compatible(name, version, other, v, metas)]
                if not pruned[other]:
                    break
            else:
                chosen[name] = version
                found = assign(index + 1, dict(domains, **pruned), chosen)
                if found is not None:
                    return found
                del chosen[name]
        return None

    return assign(0, dict(candidates), {})


def resolve(requested, fetch):
    """requested : liste ordonnee de (package, version voulue ou None).

    Retourne ({package: version}, Check). Les packages introuvables sont omis
    (leur controle de registre les signale deja).
    """
    metas, candidates = {}, {}
    for name, wanted in requested:
        meta = _metadata(name, fetch)
        if meta is not None and _candidates(meta, wanted):
            metas[name], candidates[name] = meta, _candidates(meta, wanted)
    order = [name for name, _ in requested if name in metas]
    if not order:
        return {}, None
    try:
        chosen = _search(order, candidates, metas)
    except _Budget:
        return {}, Check("compatibility", "npm", Status.NON_VERIFIE, "Recherche de versions compatibles trop longue")
    except ValueError as exc:
        return {}, Check("compatibility", "npm", Status.NON_VERIFIE, "Plage de peerDependencies illisible : %s" % exc)
    if chosen is None:
        return {}, Check("compatibility", "npm", Status.FAIL,
                         "Aucune combinaison de versions ne satisfait les peerDependencies : " + ", ".join(order))
    adjusted = ["%s %s (derniere : %s)" % (n, v, candidates[n][0]) for n, v in chosen.items() if v != candidates[n][0]]
    message = "peerDependencies satisfaites" + (" ; versions ajustees : " + ", ".join(adjusted) if adjusted else "")
    return chosen, Check("compatibility", "npm", Status.PASS, message, "", {"versions": dict(chosen)})
