"""Interface en ligne de commande du moteur : apercu sans ecriture.

    python -m forge plan spec.json             diagnostics et liste des fichiers (JSON)
    python -m forge plan spec.json --verify    idem + verification en ligne (registres, OSV, endoflife.date)
    python -m forge show spec.json AGENTS.md   contenu d'un fichier rendu

Sans --verify, aucune requete reseau n'est emise.
"""
import argparse
import json
import sys

from forge.diagnostics import ForgeError
from forge.generator.render import generate
from forge.verification.report import verify_plan


def _load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m forge", description="Apercu du moteur Forge-my-Project (aucune ecriture).")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="diagnostics et fichiers prevus")
    plan.add_argument("spec")
    plan.add_argument("--verify", action="store_true", help="verifier packages, versions et vulnerabilites (reseau)")
    show = sub.add_parser("show", help="afficher un fichier rendu")
    show.add_argument("spec")
    show.add_argument("path")
    args = parser.parse_args(argv)
    try:
        reports = []

        def verification(plan_to_check):
            reports.append(verify_plan(plan_to_check))
            return reports[-1]

        use_network = getattr(args, "verify", False)
        plan_result, files = generate(_load(args.spec), verification=verification if use_network else None)
    except ForgeError as exc:
        report = {"ok": False, "error": str(exc), "diagnostics": [x.as_dict() for x in exc.diagnostics]}
        if reports:
            report["verification"] = reports[-1].as_dict()["checks"]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2
    except (OSError, ValueError) as exc:
        print("Erreur : %s" % exc, file=sys.stderr)
        return 2
    if args.command == "show":
        if args.path not in files:
            print("Fichier non prevu : " + args.path, file=sys.stderr)
            return 1
        sys.stdout.write(files[args.path])
        return 0
    report = {
        "ok": True,
        "rules": plan_result.composition.rules,
        "files": sorted(files),
        "diagnostics": [x.as_dict() for x in plan_result.diagnostics],
    }
    if reports:
        report["verification"] = reports[-1].as_dict()["checks"]
        report["diagnostics"] += [x.as_dict() for x in reports[-1].diagnostics]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
