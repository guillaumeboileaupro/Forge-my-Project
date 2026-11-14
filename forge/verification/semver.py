"""Sous-ensemble des plages semver de npm : ||, conjonctions, ^, ~, x/*, comparateurs, X - Y.

Les versions candidates sont stables (sans pre-release). Une plage non
reconnue leve ValueError : l'appelant la traite comme NON VERIFIE.
"""
import re

STABLE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
PARTIAL = re.compile(r"^v?(\d+|[xX*])(?:\.(\d+|[xX*]))?(?:\.(\d+|[xX*]))?(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
COMPARATOR = re.compile(r"^(>=|<=|>|<|=|\^|~)?\s*(.+)$")


def parse_stable(version):
    match = STABLE.fullmatch(version or "")
    return tuple(int(x) for x in match.groups()) if match else None


def _partial(text):
    match = PARTIAL.fullmatch(text.strip())
    if not match:
        raise ValueError("Version de plage non reconnue : %r" % text)
    parts = []
    for part in match.groups():
        if part is None or part in ("x", "X", "*"):
            break
        parts.append(int(part))
    return parts


def _bump(parts, index):
    head = parts[:index] + [parts[index] + 1]
    return tuple(head + [0] * (3 - len(head)))


def _floor(parts):
    return tuple(parts + [0] * (3 - len(parts)))


def _comparator(token):
    """Retourne une liste de (operateur, version) equivalente a un comparateur."""
    op, text = COMPARATOR.fullmatch(token).groups()
    parts = _partial(text)
    if not parts:
        return []  # *, x : toute version
    if op in (None, "="):
        if len(parts) == 3:
            return [("==", tuple(parts))]
        return [(">=", _floor(parts)), ("<", _bump(parts, len(parts) - 1))]
    if op == "^":
        index = next((i for i, p in enumerate(parts) if p != 0), len(parts) - 1)
        return [(">=", _floor(parts)), ("<", _bump(parts, min(index, len(parts) - 1)))]
    if op == "~":
        return [(">=", _floor(parts)), ("<", _bump(parts, 1 if len(parts) > 1 else 0))]
    if op in (">", "<=") and len(parts) < 3:  # >1.2 signifie >=1.3.0 ; <=1.2 signifie <1.3.0
        return [(">=" if op == ">" else "<", _bump(parts, len(parts) - 1))]
    return [(op, _floor(parts))]


def _set(text):
    text = text.strip()
    hyphen = re.fullmatch(r"(\S+)\s+-\s+(\S+)", text)
    if hyphen:
        low, high = _partial(hyphen.group(1)), _partial(hyphen.group(2))
        upper = [("<=", tuple(high))] if len(high) == 3 else [("<", _bump(high, len(high) - 1))] if high else []
        return [(">=", _floor(low))] + upper
    tokens = re.findall(r"(?:>=|<=|>|<|=|\^|~)?\s*[^\s<>=^~]+", text)
    return [clause for token in tokens for clause in _comparator(token.strip())]


_OPS = {
    "==": lambda a, b: a == b, ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b, "<": lambda a, b: a < b,
}


def satisfies(version, range_text):
    value = parse_stable(version)
    if value is None:
        return False
    alternatives = [part for part in (range_text or "*").split("||")]
    return any(all(_OPS[op](value, bound) for op, bound in _set(alt or "*")) for alt in alternatives)


def stable_versions(metadata):
    """Versions stables non depreciees d'un document du registre npm, de la plus recente a la plus ancienne."""
    versions = metadata.get("versions") or {}
    usable = [v for v, meta in versions.items() if parse_stable(v) and not (meta or {}).get("deprecated")]
    return sorted(usable, key=parse_stable, reverse=True)
