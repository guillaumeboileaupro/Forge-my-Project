"""Moteur technique de Forge-my-Project (bibliotheque standard uniquement).

Le moteur ne genere aucun code metier, n'integre aucun modele d'IA et n'accede
au reseau que sur appel explicite des modules de verification ou de skills.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOGS_DIR = ROOT / "catalogs"
TEMPLATES_DIR = ROOT / "templates"
