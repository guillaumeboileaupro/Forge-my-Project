"""Cache a expiration des recherches de skills (E12).

Seuls les CANDIDATS d'une recherche sont mis en cache, jamais le contenu d'un
skill : une copie relit toujours GitHub au commit approuve et controle
l'empreinte (forge/skills/external.collect_approved). Un cache perime, altere
ou rempli a la main ne peut donc rien faire copier ; au pire il propose un
candidat que la copie refusera.

    <dossier d'etat>/skills-search/<sha256 de la requete>.json   (dossier 0700, fichier 0600)

La cle couvre les mots-cles, les catalogues, les options de recherche et le
transport (gh ou anonyme), qui changent les resultats. Une recherche degradee
(source indisponible) n'est pas mise en cache. Duree de vie :
`search.cache_ttl_seconds` (0 ou absent : pas de cache, 86 400 au plus).
"""
import hashlib
import json
import os
import secrets
import stat
import time

from forge.filesystem.bases import state_root
from forge.filesystem.destination import O_CLOEXEC, O_NOFOLLOW

SCHEMA_VERSION = 1
MAX_TTL = 86400
MAX_ENTRY_BYTES = 2 * 1024 * 1024


def ttl_from_config(config):
    value = config.get("search", {}).get("cache_ttl_seconds", 0)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, min(value, MAX_TTL))


def request_key(keywords, config, transport):
    material = {"keywords": sorted(keywords), "catalogs": config["external_catalogs"], "copy": config["copy"],
                "my_skills": config["my_skills"]["repository"], "transport": transport,
                "github": bool(config["search"].get("github_code_search")),
                "max": config["search"].get("max_candidates")}
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode("utf-8")).hexdigest()


class SearchCache:
    def __init__(self, ttl, directory=None, clock=time.time):
        self.ttl = ttl
        self.directory = directory
        self.clock = clock

    @property
    def enabled(self):
        return self.ttl > 0

    def _dir(self):
        return self.directory or state_root() / "skills-search"

    def _file(self, key):
        return self._dir() / (key + ".json")

    def get(self, key):
        """(contenu, age en secondes) si l'entree est valide et non expiree, sinon None."""
        if not self.enabled:
            return None
        try:
            fd = os.open(str(self._file(key)), os.O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
        except OSError:
            return None
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_ENTRY_BYTES:
                return None
            with os.fdopen(os.dup(fd), "rb") as handle:
                data = json.loads(handle.read().decode("utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            return None
        finally:
            os.close(fd)
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION or data.get("key") != key:
            return None
        created = data.get("created")
        if isinstance(created, bool) or not isinstance(created, (int, float)):
            return None
        age = self.clock() - created
        if age < 0 or age >= self.ttl:  # horloge revenue en arriere ou entree expiree
            return None
        return data.get("result"), int(age)

    def put(self, key, result):
        if not self.enabled:
            return False
        payload = json.dumps({"schema_version": SCHEMA_VERSION, "key": key, "created": self.clock(), "result": result},
                             ensure_ascii=False, sort_keys=True).encode("utf-8")
        if len(payload) > MAX_ENTRY_BYTES:
            return False
        directory, temp = self._dir(), None
        try:
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(str(directory), 0o700)
            target = self._file(key)
            temp = directory / (".%s.%s.tmp" % (target.name, secrets.token_hex(6)))
            fd = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
            try:
                view = memoryview(payload)
                while view:
                    view = view[os.write(fd, view):]
                os.fsync(fd)
            finally:
                os.close(fd)
            os.replace(str(temp), str(target))
        except OSError:
            if temp is not None:
                try:
                    temp.unlink()
                except OSError:
                    pass
            return False  # un cache inutilisable ne fait jamais echouer la recherche
        return True
