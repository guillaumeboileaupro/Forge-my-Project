"""Catalogue et regles personnels, editables localement (E13).

    $FORGE_LOCAL_CATALOG_DIR, sinon $XDG_CONFIG_HOME/forge-my-project/catalogs,
    sinon ~/.config/forge-my-project/catalogs
      technologies/*.json   meme format que catalogs/technologies (categorie existante)
      rules/*.json          meme format que catalogs/rules
      templates/**.tmpl     templates des regles locales

Ces fichiers sont des DONNEES : lus, bornes et valides comme le catalogue de Forge,
jamais executes ni importes. Ils ajoutent des elements, sans jamais remplacer une
technologie, une regle ou un fichier produit par Forge (pas d'`override`). Les
commandes d'une technologie locale ne sont jamais lancees par Forge : elles sont
ecrites dans la CI et les hooks du projet genere, et signalees a relire.
Dossier absent : aucun ajout. Fichier invalide, trop gros ou trop nombreux, lien
symbolique : erreur explicite (aucun chargement partiel).
"""
import os
import stat
from pathlib import Path

O_NOFOLLOW_FLAGS = getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)

MAX_FILES = 16  # fichiers JSON par dossier
MAX_JSON_BYTES = 64 * 1024
MAX_TEMPLATES = 32
MAX_TEMPLATE_BYTES = 64 * 1024
MAX_TECHNOLOGIES = 32
MAX_RULES = 32
LOCAL_TEMPLATE_PREFIX = "@local/"  # distingue un template local d'un template de Forge


class LocalCatalogError(ValueError):
    """Converti en CatalogError / RuleError par les chargeurs."""


def local_dir():
    explicit = os.environ.get("FORGE_LOCAL_CATALOG_DIR")
    if explicit:
        return Path(explicit)
    config = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config) / "forge-my-project" / "catalogs"


def _require(condition, message):
    if not condition:
        raise LocalCatalogError("Catalogue local : " + message)


def _directory(path):
    """True si le dossier existe (et n'est pas un lien), False s'il est absent."""
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return False
    _require(stat.S_ISDIR(info.st_mode), "%s n'est pas un dossier (lien symbolique refuse)" % path)
    return True


def read_bounded(path, limit):
    """Lit un fichier ordinaire (jamais un lien) de `limit` octets au plus, en UTF-8."""
    try:
        fd = os.open(str(path), os.O_RDONLY | O_NOFOLLOW_FLAGS)
    except OSError as exc:
        raise LocalCatalogError("Catalogue local : %s illisible ou lien symbolique (%s)" % (path, exc.strerror)) from exc
    try:
        info = os.fstat(fd)
        _require(stat.S_ISREG(info.st_mode), "%s n'est pas un fichier ordinaire" % path)
        _require(info.st_size <= limit, "%s depasse %d octets" % (path, limit))
        data = os.read(fd, limit + 1)
    finally:
        os.close(fd)
    _require(len(data) <= limit, "%s depasse %d octets" % (path, limit))
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LocalCatalogError("Catalogue local : %s n'est pas en UTF-8" % path) from exc


def json_files(kind, root=None):
    """[(chemin, texte)] des fichiers JSON locaux `kind` (technologies ou rules), tries par nom."""
    directory = (root or local_dir()) / kind
    if not _directory(directory):
        return []
    entries = sorted(os.scandir(directory), key=lambda e: e.name)
    found = [e for e in entries if e.name.endswith(".json")]
    _require(len(found) <= MAX_FILES, "%s contient plus de %d fichiers JSON" % (directory, MAX_FILES))
    return [(Path(e.path), read_bounded(e.path, MAX_JSON_BYTES)) for e in found]


def templates_dir(root=None):
    return (root or local_dir()) / "templates"


def check_templates(root=None):
    """Borne le dossier des templates locaux (nombre, taille, aucun lien) ; retourne son chemin."""
    directory = templates_dir(root)
    if not _directory(directory):
        return directory
    count = 0
    for current, dirs, files in os.walk(directory, followlinks=False):
        for name in dirs:
            _require(not os.path.islink(os.path.join(current, name)), "lien symbolique refuse : %s" % name)
        for name in files:
            path = os.path.join(current, name)
            _require(not os.path.islink(path), "lien symbolique refuse : %s" % path)
            count += 1
            _require(count <= MAX_TEMPLATES, "plus de %d templates locaux" % MAX_TEMPLATES)
            _require(os.path.getsize(path) <= MAX_TEMPLATE_BYTES, "%s depasse %d octets" % (path, MAX_TEMPLATE_BYTES))
    return directory
