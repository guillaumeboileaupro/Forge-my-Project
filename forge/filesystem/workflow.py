"""Comparaison puis ecriture confirmee dans une destination locale (T17).

Independant du transport HTTP : recoit les fichiers deja regeneres et valides.
La comparaison renvoie un jeton HMAC lie a la destination, aux contenus prepares
et a l'etat de chaque cible ; l'ecriture exige ce jeton, sinon la validation est
perimee (configuration, editions ou destination modifiees depuis).
"""
import hashlib
import hmac
import json
import secrets

from forge.filesystem.compare import MAX_MERGEABLE, compare, sha256
from forge.filesystem.content import ContentError, check_modified, check_paths
from forge.filesystem.destination import Destination
from forge.filesystem.writer import apply_changes

ACTIONS = ("keep", "replace", "merge", "auto")
_KEY = secrets.token_bytes(32)  # propre au processus : un jeton ne survit pas a un redemarrage


class DecisionError(ValueError):
    """Decision de fusion manquante, inconnue ou invalide."""


class StaleValidation(RuntimeError):
    """Jeton absent ou different : comparer a nouveau avant d'ecrire."""


def _token(destination, files, states, bases=None):
    material = json.dumps({"destination": destination.path, "files": {p: sha256(c.encode("utf-8")) for p, c in files.items()},
                           "states": states, "bases": {p: sha256(c.encode("utf-8")) for p, c in (bases or {}).items()}},
                          sort_keys=True).encode("utf-8")
    return hmac.new(_KEY, material, hashlib.sha256).hexdigest()


def _scan(destination, files, bases=None):
    with destination.open() as fd:
        return compare(fd, files, bases)


def validate_bases(files, bases):
    """Revalide une base explicite; son absence desactive simplement la fusion automatique."""
    if bases is None:
        return {}
    if not isinstance(bases, dict) or set(bases) - set(files):
        raise DecisionError("bases : objet optionnel limite aux chemins prepares")
    for path, content in bases.items():
        if not isinstance(path, str) or not isinstance(content, str) or "\x00" in content:
            raise DecisionError("Base commune invalide pour %s" % path)
        if len(content.encode("utf-8")) > MAX_MERGEABLE:
            raise DecisionError("Base commune trop volumineuse pour %s" % path)
    return dict(bases)


def compare_destination(value, files, bases=None):
    """Destination decrite, entrees comparees, resume et jeton de validation."""
    bases = validate_bases(files, bases)
    destination = Destination(value)
    info = destination.describe()
    entries, states = _scan(destination, files, bases)
    summary = {status: sum(1 for e in entries if e["status"] == status) for status in ("new", "identical", "conflict", "blocked")}
    return {"destination": info, "entries": entries, "summary": summary,
            "token": _token(destination, files, states, bases)}


def _decisions(entries, decisions, generated):
    if not isinstance(decisions, dict):
        raise DecisionError("decisions : objet chemin -> {action, content} attendu")
    by_path = {e["path"]: e for e in entries}
    conflicts = {p for p, e in by_path.items() if e["status"] == "conflict"}
    unknown = sorted(set(decisions) - conflicts)
    if unknown:
        raise DecisionError("Decision pour un fichier sans conflit : " + ", ".join(unknown))
    missing = sorted(conflicts - set(decisions))
    if missing:
        raise DecisionError("Choisir conserver, remplacer ou fusionner pour : " + ", ".join(missing))
    chosen, problems = {}, []
    for path in sorted(conflicts):
        item = decisions[path]
        if not isinstance(item, dict) or item.get("action") not in ACTIONS or set(item) - {"action", "content"}:
            raise DecisionError("Decision invalide pour %s (keep, replace, auto ou merge)" % path)
        if item["action"] == "merge":
            content = item.get("content")
            if not by_path[path]["mergeable"]:
                raise DecisionError("Fusion impossible pour %s : conserver ou remplacer" % path)
            if not isinstance(content, str) or "\x00" in content or len(content.encode("utf-8", "replace")) > MAX_MERGEABLE:
                raise DecisionError("Contenu fusionne invalide pour %s" % path)
            problems.extend(check_modified(path, generated[path], content))
        elif item["action"] == "auto" and by_path[path]["auto_merge"] is None:
            raise DecisionError("Fusion automatique impossible pour %s : resolution manuelle requise" % path)
        elif item["action"] == "auto":
            problems.extend(check_modified(path, generated[path], by_path[path]["auto_merge"]))
        elif "content" in item:
            raise DecisionError("content n'est accepte que pour merge (%s)" % path)
        chosen[path] = item
    if problems:
        raise ContentError(problems)
    return chosen


def write_destination(value, files, generated, token, decisions, confirm, bases=None):
    """Ecrit apres confirmation ; rapport detaille (crees, remplaces, fusionnes, conserves, identiques)."""
    if confirm is not True:
        raise DecisionError("Confirmation explicite requise avant l'ecriture")
    bases = validate_bases(files, bases)
    destination = Destination(value)
    if not destination.describe()["writable"]:
        raise DecisionError("Permissions insuffisantes : ecriture impossible dans %s" % destination.path)
    entries, states = _scan(destination, files, bases)
    if not isinstance(token, str) or not hmac.compare_digest(token, _token(destination, files, states, bases)):
        raise StaleValidation("Validation perimee : la destination, la configuration ou les fichiers ont change. "
                              "Comparer a nouveau avant d'ecrire.")
    blocked = [e["path"] for e in entries if e["status"] == "blocked"]
    if blocked:
        raise DecisionError("Ecriture refusee, entrees non sures dans la destination : " + ", ".join(blocked))
    problems = check_paths(files)
    if problems:
        raise ContentError(problems)
    chosen = _decisions(entries, decisions, generated)
    writes, skipped = {}, []
    for entry in entries:
        path, status = entry["path"], entry["status"]
        if status == "new":
            writes[path] = ("create", files[path].encode("utf-8"))
        elif status == "identical":
            skipped.append({"path": path, "action": "identical"})
        else:
            item = chosen[path]
            if item["action"] == "keep":
                skipped.append({"path": path, "action": "kept"})
            else:
                text = (item["content"] if item["action"] == "merge" else
                        entry["auto_merge"] if item["action"] == "auto" else files[path])
                action = "merge" if item["action"] in ("merge", "auto") else item["action"]
                writes[path] = (action, text.encode("utf-8"))
    report = apply_changes(destination, writes, states)
    report["operations"] = sorted(report["operations"] + skipped, key=lambda op: op["path"])
    report["summary"] = {action: sum(1 for op in report["operations"] if op["action"] == action)
                         for action in ("created", "replaced", "merged", "kept", "identical")}
    return report
