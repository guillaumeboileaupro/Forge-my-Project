"""Profils de configuration : predefinis (catalogs/profiles) et personnalises.

Un profil contient des reponses reutilisables (type, technologies, versions,
agents, securite, options, architecture) mais jamais le nom ni la description
d'un projet. Les profils personnalises sont stockes dans un fichier local de
l'utilisateur, hors de tout projet cible :
    $FORGE_PROFILES_FILE, sinon $XDG_CONFIG_HOME/forge-my-project/profiles.json,
    sinon ~/.config/forge-my-project/profiles.json
Ecriture atomique, permissions 0600 ; un fichier illisible n'est jamais ecrase.
"""
import json
import os
import re
import tempfile
import threading
from pathlib import Path

from forge import CATALOGS_DIR
from forge.config.answers import AnswersError, parse_answers

SCHEMA_VERSION = 1
PROFILE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
PROFILE_FIELDS = {"label", "description", "answers"}
PROJECT_SPECIFIC = ("name", "description")
MAX_PROFILES = 50
MAX_FILE_BYTES = 1024 * 1024
_LOCK = threading.Lock()


class ProfileError(ValueError):
    pass


class ProfileNotFound(ProfileError):
    pass


def default_path():
    explicit = os.environ.get("FORGE_PROFILES_FILE")
    if explicit:
        return Path(explicit)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(Path.home(), ".config")
    return Path(base) / "forge-my-project" / "profiles.json"


def _text(value, field, limit, required):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ProfileError("%s invalide (%d caracteres maximum%s)" % (field, limit, ", obligatoire" if required else ""))
    return " ".join("".join(ch for ch in value if ch.isprintable()).split())


def normalise_profile(data, catalog):
    """Valide {label, description, answers} ; retire les champs propres a un projet."""
    if not isinstance(data, dict) or set(data) - PROFILE_FIELDS:
        raise ProfileError("Profil : champs autorises label, description, answers")
    answers = data.get("answers")
    if not isinstance(answers, dict):
        raise ProfileError("Profil : reponses manquantes")
    answers = {k: v for k, v in answers.items() if k not in PROJECT_SPECIFIC}
    try:
        normalised = parse_answers(answers, catalog)
    except AnswersError as exc:
        raise ProfileError("Profil invalide : %s" % exc) from exc
    for key in PROJECT_SPECIFIC:
        normalised.pop(key)
    return {
        "label": _text(data.get("label"), "Libelle", 60, True),
        "description": _text(data.get("description", ""), "Description du profil", 200, False),
        "answers": normalised,
    }


def load_predefined(catalog, directory=None):
    """Charge et valide les profils fournis avec l'outil (erreur = catalogue a corriger)."""
    profiles = []
    for path in sorted(Path(directory or CATALOGS_DIR / "profiles").glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("schema_version") != SCHEMA_VERSION or not PROFILE_ID.fullmatch(raw.get("id", "")):
            raise ProfileError("Profil predefini invalide : " + path.name)
        body = normalise_profile({k: raw.get(k) for k in PROFILE_FIELDS if k in raw}, catalog)
        profiles.append(dict(body, id=raw["id"], kind="predefini"))
    return profiles


def _slug(label):
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:40] or "profil"
    return slug if slug[0].isalnum() else "p-" + slug


class ProfileStore:
    def __init__(self, catalog, path=None, reserved=()):
        self.catalog = catalog
        self.path = Path(path) if path else default_path()
        self.reserved = set(reserved)

    def _read(self):
        if not self.path.exists():
            return []
        if self.path.is_symlink() or not self.path.is_file() or self.path.stat().st_size > MAX_FILE_BYTES:
            raise ProfileError("Fichier de profils refuse (lien, type ou taille) : %s" % self.path)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProfileError("Fichier de profils illisible, non modifie : %s" % self.path) from exc
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("profiles"), list):
            raise ProfileError("Fichier de profils incompatible, non modifie : %s" % self.path)
        profiles = []
        for item in data["profiles"]:
            if not isinstance(item, dict) or not PROFILE_ID.fullmatch(str(item.get("id", ""))):
                raise ProfileError("Profil enregistre invalide dans %s" % self.path)
            body = normalise_profile({k: item.get(k) for k in PROFILE_FIELDS if k in item}, self.catalog)
            profiles.append(dict(body, id=item["id"], kind="personnalise"))
        return profiles

    def _write(self, profiles):
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        stored = [{k: p[k] for k in ("id", "label", "description", "answers")} for p in profiles]
        payload = json.dumps({"schema_version": SCHEMA_VERSION, "profiles": stored}, ensure_ascii=False, indent=2)
        fd, tmp = tempfile.mkstemp(prefix=".profiles-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload + "\n")
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def list(self):
        with _LOCK:
            return self._read()

    def create(self, data):
        body = normalise_profile(data, self.catalog)
        with _LOCK:
            profiles = self._read()
            if len(profiles) >= MAX_PROFILES:
                raise ProfileError("Nombre maximal de profils atteint (%d)" % MAX_PROFILES)
            taken = self.reserved | {p["id"] for p in profiles}
            base = _slug(body["label"])
            profile_id, index = base, 2
            while profile_id in taken:
                profile_id, index = "%s-%d" % (base, index), index + 1
            profile = dict(body, id=profile_id, kind="personnalise")
            self._write(profiles + [profile])
            return profile

    def update(self, profile_id, data):
        body = normalise_profile(data, self.catalog)
        with _LOCK:
            profiles = self._read()
            for index, profile in enumerate(profiles):
                if profile["id"] == profile_id:
                    profiles[index] = dict(body, id=profile_id, kind="personnalise")
                    self._write(profiles)
                    return profiles[index]
        raise self._missing(profile_id)

    def delete(self, profile_id):
        with _LOCK:
            profiles = self._read()
            remaining = [p for p in profiles if p["id"] != profile_id]
            if len(remaining) == len(profiles):
                raise self._missing(profile_id)
            self._write(remaining)

    def _missing(self, profile_id):
        if profile_id in self.reserved:
            return ProfileError("Les profils predefinis ne sont pas modifiables")
        return ProfileNotFound("Profil introuvable : %s" % profile_id)
