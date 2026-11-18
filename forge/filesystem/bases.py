"""Bases communes de la fusion a trois voies (E07) : ce que Forge a reellement ecrit.

Une base n'est fiable que si elle est exactement le contenu genere qu'une ecriture
reussie a laisse dans la destination. Elle est enregistree apres l'ecriture, par
destination, hors du projet de l'utilisateur :

    $FORGE_STATE_DIR, sinon $XDG_STATE_HOME/forge-my-project, sinon ~/.local/state/forge-my-project
    -> merge-bases/<sha256 du chemin de destination>.json   (dossier 0700, fichier 0600)

Chaque entree porte son empreinte SHA-256. Une base absente, alteree, illisible, trop
volumineuse ou enregistree pour une autre destination est ignoree : la fusion revient
alors au choix manuel (conserver, remplacer, fusionner a la main), jamais a une supposition.
"""
import hashlib
import json
import os
import secrets
import stat
from pathlib import Path

from forge.filesystem.compare import MAX_MERGEABLE
from forge.filesystem.destination import O_CLOEXEC, O_NOFOLLOW

SCHEMA_VERSION = 1
MAX_STORE_BYTES = 8 * 1024 * 1024


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def store_dir():
    explicit = os.environ.get("FORGE_STATE_DIR")
    if explicit:
        return Path(explicit) / "merge-bases"
    state = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state) / "forge-my-project" / "merge-bases"


def _store_file(destination):
    return store_dir() / (_digest(destination) + ".json")


def _read(destination):
    path = _store_file(destination)
    try:
        fd = os.open(str(path), os.O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
    except OSError:
        return {}
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_STORE_BYTES:
            return {}
        with os.fdopen(os.dup(fd), "rb") as handle:
            data = json.loads(handle.read().decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    finally:
        os.close(fd)
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION \
            or data.get("destination") != destination or not isinstance(data.get("files"), dict):
        return {}
    return data["files"]


def load(destination, paths):
    """Bases intactes {chemin: contenu} pour les chemins demandes ; le reste est absent."""
    stored, found = _read(destination), {}
    for path in paths:
        entry = stored.get(path)
        if not isinstance(entry, dict):
            continue
        content, digest = entry.get("content"), entry.get("sha256")
        if isinstance(content, str) and len(content.encode("utf-8")) <= MAX_MERGEABLE and digest == _digest(content):
            found[path] = content
    return found


def record(destination, contents):
    """Enregistre (fusionne) les contenus generes effectivement presents apres une ecriture reussie."""
    files = {p: e for p, e in _read(destination).items() if isinstance(e, dict)}
    for path, content in contents.items():
        if len(content.encode("utf-8")) <= MAX_MERGEABLE:
            files[path] = {"sha256": _digest(content), "content": content}
        else:
            files.pop(path, None)  # trop volumineux : pas de base, fusion manuelle
    payload = json.dumps({"schema_version": SCHEMA_VERSION, "destination": destination, "files": files},
                         ensure_ascii=False, sort_keys=True).encode("utf-8")
    if len(payload) > MAX_STORE_BYTES:
        return False  # aucune base enregistree plutot qu'une base partielle trompeuse
    directory = store_dir()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(str(directory), 0o700)
    target = _store_file(destination)
    temp = directory / (".%s.%s.tmp" % (target.name, secrets.token_hex(6)))
    fd = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
    try:
        view = memoryview(payload)
        while view:
            view = view[os.write(fd, view):]
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.replace(str(temp), str(target))
    except OSError:
        temp.unlink(missing_ok=True)
        raise
    return True


def forget(destination):
    """Supprime les bases d'une destination (tests, reinitialisation volontaire)."""
    try:
        _store_file(destination).unlink()
    except FileNotFoundError:
        pass
