"""Verification statique des API utilisees par les projets generes (E11).

Un contrat d'API est un import reellement present dans un fichier genere (Python : `ast` ;
JavaScript/TypeScript : declarations `import`), ou le module importable annonce par le
catalogue pour une bibliotheque Python. Rien n'est execute ni installe : le code publie est
lu comme du texte.

- Hors ligne : bibliotheque standard Python, modules integres Node et fichiers locaux sont
  PASS ; un module tiers non declare dans le manifeste est FAIL ; le reste est NON VERIFIE.
- En ligne (verification explicite) : archive npm (integrite SHA-512) et roue PyPI
  (empreinte SHA-256) sont lues pour prouver sous-chemins, exports nommes, export par defaut,
  proprietes et modules. Une absence demontree est FAIL ; une analyse impossible (reexport
  externe, paquet sans declarations, source indisponible) reste NON VERIFIE, jamais PASS.
"""
import ast
import base64
import hashlib
import io
import json
import posixpath
import re
import sys
import tarfile
import zipfile
from dataclasses import dataclass

from forge.diagnostics import Status
from forge.verification.checks import Check, npm_url, pypi_url
from forge.verification.http import FetchError

NODE_BUILTINS = frozenset({
    "assert", "assert/strict", "async_hooks", "buffer", "child_process", "cluster", "console", "crypto", "dns",
    "events", "fs", "fs/promises", "http", "http2", "https", "module", "net", "os", "path", "path/posix",
    "perf_hooks", "process", "readline", "stream", "stream/promises", "string_decoder", "test", "timers",
    "timers/promises", "tls", "tty", "url", "util", "v8", "vm", "worker_threads", "zlib",
})
JS_SUFFIXES = (".js", ".mjs", ".cjs", ".ts", ".mts", ".tsx", ".jsx")
JS_IMPORT = re.compile(r"""^\s*import\s+(?:type\s+)?(?P<clause>[^'"]*?)\s*from\s*["'](?P<spec>[^"']+)["']|^\s*import\s*["'](?P<bare>[^"']+)["']""", re.M)
JS_DYNAMIC_IMPORT = re.compile(r"""\bimport\(\s*["'](?P<spec>[^"']+)["']\s*\)""")  # chemin litteral uniquement
MAX_ARCHIVE_FILES = 5000
MAX_FOLLOW = 6


@dataclass(frozen=True)
class Contract:
    language: str          # python | javascript
    module: str            # specificateur importe
    names: tuple = ()      # exports nommes importes ; "default" pour l'import par defaut
    members: tuple = ()    # chemins de proprietes utilises sur l'import par defaut ("configs.recommended")
    source: str = ""       # fichier:ligne, ou catalogue

    @property
    def subject(self):
        detail = ", ".join(self.names + self.members)
        return "%s:%s%s" % (self.language, self.module, " {%s}" % detail if detail else "")


# --- Extraction ---------------------------------------------------------------------------

