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

from forge.filesystem import bases as base_store
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


def _known_bases(destination, files):
    """Bases fiables : contenus generes enregistres apres une ecriture reussie (forge.filesystem.bases)."""
    return base_store.load(destination.path, files)


def _remember_bases(destination, generated, operations):
    """Le contenu genere devient la base des fichiers ecrits ou deja identiques ; un fichier
    conserve garde son ancienne base. Un echec d'enregistrement n'annule pas l'ecriture
    reussie : la prochaine comparaison proposera seulement la fusion manuelle."""
    written = {op["path"]: generated[op["path"]] for op in operations
               if op["action"] in ("created", "replaced", "merged", "identical") and op["path"] in generated}
    try:
        saved = base_store.record(destination.path, written) if written else True
    except OSError as exc:
        return "non enregistrees (%s) : fusion automatique indisponible a la prochaine ecriture" % exc.strerror
    return "enregistrees" if saved else "non enregistrees (trop volumineuses) : fusion manuelle a la prochaine ecriture"


def _scan(destination, files, bases=None):
    with destination.open() as fd:
        return compare(fd, files, bases)


def compare_destination(value, files):
    """Destination decrite, entrees comparees, resume et jeton de validation."""
    destination = Destination(value)
    bases = _known_bases(destination, files)
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


def write_destination(value, files, generated, token, decisions, confirm):
    """Ecrit apres confirmation ; rapport detaille (crees, remplaces, fusionnes, conserves, identiques)."""
    if confirm is not True:
        raise DecisionError("Confirmation explicite requise avant l'ecriture")
    destination = Destination(value)
    bases = _known_bases(destination, files)
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
    report["merge_bases"] = _remember_bases(destination, generated, report["operations"])
    return report
