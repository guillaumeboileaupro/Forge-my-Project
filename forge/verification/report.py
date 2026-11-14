"""Verification d'un plan : packages, versions, vulnerabilites, runtimes, API (T11).

Appel explicite uniquement : c'est la seule etape du moteur qui interroge
les registres. Erreur critique (package inexistant, version absente,
vulnerabilite haute/critique, runtime en fin de vie) = blocage.
"""
import datetime
from dataclasses import dataclass

from forge import diagnostics as d
from forge.diagnostics import Status
from forge.verification import checks
from forge.verification.http import fetch_json


@dataclass(frozen=True)
class VerificationReport:
    checks: tuple
    diagnostics: tuple

    @property
    def ok(self):
        return not d.has_errors(self.diagnostics)

    def find(self, kind, subject_prefix):
        return [c for c in self.checks if c.kind == kind and c.subject.startswith(subject_prefix)]

    def package_status(self, ecosystem, package):
        """Etat agrege d'une dependance (registre + vulnerabilites) et details."""
        prefix = "%s:%s" % (ecosystem, package)
        found = [c for c in self.checks if c.kind in ("package", "vulnerabilities")
                 and (c.subject == prefix or c.subject.startswith(prefix + "@"))]
        if not found:
            return Status.NON_VERIFIE, {}
        details = next((c.details for c in found if c.kind == "package"), {})
        if any(c.status is Status.FAIL for c in found):
            return Status.FAIL, details
        if len(found) < 2 or any(c.status is Status.NON_VERIFIE for c in found):
            return Status.NON_VERIFIE, details
        return Status.PASS, details

    def as_dict(self):
        return {"ok": self.ok, "checks": [c.as_dict() for c in self.checks],
                "diagnostics": [x.as_dict() for x in self.diagnostics]}


def _diagnostic(check):
    if check.status is Status.FAIL:
        return d.error("verification-" + check.kind, "%s : %s" % (check.subject, check.message), check.subject)
    if check.status is Status.NON_VERIFIE and check.kind != "api":
        return d.warning("unverified-" + check.kind, "%s : %s" % (check.subject, check.message), check.subject)
    return None


def _verify_package(tech, wanted, fetch):
    result = [checks.check_package(tech.ecosystem, tech.package, wanted, fetch)]
    version = result[0].details.get("version")
    if result[0].status is Status.PASS and version:
        result.append(checks.check_vulnerabilities(tech.ecosystem, tech.package, version, fetch))
    else:
        result.append(checks.Check("vulnerabilities", "%s:%s" % (tech.ecosystem, tech.package), Status.NON_VERIFIE,
                                   "Audit impossible sans version verifiee"))
    return result


def verify_plan(plan, fetch=fetch_json, today=None):
    """Verifie chaque technologie du plan. `today` (AAAA-MM-JJ) est injectable pour les tests."""
    today = today or datetime.date.today().isoformat()
    results = []
    for tech in plan.resolution.technologies:
        if tech.package:
            results.extend(_verify_package(tech, plan.spec.versions.get(tech.id), fetch))
            results.append(checks.api_unverified(tech))
        if tech.eol_product and tech.id in plan.resolution.versions:
            results.append(checks.check_runtime(tech.eol_product, plan.resolution.versions[tech.id], today, fetch))
    diagnostics = tuple(x for x in map(_diagnostic, results) if x is not None)
    return VerificationReport(tuple(results), diagnostics)