def _python_contracts(path, text):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [Contract("python", alias.name, (), (), "%s:%d" % (path, node.lineno)) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names = tuple(alias.name for alias in node.names if alias.name != "*")
            found.append(Contract("python", node.module, names, (), "%s:%d" % (path, node.lineno)))
    return found


def _js_clause(clause):
    names, default = [], None
    named = re.search(r"\{([^}]*)\}", clause)
    if named:
        for part in named.group(1).split(","):
            part = part.strip()
            if part and not part.startswith("type "):
                names.append(part.split(" as ")[0].strip())
        clause = clause.replace(named.group(0), "")
    clause = clause.strip().rstrip(",").strip()
    if clause and not clause.startswith("*"):
        default = clause.split(",")[0].strip()
    return names, default


def _js_contracts(path, text):
    found = []
    for match in JS_IMPORT.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        spec = match.group("spec") or match.group("bare")
        names, default = _js_clause(match.group("clause") or "")
        members = ()
        if default:
            chains = re.findall(r"\b%s((?:\.[A-Za-z_$][\w$]*)+)" % re.escape(default), text)
            members = tuple(sorted({chain.lstrip(".") for chain in chains}))
            names = ["default"] + names
        found.append(Contract("javascript", spec, tuple(names), members, "%s:%d" % (path, line)))
    for match in JS_DYNAMIC_IMPORT.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        found.append(Contract("javascript", match.group("spec"), (), (), "%s:%d" % (path, line)))
    return found


def contracts_from_files(files):
    """Contrats d'API des fichiers generes, dans l'ordre des chemins."""
    found = []
    for path in sorted(files):
        if path.endswith(".py"):
            found += _python_contracts(path, files[path])
        elif path.endswith(JS_SUFFIXES):
            found += _js_contracts(path, files[path])
    return found


def catalog_contracts(plan):
    """Module importable annonce par le catalogue pour chaque bibliotheque Python retenue."""
    return [Contract("python", tech.module, (), (), "catalogue:%s" % tech.id)
            for tech in plan.resolution.technologies if tech.ecosystem == "pypi" and getattr(tech, "module", None)]


# --- Classement statique ------------------------------------------------------------------

def npm_package_name(spec):
    parts = spec.split("/")
    return "/".join(parts[:2]) if spec.startswith("@") else parts[0]


def _declared(files):
    npm, pypi = set(), set()
    if "package.json" in files:
        manifest = json.loads(files["package.json"])
        npm = set(manifest.get("dependencies", {})) | set(manifest.get("devDependencies", {}))
    if "pyproject.toml" in files:
        pypi = {re.split(r"[<>=!~\[ ;]", item.strip().strip('",'), maxsplit=1)[0].lower()
                for item in re.findall(r'^\s*"([^"]+)",?\s*$', files["pyproject.toml"], re.M)}
    return npm, pypi


def _local_target(contract, files):
    base = posixpath.dirname(contract.source.split(":")[0])
    target = posixpath.normpath(posixpath.join(base, contract.module))
    candidates = [target]
    if target.startswith("dist/"):  # sortie de build : verifier la source TypeScript ou JavaScript
        stem = "src/" + target[len("dist/"):].rsplit(".", 1)[0]
        candidates += [stem + ".ts", stem + ".tsx", stem + ".js"]
    return next((c for c in candidates if c in files), None)


def static_check(contract, plan, files, declared=None):
    """Check si le contrat est etabli hors ligne, sinon None (verification en ligne requise)."""
    npm, pypi = declared or _declared(files)
    subject = contract.subject
    if contract.language == "python":
        root = contract.module.split(".")[0]
        if root in sys.stdlib_module_names:
            return Check("api", subject, Status.PASS, "Bibliotheque standard Python", contract.source)
        if root == plan.spec.package_name:
            return Check("api", subject, Status.PASS, "Paquet du projet (src/%s)" % root, contract.source)
        if not contract.source.startswith("catalogue:") and not _python_distribution(plan, root, pypi):
            return Check("api", subject, Status.FAIL, "Module %s importe mais non declare dans pyproject.toml" % root,
                         contract.source)
        return None
    spec = contract.module
    if spec.startswith("node:") or spec in NODE_BUILTINS:
        name = spec[5:] if spec.startswith("node:") else spec
        status = Status.PASS if name in NODE_BUILTINS else Status.FAIL
        return Check("api", subject, status, "Module integre Node.js" if status is Status.PASS
                     else "Module integre Node.js inconnu : %s" % name, contract.source)
    if spec.startswith("."):
        target = _local_target(contract, files)
        if target is None:
            return Check("api", subject, Status.FAIL, "Fichier local introuvable : %s" % spec, contract.source)
        return Check("api", subject, Status.PASS, "Fichier du projet : %s" % target, contract.source)
    if npm_package_name(spec) not in npm:
        return Check("api", subject, Status.FAIL, "Paquet %s importe mais non declare dans package.json"
                     % npm_package_name(spec), contract.source)
    return None


def _python_distribution(plan, module, declared):
    for tech in plan.resolution.technologies:
        if tech.ecosystem == "pypi" and getattr(tech, "module", None) == module and tech.package.lower() in declared:
            return tech.package
    return None


def _unique(checks):
    """Un contrat identique (meme sujet, meme statut, meme preuve) n'est rapporte qu'une fois."""
    seen, result = set(), []
    for check in checks:
        key = (check.subject, check.status, check.message)
        if key not in seen:
            seen.add(key)
            result.append(check)
    return result


def static_checks(plan, files):
    """Classement hors ligne de tous les contrats ; NON VERIFIE quand la preuve exige le reseau."""
    declared = _declared(files)
    results = []
    for contract in contracts_from_files(files) + catalog_contracts(plan):
        check = static_check(contract, plan, files, declared)
        results.append(check or Check("api", contract.subject, Status.NON_VERIFIE,
                                      "Verification en ligne requise (archive officielle du paquet)", contract.source))
    return _unique(results)


# --- Verification en ligne : npm ----------------------------------------------------------

def _integrity(data, expected):
    algorithm, _, digest = (expected or "").partition("-")
    if algorithm != "sha512" or not digest:
        return False
    return base64.b64encode(hashlib.sha512(data).digest()).decode("ascii") == digest


def _npm_archive(package, version, fetch, fetch_bytes):
    response = fetch(npm_url(package))
    if response.status == 404 or not isinstance(response.data, dict):
        raise LookupError("paquet introuvable sur npm")
    version = version or response.data.get("dist-tags", {}).get("latest")
    meta = response.data.get("versions", {}).get(version)
    if not meta:
        raise LookupError("version %s absente" % version)
    dist = meta.get("dist", {})
    blob = fetch_bytes(dist.get("tarball", ""))
    if not _integrity(blob, dist.get("integrity")):
        raise ValueError("integrite SHA-512 de l'archive non confirmee")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
        for count, member in enumerate(archive):
            if count > MAX_ARCHIVE_FILES:
                raise ValueError("archive trop volumineuse")
            if member.isfile() and member.name.endswith((".json", ".d.ts", ".d.mts", ".d.cts", ".js", ".mjs", ".cjs")):
                name = member.name.split("/", 1)[1] if "/" in member.name else member.name
                files[name] = archive.extractfile(member).read().decode("utf-8", "replace")
    return version, files


def _exports_target(manifest, subpath, condition_order=("types", "import", "default", "require")):
    exports = manifest.get("exports")
    key = "." if not subpath else "./" + subpath
    if exports is None:
        return None, False
    if isinstance(exports, (str, list)) or (isinstance(exports, dict) and not any(k.startswith(".") for k in exports)):
        exports = {".": exports}
    entry = exports.get(key)
    if entry is None:
        for pattern, value in exports.items():
            if pattern.endswith("/*") and key.startswith(pattern[:-1]):
                entry = json.loads(json.dumps(value).replace("*", key[len(pattern) - 1:]))
                break
    if entry is None:
        return None, True
    def pick(value, wanted):
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return next((pick(v, wanted) for v in value if pick(v, wanted)), None)
        if isinstance(value, dict):
            for condition in (wanted,) + condition_order:
                if condition in value and pick(value[condition], wanted):
                    return pick(value[condition], wanted)
        return None
    return {"types": pick(entry, "types"), "code": pick(entry, "import") or pick(entry, "default")}, False


def _declaration_for(manifest, files, subpath):
    target, missing = _exports_target(manifest, subpath)
    if missing:
        return None, "sous-chemin non exporte"
    types = target and target["types"]
    if not types and not subpath:
        types = manifest.get("types") or manifest.get("typings")
    if not types:
        code = (target and target["code"]) or (None if subpath else manifest.get("main", "index.js"))
        if code:
            for suffix in (".d.ts", ".d.mts", ".d.cts"):
                candidate = re.sub(r"\.(m|c)?js$", "", code.lstrip("./")) + suffix
                if candidate in files:
                    return candidate, None
        return None, None
    return types.lstrip("./"), None


EXPORT_DECL = r"export\s+(?:declare\s+)?(?:async\s+)?(?:function|const|let|var|class|interface|type|enum|namespace)\s+%s\b"


def _find_export(files, start, name, depth=0):
    """True si `name` est exporte depuis le fichier de declarations, False si absence prouvee, None si inconnu."""
    text = files.get(start)
    if text is None or depth > MAX_FOLLOW:
        return None
    if name == "default":
        if re.search(r"export\s+default\b|export\s*=\s*\w|export\s*\{[^}]*\bas\s+default\b", text):
            return True
    elif re.search(EXPORT_DECL % re.escape(name), text) or re.search(r"export\s*\{[^}]*\b%s\b[^}]*\}" % re.escape(name), text):
        return True
    unknown = False
    for target in re.findall(r"""export\s*\*\s*from\s*["']([^"']+)["']""", text):
        if not target.startswith("."):
            unknown = True
            continue
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(start), target))
        candidates = [resolved] + [re.sub(r"\.(m|c)?js$", "", resolved) + s for s in (".d.ts", ".d.mts", ".d.cts")] \
            + [resolved + "/index.d.ts"]
        found = None
        for candidate in candidates:
            if candidate in files:
                found = _find_export(files, candidate, name, depth + 1)
                break
        if found:
            return True
        if found is None:
            unknown = True
    return None if unknown else False


