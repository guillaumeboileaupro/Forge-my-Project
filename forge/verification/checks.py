"""Controles unitaires : existence de package, version, licence, vulnerabilites, fin de vie.

Chaque controle retourne un Check avec un etat PASS / FAIL / NON VERIFIE et
la preuve (URL interrogee). `fetch` est injectable pour les tests.
"""
import re
from dataclasses import dataclass, field
from urllib.parse import quote

from forge.config import versions
from forge.diagnostics import Status
from forge.verification.http import FetchError, fetch_json

OSV_ECOSYSTEMS = {"pypi": "PyPI", "npm": "npm"}
BLOCKING_SEVERITIES = {"HIGH", "CRITICAL"}
KNOWN_SEVERITIES = BLOCKING_SEVERITIES | {"LOW", "MODERATE", "MEDIUM"}


@dataclass(frozen=True)
class Check:
    kind: str  # package | vulnerabilities | runtime | api
    subject: str
    status: Status
    message: str
    evidence: str = ""
    details: dict = field(default_factory=dict)

    def as_dict(self):
        return {"kind": self.kind, "subject": self.subject, "status": self.status.value,
                "message": self.message, "evidence": self.evidence, "details": dict(self.details)}


def pypi_url(name):
    normalised = re.sub(r"[-_.]+", "-", name).lower()  # PEP 503
    return "https://pypi.org/pypi/%s/json" % quote(normalised, safe="")


def npm_url(name):
    return "https://registry.npmjs.org/" + quote(name, safe="@")


def _first_line(value):
    return value.strip().splitlines()[0] if isinstance(value, str) and value.strip() else ""


def _pypi(data, wanted):
    """Retourne (version | None si absente | False si retiree, derniere version, licence)."""
    info = data.get("info") or {}
    releases = data.get("releases") or {}
    latest = info.get("version") or ""
    version = wanted or latest
    if version not in releases:
        return None, latest, ""
    files = releases[version] or []
    if files and all(f.get("yanked") for f in files):
        return False, latest, ""
    return version, latest, info.get("license_expression") or _first_line(info.get("license"))


def _npm(data, wanted):
    known = data.get("versions") or {}
    latest = (data.get("dist-tags") or {}).get("latest") or ""
    version = wanted or latest
    if version not in known:
        return None, latest, ""
    meta = known[version] or {}
    if meta.get("deprecated"):
        return False, latest, ""
    license_ = meta.get("license") or data.get("license")
    return version, latest, license_ if isinstance(license_, str) else ""


def check_package(ecosystem, name, wanted=None, fetch=fetch_json):
    url = pypi_url(name) if ecosystem == "pypi" else npm_url(name)
    subject = "%s:%s" % (ecosystem, name)
    try:
        response = fetch(url)
    except FetchError as exc:
        return Check("package", subject, Status.NON_VERIFIE, "Registre indisponible : %s" % exc, url)
    if response.status == 404:
        return Check("package", subject, Status.FAIL, "Package inexistant sur le registre officiel", url)
    if response.status != 200 or not isinstance(response.data, dict):
        return Check("package", subject, Status.NON_VERIFIE, "Reponse du registre inexploitable", url)
    version, latest, license_ = (_pypi if ecosystem == "pypi" else _npm)(response.data, wanted)
    if version is None:
        return Check("package", subject, Status.FAIL, "Version %s introuvable" % (wanted or "latest"), url, {"latest": latest})
    if version is False:
        return Check("package", subject, Status.FAIL, "Version retiree ou obsolete (yanked/deprecated)", url, {"latest": latest})
    details = {"version": version, "latest": latest, "license": license_ or "NON VERIFIE"}
    return Check("package", subject, Status.PASS, "Package et version presents sur le registre", url, details)


def _severity(vuln):
    raw = (vuln.get("database_specific") or {}).get("severity")
    return raw.upper() if isinstance(raw, str) else None


