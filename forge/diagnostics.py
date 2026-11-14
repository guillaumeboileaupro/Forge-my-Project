"""Etats et diagnostics partages par tous les modules du moteur."""
from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    """Resultat d'un controle. NON_VERIFIE n'est jamais equivalent a PASS."""

    PASS = "PASS"
    FAIL = "FAIL"
    NON_VERIFIE = "NON VERIFIE"


class Severity(str, Enum):
    ERROR = "error"  # bloque la generation
    WARNING = "warning"  # demande une confirmation
    INFO = "info"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    subject: str = ""

    def as_dict(self):
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "subject": self.subject,
        }


def error(code, message, subject=""):
    return Diagnostic(code, Severity.ERROR, message, subject)


def warning(code, message, subject=""):
    return Diagnostic(code, Severity.WARNING, message, subject)


def info(code, message, subject=""):
    return Diagnostic(code, Severity.INFO, message, subject)


def has_errors(diagnostics):
    return any(d.severity is Severity.ERROR for d in diagnostics)


class ForgeError(ValueError):
    """Erreur bloquante portant les diagnostics qui l'expliquent."""

    def __init__(self, message, diagnostics=()):
        super().__init__(message)
        self.diagnostics = tuple(diagnostics)
