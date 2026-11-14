"""Facade compatible du generateur historique.

Les imports existants restent valides pendant que l'implementation evolue dans
le package ``forge``. Aucun appelant ne doit dependre des modules ``legacy``.
"""
from forge.config.legacy import FIELDS, NAME, OPTIONS, validate
from forge.generator.legacy import build, generate, skill

__all__ = [
    "FIELDS",
    "NAME",
    "OPTIONS",
    "build",
    "generate",
    "skill",
    "validate",
]
