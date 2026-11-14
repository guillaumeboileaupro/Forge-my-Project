"""Validation du contrat historique expose par ``generator.py``."""
import re

OPTIONS = {
    "language": {"python", "typescript"},
    "agent": {"codex", "claude", "copilot", "agnostic"},
    "deployment": {"none", "docker", "s3ns", "outscale"},
    "security": {"strict", "hardened"},
}
FIELDS = {"name", "description", "one_pr", *OPTIONS}
NAME = re.compile(r"^[a-z][a-z0-9-]{1,48}[a-z0-9]$")


def validate(data):
    """Valide et normalise la configuration historique du formulaire."""
    if not isinstance(data, dict):
        raise ValueError("Configuration JSON attendue")
    unknown = set(data) - FIELDS
    if unknown:
        raise ValueError("Champ inconnu : " + sorted(unknown)[0])
    name = data.get("name")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError("Nom de projet invalide (3-50 caracteres, minuscules, chiffres, tirets)")
    config = {"name": name}
    for key, allowed in OPTIONS.items():
        value = data.get(key)
        if not isinstance(value, str) or value not in allowed:
            raise ValueError("Option invalide : " + key)
        config[key] = value
    description = data.get("description", "")
    if not isinstance(description, str) or len(description) > 500:
        raise ValueError("Description invalide")
    config["description"] = " ".join(description.split())
    one_pr = data.get("one_pr", True)
    if not isinstance(one_pr, bool):
        raise ValueError("Option invalide : one_pr")
    config["one_pr"] = one_pr
    return config
