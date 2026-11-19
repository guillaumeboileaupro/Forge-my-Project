"""Preparation manuelle d'une protection de branche GitHub (E09).

L'inspection n'utilise que des requetes GET. La commande de mutation est du
texte retourne a l'utilisateur : ce module ne l'execute jamais.
"""
import json
from dataclasses import dataclass
from urllib.parse import quote

from forge.skills.github import FetchError, GhCliClient, REPOSITORY, REF

ATTRIBUTION_CHECK = "Attribution Git (aucun agent IA auteur, committer ou co-auteur)"


@dataclass(frozen=True)
class Inspection:
    repository: str
    branch: str
    head_sha: str
    checks: tuple[str, ...]
    conclusions: dict[str, tuple[str, ...]]
    permissions: dict[str, bool]
    protection_active: bool | None


def _validate(repository, branch):
    if not isinstance(repository, str) or not REPOSITORY.fullmatch(repository):
        raise ValueError("Depot invalide : utiliser owner/repository")
    if not isinstance(branch, str) or not REF.fullmatch(branch) or ".." in branch:
        raise ValueError("Branche invalide")


def inspect(client, repository, branch):
    """Inspecte depot, branche, checks et protection avec des GET uniquement."""
    _validate(repository, branch)
    repo_path = "/repos/%s" % repository
    try:
        repo = client.get_json(repo_path)
    except FetchError as exc:
        raise ValueError("Depot absent ou inaccessible") from exc
    encoded_branch = quote(branch, safe="")
    try:
        branch_data = client.get_json("%s/branches/%s" % (repo_path, encoded_branch))
    except FetchError as exc:
        raise ValueError("Branche inexistante ou inaccessible") from exc
    head_sha = branch_data.get("commit", {}).get("sha", "")
    if not isinstance(head_sha, str) or len(head_sha) != 40:
        raise ValueError("La branche ne fournit pas de commit de tete valide")
    try:
        check_data = client.get_json("%s/commits/%s/check-runs?per_page=100" % (repo_path, head_sha))
    except FetchError as exc:
        raise ValueError("Controles CI inaccessibles avec les permissions actuelles") from exc
    conclusions = {}
    for item in check_data.get("check_runs", []):
        if isinstance(item, dict) and isinstance(item.get("name"), str) and item["name"].strip():
            conclusions.setdefault(item["name"].strip(), set()).add(str(item.get("conclusion")))
    checks = sorted(conclusions)
    try:
        client.get_json("%s/branches/%s/protection" % (repo_path, encoded_branch))
        protected = True
    except FetchError as exc:
        protected = False if "HTTP 404" in str(exc) or "introuvable" in str(exc).lower() else None
    raw_permissions = repo.get("permissions", {}) if isinstance(repo, dict) else {}
    permissions = {name: bool(raw_permissions.get(name)) for name in ("admin", "maintain", "push")}
    return Inspection(repository, branch, head_sha, tuple(checks),
                      {name: tuple(sorted(found)) for name, found in conclusions.items()}, permissions, protected)


def _command(repository, branch, checks):
    payload = {
        "required_status_checks": {
            "strict": True,
            "checks": [{"context": name} for name in checks],
        },
        "enforce_admins": True,
        "required_pull_request_reviews": None,
        "restrictions": None,
        "allow_force_pushes": False,
        "allow_deletions": False,
    }
    endpoint = "repos/%s/branches/%s/protection" % (repository, quote(branch, safe=""))
    return "gh api --method PUT %s --input - <<'JSON'\n%s\nJSON" % (
        json.dumps(endpoint), json.dumps(payload, ensure_ascii=False, indent=2))


def prepare(repository, branch, client=None):
    """Retourne l'aperçu et la commande manuelle, sans effectuer la mutation."""
    client = client or GhCliClient()
    if not client.authenticated():
        raise ValueError("GitHub CLI absente ou non authentifiee ; executer `gh auth login` puis reessayer")
    result = inspect(client, repository, branch)
    # Seuls les controles reussis a chaque execution sur le commit de tete deviennent obligatoires :
    # exiger un controle en echec, annule, ignore ou en cours bloquerait toute fusion.
    passing = [name for name in result.checks if result.conclusions[name] == ("success",)]
    warnings = ["Controle %s non propose : conclusion %s sur le commit de tete."
                % (name, ", ".join(result.conclusions[name])) for name in result.checks if name not in passing]
    if not result.checks:
        warnings.append("Aucun controle CI observe sur le commit de tete ; aucun controle n'est declare disponible.")
    if ATTRIBUTION_CHECK not in passing:
        warnings.append("Le controle d'attribution Git n'a pas ete observe en succes : la commande n'est pas generee tant qu'il n'est pas verifie.")
    can_admin = result.permissions["admin"]
    if not can_admin:
        warnings.append("Permission insuffisante : un acces Administration en ecriture est necessaire pour executer la commande.")
    if result.protection_active is None:
        warnings.append("Protection actuelle NON VERIFIEE : les permissions ne permettent pas de la lire.")
    proposed = passing
    command = _command(repository, branch, proposed) if proposed and ATTRIBUTION_CHECK in proposed else None
    return {
        "repository": repository,
        "branch": branch,
        "head_sha": result.head_sha,
        "available_checks": list(result.checks),
        "check_conclusions": {name: list(found) for name, found in result.conclusions.items()},
        "required_checks": proposed,
        "attribution_check": ATTRIBUTION_CHECK,
        "attribution_verified": ATTRIBUTION_CHECK in passing,
        "permissions": result.permissions,
        "required_permission": "Administration: write",
        "can_apply": can_admin,
        "protection_active": result.protection_active,
        "protection_verified": result.protection_active is not None,
        "warnings": warnings,
        "command": command,
        "manual_only": True,
    }
