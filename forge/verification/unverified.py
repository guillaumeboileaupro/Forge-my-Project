"""Controles NON VERIFIE et avertissements : inventaire, criticite, confirmation (E06).

Un controle impossible a etablir reste NON VERIFIE : la confirmation de l'utilisateur
l'accepte en connaissance de cause sans jamais le transformer en PASS.

- `assess(result)` liste chaque element a confirmer (nom, raison exacte, risque) et
  marque `critical` ceux qu'aucune confirmation ne peut lever.
- Le jeton de confirmation (HMAC propre au processus) lie la configuration et
  l'ensemble exact des controles concernes ; `check_confirmation` le recalcule sur un
  resultat regenere : configuration ou controles changes = confirmation perimee.

Regles de criticite :
- niveau `hardened` : les controles de securite (vulnerabilites, outils de securite,
  actions epinglees, serveurs MCP) doivent reussir ; NON VERIFIE = blocage ;
- niveau `hardened` sans verification en ligne : blocage (ces controles n'ont pas eu lieu).
"""
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass

from forge import diagnostics as d
from forge.diagnostics import Status

_KEY = secrets.token_bytes(32)  # un redemarrage du serveur perime toutes les confirmations
UNVERIFIED = Status.NON_VERIFIE.value
WARNING = "AVERTISSEMENT"
SECURITY_KINDS = ("vulnerabilities", "tool", "action", "mcp")
UNVERIFIED_CODES = {"mcp-unverified", "skill-unverified", "skills-not-fetched",
                    "security-sast-unverified", "security-image-unverified"}
RISKS = {
    "package": "Existence, version ou licence du package non confirmees : installation en echec ou package usurpe possibles.",
    "vulnerabilities": "Vulnerabilites connues non recherchees : une dependance vulnerable peut etre installee.",
    "runtime": "Fin de support non confirmee : le runtime peut ne plus recevoir de correctifs.",
    "compatibility": "Compatibilite entre packages non confirmee : installation ou execution en echec possibles.",
    "tool": "Integrite d'un outil de securite de la CI non confirmee (version ou empreinte).",
    "action": "Epinglage d'une action GitHub non confirme : la CI pourrait executer un code inattendu.",
    "mcp": "Serveur MCP non confirme sur le registre officiel : provenance et transport non garantis.",
    "api": "API non verifiee automatiquement : consulter la documentation officielle avant usage.",
    "mcp-unverified": "Serveurs MCP non verifies : provenance et transport non garantis.",
    "skill-unverified": "Skill non recupere ou non verifie : contenu absent ou non controle.",
    "skills-not-fetched": "Skills externes approuves absents du projet genere.",
    "security-sast-unverified": "Aucune analyse statique de securite pour JavaScript/TypeScript.",
    "security-image-unverified": "Image conteneur non analysee : vulnerabilites de l'image non detectees.",
    "verification-not-run": "Aucun controle en ligne : packages, vulnerabilites, outils et actions non verifies.",
}
DEFAULT_RISK = "Element optionnel absent ou incomplet : relire le projet genere avant usage."


class ConfirmationError(ValueError):
    """Confirmation absente, perimee, ou controle critique NON VERIFIE."""

    def __init__(self, message, assessment, stale=False):
        super().__init__(message)
        self.assessment = assessment
        self.stale = stale


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    status: str  # NON VERIFIE | AVERTISSEMENT
    reason: str
    risk: str
    critical: bool

    def as_dict(self):
        return {"id": self.id, "name": self.name, "status": self.status, "reason": self.reason,
                "risk": self.risk, "critical": self.critical}


def _from_check(check, hardened):
    critical = hardened and check.kind in SECURITY_KINDS
    return Item("%s:%s" % (check.kind, check.subject), "Controle %s : %s" % (check.kind, check.subject),
                 UNVERIFIED, check.message, RISKS.get(check.kind, DEFAULT_RISK), critical)


def _from_diagnostic(diag, hardened):
    unverified = diag.code in UNVERIFIED_CODES
    critical = hardened and diag.code == "mcp-unverified"
    name = diag.subject or diag.code
    return Item("%s:%s" % (diag.code, diag.subject), "%s (%s)" % (name, diag.code),
                 UNVERIFIED if unverified else WARNING, diag.message,
                 RISKS.get(diag.code, DEFAULT_RISK), critical)


def items(result):
    """Elements a confirmer, tries et sans doublon ; les controles NON VERIFIE d'abord."""
    hardened = result.plan.spec.security == "hardened"
    found = {}
    if result.verification is not None:
        for check in result.verification.checks:
            if check.status is Status.NON_VERIFIE:
                item = _from_check(check, hardened)
                found[item.id] = item
    elif hardened:
        found["verification-not-run:"] = Item(
            "verification-not-run:", "Verification en ligne (niveau hardened)", UNVERIFIED,
            "Le niveau hardened impose la verification en ligne, qui n'a pas ete executee.",
            RISKS["verification-not-run"], True)
    for diag in result.diagnostics:
        if diag.severity is d.Severity.WARNING and not diag.code.startswith("unverified-"):
            item = _from_diagnostic(diag, hardened)
            found.setdefault(item.id, item)
    return sorted(found.values(), key=lambda i: (i.status != UNVERIFIED, not i.critical, i.id))


def _token(config, flags, found):
    material = json.dumps({"config": config, "flags": flags,
                           "items": [[i.id, i.status, i.critical] for i in found]},
                          sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hmac.new(_KEY, material, hashlib.sha256).hexdigest()


def assess(result, config, flags):
    """Inventaire expose a l'interface : elements, criticite et jeton de confirmation."""
    found = items(result)
    critical = [i.id for i in found if i.critical]
    return {
        "items": [i.as_dict() for i in found],
        "counts": {"non_verifie": sum(i.status == UNVERIFIED for i in found),
                   "avertissements": sum(i.status == WARNING for i in found), "critiques": len(critical)},
        "blocking": critical,
        "token": _token(config, flags, found) if found and not critical else None,
    }


def ensure_not_blocking(assessment):
    """Refuse toute operation tant qu'un controle critique reste NON VERIFIE."""
    if assessment["blocking"]:
        raise ConfirmationError("Operation bloquee : controle(s) critique(s) NON VERIFIE (%s). Aucune confirmation "
                                "ne peut les lever ; executer la verification en ligne ou changer de niveau de securite."
                                % ", ".join(assessment["blocking"]), assessment)


def check_confirmation(assessment, confirmation):
    """Confirmation explicite, et correspondant toujours aux controles regeneres."""
    ensure_not_blocking(assessment)
    if not assessment["items"]:
        return
    if confirmation is None:
        raise ConfirmationError("Confirmation explicite requise : %d controle(s) NON VERIFIE ou avertissement(s) "
                                "a accepter avant l'ecriture." % len(assessment["items"]), assessment, stale=True)
    if not isinstance(confirmation, str) or not hmac.compare_digest(confirmation, assessment["token"]):
        raise ConfirmationError("Confirmation perimee : la configuration ou les controles NON VERIFIE ont change "
                                "depuis la confirmation. Relire la liste et confirmer a nouveau.", assessment, stale=True)


def journal_entries(assessment, confirmed):
    """Trace : chaque element garde son statut et sa raison ; la confirmation est notee a part."""
    return [dict(item, confirmed=confirmed) for item in assessment["items"]]
