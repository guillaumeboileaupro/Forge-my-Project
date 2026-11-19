"""Acces en lecture seule a un depot GitHub (API REST).

Deux transports :
- GhCliClient : reutilise l'authentification de la CLI `gh` si elle est
  presente et connectee (le jeton reste gere par gh, jamais lu ici) ;
- HttpClient : acces anonyme aux depots publics via la liste d'hotes autorisee.
Aucun ne modifie de depot distant.
"""
import json
import re
import shutil
import subprocess
from urllib.parse import quote

from forge.verification.http import FetchError, fetch_json, fetch_text

REPOSITORY = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")
REF = re.compile(r"^[A-Za-z0-9._/-]{1,100}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
API_PATH = re.compile(r"^/repos/[A-Za-z0-9._/%?=&-]+$|^/search/code\?q=[A-Za-z0-9+:._%-]+&per_page=\d{1,3}$")


def check_repository(repository, ref):
    if not REPOSITORY.fullmatch(repository or "") or not REF.fullmatch(ref or "") or ".." in ref:
        raise FetchError("Depot ou reference invalide")


def contents_path(repository, path, sha):
    return "/repos/%s/contents/%s?ref=%s" % (repository, quote(path), sha)


class HttpClient:
    """Acces anonyme (depots publics uniquement, quota d'API reduit)."""

    name = "https-anonyme"

    def get_json(self, api_path):
        response = fetch_json("https://api.github.com" + api_path)
        if response.status == 404:
            raise FetchError("Ressource GitHub introuvable : " + api_path)
        return response.data

    def get_text(self, repository, path, sha):
        url = "https://raw.githubusercontent.com/%s/%s/%s" % (repository, sha, quote(path))
        response = fetch_text(url)
        if response.status == 404:
            raise FetchError("Fichier introuvable : " + path)
        return response.data


class GhCliClient:
    """Appels `gh api` en lecture (GET uniquement), sans shell."""

    name = "gh-cli"

    def __init__(self, executable="gh", timeout=30):
        self.executable = executable
        self.timeout = timeout

    def _run(self, args):
        try:
            result = subprocess.run([self.executable, *args], capture_output=True, timeout=self.timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise FetchError("gh indisponible") from exc
        if result.returncode != 0:
            # Le corps d'erreur peut contenir des donnees distantes : ne conserver
            # que le statut HTTP, jamais la sortie complete ni un jeton.
            stderr = result.stderr if isinstance(result.stderr, bytes) else b""
            match = re.search(rb"HTTP (\d{3})", stderr)
            status = " HTTP %s" % match.group(1).decode("ascii") if match else ""
            raise FetchError("gh api a echoue%s (code %d)" % (status, result.returncode))
        return result.stdout

    def get_json(self, api_path):
        if not API_PATH.fullmatch(api_path):
            raise FetchError("Chemin d'API refuse")
        try:
            return json.loads(self._run(["api", "--method", "GET", api_path]).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FetchError("Reponse gh invalide") from exc

    def get_text(self, repository, path, sha):
        api_path = contents_path(repository, path, sha)
        if not API_PATH.fullmatch(api_path):
            raise FetchError("Chemin d'API refuse")
        raw = self._run(["api", "--method", "GET", "-H", "Accept: application/vnd.github.raw", api_path])
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise FetchError("Contenu non textuel : " + path) from exc

    def authenticated(self):
        try:
            self._run(["auth", "status", "--hostname", "github.com"])
        except FetchError:
            return False
        return True


def default_client():
    """gh authentifie si disponible, sinon acces HTTPS anonyme."""
    if shutil.which("gh"):
        client = GhCliClient()
        if client.authenticated():
            return client
    return HttpClient()