def _verify_npm(contract, version, fetch, fetch_bytes, cache):
    package = npm_package_name(contract.module)
    subpath = contract.module[len(package):].lstrip("/")
    key = (package, version)
    if key not in cache:
        try:
            cache[key] = _npm_archive(package, version, fetch, fetch_bytes)
        except (FetchError, LookupError, ValueError, tarfile.TarError, OSError) as exc:
            cache[key] = exc
    archive = cache[key]
    evidence = npm_url(package)
    if isinstance(archive, LookupError):
        return Check("api", contract.subject, Status.FAIL, "%s : %s" % (package, archive), evidence)
    if isinstance(archive, Exception):
        return Check("api", contract.subject, Status.NON_VERIFIE, "Archive %s indisponible : %s" % (package, archive), evidence)
    resolved, files = archive
    manifest = json.loads(files.get("package.json", "{}"))
    declaration, problem = _declaration_for(manifest, files, subpath)
    label = "%s@%s" % (contract.module, resolved)
    if problem:
        return Check("api", contract.subject, Status.FAIL, "%s : %s" % (label, problem), evidence)
    if declaration is None:
        return Check("api", contract.subject, Status.NON_VERIFIE,
                     "%s : aucune declaration de types publiee, API non verifiable statiquement" % label, evidence)
    missing, unknown = [], []
    for name in contract.names:
        verdict = _find_export(files, declaration, name)
        (unknown if verdict is None else missing if verdict is False else []).append(name)
    for chain in contract.members:
        if not all(re.search(r"\b%s\s*[?]?\s*:" % re.escape(part), "\n".join(
                t for p, t in files.items() if p.endswith((".d.ts", ".d.mts", ".d.cts")))) for part in chain.split(".")):
            unknown.append(chain)
    where = "%s (%s)" % (label, declaration)
    if missing:
        return Check("api", contract.subject, Status.FAIL, "%s : export absent : %s" % (where, ", ".join(missing)), evidence)
    if unknown:
        return Check("api", contract.subject, Status.NON_VERIFIE, "%s : non etabli statiquement : %s"
                     % (where, ", ".join(unknown)), evidence)
    found = ", ".join(contract.names) or "module exporte"
    if contract.members:  # preuve plus faible : proprietes presentes dans les declarations du paquet
        found += " ; proprietes %s presentes dans les declarations du paquet" % ", ".join(contract.members)
    return Check("api", contract.subject, Status.PASS, "%s : %s" % (where, found), evidence)


