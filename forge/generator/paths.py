"""Validation des chemins relatifs produits ou lus par le moteur."""
import re
from pathlib import Path, PurePosixPath

SEGMENT = re.compile(r"^[A-Za-z0-9_.@-][A-Za-z0-9_.@ -]{0,99}$")
MAX_DEPTH = 12


class PathError(ValueError):
    pass


def safe_relative_path(path):
    """Accepte uniquement un chemin POSIX relatif sans remontee ni segment special."""
    if not isinstance(path, str) or not path or "\\" in path or "\x00" in path:
        raise PathError("Chemin invalide : %r" % (path,))
    pure = PurePosixPath(path)
    parts = pure.parts
    if pure.is_absolute() or not parts or len(parts) > MAX_DEPTH or str(pure) != path:
        raise PathError("Chemin invalide : %r" % (path,))
    for part in parts:
        if part in (".", "..") or not SEGMENT.fullmatch(part) or part != part.strip():
            raise PathError("Segment de chemin invalide : %r" % (path,))
    return path


def resolve_inside(root, relative):
    """Resout un chemin relatif sous root et refuse toute sortie (liens compris)."""
    root = Path(root).resolve()
    target = (root / safe_relative_path(relative)).resolve()
    if target != root and root not in target.parents:
        raise PathError("Chemin hors de la racine : %r" % (relative,))
    return target
