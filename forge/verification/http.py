"""Acces HTTP en lecture seule vers une liste fermee de services officiels.

Le reseau n'est utilise que lorsqu'une verification est demandee
explicitement. Toute indisponibilite produit FetchError, traduite en
NON VERIFIE par les appelants : jamais en PASS.
"""
import json
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ALLOWED_HOSTS = {"pypi.org", "registry.npmjs.org", "api.osv.dev", "endoflife.date", "api.github.com", "raw.githubusercontent.com"}
MAX_BYTES = 20 * 1024 * 1024
USER_AGENT = "Forge-my-Project-verifier"


class FetchError(Exception):
    """Service injoignable ou reponse inexploitable."""


class Response:
    def __init__(self, status, data):
        self.status = status
        self.data = data


def _check_url(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS or parts.username or parts.port:
        raise FetchError("URL non autorisee : " + url)


def fetch_json(url, payload=None, timeout=15):
    """GET (ou POST JSON si payload) ; retourne Response. 404 n'est pas une erreur reseau."""
    _check_url(url)
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - schema et hote controles
            raw = response.read(MAX_BYTES + 1)
            status = response.status
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return Response(404, None)
        raise FetchError("HTTP %d pour %s" % (exc.code, url)) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FetchError("Service injoignable : %s" % url) from exc
    if len(raw) > MAX_BYTES:
        raise FetchError("Reponse trop volumineuse : " + url)
    try:
        return Response(status, json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FetchError("Reponse JSON invalide : " + url) from exc