# --- Verification en ligne : PyPI ---------------------------------------------------------

def _verify_python(contract, plan, versions, fetch, fetch_bytes, cache):
    root = contract.module.split(".")[0]
    package = next((t.package for t in plan.resolution.technologies if t.ecosystem == "pypi"
                    and getattr(t, "module", None) == root), None)
    if package is None:
        return Check("api", contract.subject, Status.NON_VERIFIE, "Distribution PyPI inconnue pour %s" % root, contract.source)
    evidence = pypi_url(package)
    if package not in cache:
        try:
            cache[package] = _wheel_names(package, versions.get(package), fetch, fetch_bytes)
        except (FetchError, LookupError, ValueError, zipfile.BadZipFile, OSError) as exc:
            cache[package] = exc
    names = cache[package]
    if isinstance(names, LookupError):
        return Check("api", contract.subject, Status.FAIL, "%s : %s" % (package, names), evidence)
    if isinstance(names, Exception):
        return Check("api", contract.subject, Status.NON_VERIFIE, "Roue %s indisponible : %s" % (package, names), evidence)
    version, wheel, entries = names
    path = contract.module.replace(".", "/")
    if not any(e in entries for e in (path + "/__init__.py", path + ".py")) and not any(
            e.startswith(path + "/") for e in entries):
        return Check("api", contract.subject, Status.FAIL, "Module %s absent de %s" % (contract.module, wheel), evidence)
    return Check("api", contract.subject, Status.PASS, "Module %s present dans %s (%s %s)"
                 % (contract.module, wheel, package, version), evidence)


def _wheel_names(package, version, fetch, fetch_bytes):
    response = fetch(pypi_url(package))
    if response.status == 404 or not isinstance(response.data, dict):
        raise LookupError("paquet introuvable sur PyPI")
    version = version or response.data.get("info", {}).get("version")
    files = response.data.get("releases", {}).get(version)
    if not files:
        raise LookupError("version %s absente" % version)
    wheels = [f for f in files if f.get("packagetype") == "bdist_wheel" and not f.get("yanked")]
    if not wheels:
        raise ValueError("aucune roue publiee (sdist seule)")
    wheel = next((w for w in wheels if w.get("filename", "").endswith("-none-any.whl")), wheels[0])
    blob = fetch_bytes(wheel.get("url", ""))
    if hashlib.sha256(blob).hexdigest() != (wheel.get("digests") or {}).get("sha256"):
        raise ValueError("empreinte SHA-256 de la roue non confirmee")
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        return version, wheel["filename"], set(archive.namelist())


def verify_contracts(plan, files, fetch, fetch_bytes, npm_versions=None, pypi_versions=None):
    """Statique d'abord, puis preuve en ligne pour chaque contrat tiers restant."""
    declared = _declared(files)
    cache, results = {}, []
    for contract in contracts_from_files(files) + catalog_contracts(plan):
        check = static_check(contract, plan, files, declared)
        if check is None:
            if contract.language == "javascript":
                package = npm_package_name(contract.module)
                check = _verify_npm(contract, (npm_versions or {}).get(package), fetch, fetch_bytes, cache)
            else:
                check = _verify_python(contract, plan, pypi_versions or {}, fetch, fetch_bytes, cache)
        results.append(check)
    return _unique(results)
