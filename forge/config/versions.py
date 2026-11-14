"""Comparaison de versions numeriques et contraintes simples (>=, <=, >, <, ==, !=).

Volontairement limite aux versions numeriques "X.Y.Z" : les versions
pre-release ne sont pas acceptees dans le catalogue.
"""
import re

_VERSION = re.compile(r"^\d+(\.\d+){0,3}$")
_CLAUSE = re.compile(r"^(>=|<=|==|!=|>|<)\s*(\d+(?:\.\d+){0,3})$")


def parse(version):
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise ValueError("Version invalide : %r" % (version,))
    return tuple(int(part) for part in version.split("."))


def _compare(left, right):
    width = max(len(left), len(right))
    left = left + (0,) * (width - len(left))
    right = right + (0,) * (width - len(right))
    return (left > right) - (left < right)


def parse_constraint(constraint):
    """Retourne la liste des clauses (operateur, version) d'une contrainte "a,b"."""
    if not isinstance(constraint, str) or not constraint.strip():
        raise ValueError("Contrainte de version vide")
    clauses = []
    for raw in constraint.split(","):
        match = _CLAUSE.fullmatch(raw.strip())
        if not match:
            raise ValueError("Contrainte de version invalide : %r" % (constraint,))
        clauses.append((match.group(1), parse(match.group(2))))
    return clauses


_OPERATORS = {
    ">=": lambda c: c >= 0,
    "<=": lambda c: c <= 0,
    ">": lambda c: c > 0,
    "<": lambda c: c < 0,
    "==": lambda c: c == 0,
    "!=": lambda c: c != 0,
}


def satisfies(version, constraint):
    value = parse(version)
    return all(_OPERATORS[op](_compare(value, bound)) for op, bound in parse_constraint(constraint))
