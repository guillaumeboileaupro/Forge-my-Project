"""Interface en ligne de commande du moteur : apercu sans ecriture.

    python -m forge plan spec.json          diagnostics et liste des fichiers (JSON)
    python -m forge show spec.json AGENTS.md contenu d'un fichier rendu
"""
import argparse
import json
import sys

from forge.diagnostics import ForgeError
from forge.generator.render import generate


def _load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m forge", description="Apercu du moteur Forge-my-Project (aucune ecriture).")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="diagnostics et fichiers prevus")
    plan.add_argument("spec")
    show = sub.add_parser("show", help="afficher un fichier rendu")
    show.add_argument("spec")
    show.add_argument("path")
    args = parser.parse_args(argv)
    try:
        plan_result, files = generate(_load(args.spec))
    except ForgeError as exc:
        report = {"ok": False, "error": str(exc), "diagnostics": [x.as_dict() for x in exc.diagnostics]}
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
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