def check_vulnerabilities(ecosystem, name, version, fetch=fetch_json):
    url = "https://api.osv.dev/v1/query"
    subject = "%s:%s@%s" % (ecosystem, name, version)
    payload = {"package": {"name": name, "ecosystem": OSV_ECOSYSTEMS[ecosystem]}, "version": version}
    try:
        response = fetch(url, payload)
    except FetchError as exc:
        return Check("vulnerabilities", subject, Status.NON_VERIFIE, "Base OSV indisponible : %s" % exc, url)
    if response.status != 200 or not isinstance(response.data, dict):
        return Check("vulnerabilities", subject, Status.NON_VERIFIE, "Reponse OSV inexploitable", url)
    vulns = response.data.get("vulns") or []
    if response.data.get("next_page_token"):
        return Check("vulnerabilities", subject, Status.NON_VERIFIE, "Resultats OSV pagines non traites", url)
    severities = {v.get("id", "?"): _severity(v) for v in vulns}
    details = {"vulnerabilities": sorted(severities)}
    blocking = sorted(i for i, s in severities.items() if s in BLOCKING_SEVERITIES)
    unknown = sorted(i for i, s in severities.items() if s not in KNOWN_SEVERITIES)
    if blocking:
        return Check("vulnerabilities", subject, Status.FAIL, "Vulnerabilites haute/critique : " + ", ".join(blocking), url, details)
    if unknown:
        return Check("vulnerabilities", subject, Status.NON_VERIFIE, "Severite inconnue : " + ", ".join(unknown), url, details)
    message = "Aucune vulnerabilite connue" if not vulns else "Vulnerabilites non bloquantes : " + ", ".join(sorted(severities))
    return Check("vulnerabilities", subject, Status.PASS, message, url, details)


def _cycle_matches(cycle, version):
    try:
        return versions.parse(str(cycle)) == versions.parse(version)
    except ValueError:
        return False


def check_runtime(product, version, today, fetch=fetch_json):
    """Verifie qu'un cycle de version existe et n'est pas en fin de vie a la date `today` (ISO)."""
    url = "https://endoflife.date/api/%s.json" % quote(product, safe="")
    subject = "%s %s" % (product, version)
    try:
        response = fetch(url)
    except FetchError as exc:
        return Check("runtime", subject, Status.NON_VERIFIE, "endoflife.date indisponible : %s" % exc, url)
    if response.status != 200 or not isinstance(response.data, list):
        return Check("runtime", subject, Status.NON_VERIFIE, "Reponse endoflife.date inexploitable", url)
    cycle = next((c for c in response.data if isinstance(c, dict) and _cycle_matches(c.get("cycle"), version)), None)
    if cycle is None:
        return Check("runtime", subject, Status.FAIL, "Cycle de version inconnu", url)
    eol = cycle.get("eol")
    details = {"eol": str(eol), "latest": str(cycle.get("latest", ""))}
    if eol is True or isinstance(eol, str) and eol <= today:
        return Check("runtime", subject, Status.FAIL, "Version en fin de vie (%s)" % eol, url, details)
    if eol is False or isinstance(eol, str):
        return Check("runtime", subject, Status.PASS, "Version maintenue", url, details)
    return Check("runtime", subject, Status.NON_VERIFIE, "Date de fin de vie inconnue", url, details)


def api_unverified(tech):
    """Les API ne sont pas verifiables sans installer le package : etat explicite."""
    return Check("api", tech.id, Status.NON_VERIFIE,
                 "API non verifiee automatiquement : consulter la documentation officielle avant usage", tech.docs)


def check_action(repository, tag, sha, fetch=fetch_json):
    """Verifie que le tag d'une action GitHub designe toujours le commit epingle."""
    subject = "%s@%s" % (repository, tag)
    url = "https://api.github.com/repos/%s/git/ref/tags/%s" % (repository, quote(tag, safe=""))
    try:
        response = fetch(url)
        target = (response.data or {}).get("object") or {}
        if target.get("type") == "tag":  # tag annote : dereferencer vers le commit
            response = fetch(target.get("url", ""))
            target = (response.data or {}).get("object") or {}
    except FetchError as exc:
        return Check("action", subject, Status.NON_VERIFIE, "API GitHub indisponible : %s" % exc, url)
    if response.status == 404:
        return Check("action", subject, Status.FAIL, "Tag introuvable", url)
    if target.get("sha") != sha:
        return Check("action", subject, Status.FAIL, "Le tag ne pointe plus sur le SHA epingle %s" % sha[:12], url,
                     {"actual": str(target.get("sha", ""))})
    return Check("action", subject, Status.PASS, "Tag et SHA epingle concordants", url, {"sha": sha})

