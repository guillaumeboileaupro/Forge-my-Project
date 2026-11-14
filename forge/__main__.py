"""Interface en ligne de commande du moteur : apercu sans ecriture disque.

    python -m forge plan spec.json                    diagnostics et fichiers prevus (JSON)
    python -m forge plan spec.json --verify --skills  + verification en ligne et skills my-skills
    python -m forge show spec.json AGENTS.md          contenu d'un fichier rendu
    python -m forge skills-search spec.json           candidats de skills externes (reseau, aucune copie)

Sans --verify, --skills ni skills-search, aucune requete reseau n'est emise.
"""
import argparse
import json
import sys

from forge.diagnostics import ForgeError
from forge.pipeline import run
from forge.planner.plan import build_plan
from forge.skills.service import search_for_plan


def _load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _parser():
    parser = argparse.ArgumentParser(prog="python -m forge", description="Apercu du moteur Forge-my-Project (aucune ecriture).")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("plan", "diagnostics et fichiers prevus"), ("show", "afficher un fichier rendu")):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("spec")
        if name == "show":
            command.add_argument("path")
        command.add_argument("--verify", action="store_true", help="verifier packages, versions, vulnerabilites (reseau)")
        command.add_argument("--skills", action="store_true", help="recuperer les skills de my-skills (reseau)")
    search = sub.add_parser("skills-search", help="rechercher des skills externes (candidats a approuver)")
    search.add_argument("spec")
    return parser


def _search(path):
    plan = build_plan(_load(path))
    found = search_for_plan(plan)
    print(json.dumps({"candidates": [c.as_dict() for c in found.candidates], "notes": found.notes},
                     ensure_ascii=False, indent=2))
    return 0


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.command == "skills-search":
        try:
            return _search(args.spec)
        except (OSError, ValueError) as exc:
            print("Erreur : %s" % exc, file=sys.stderr)
            return 2
    try:
        result = run(_load(args.spec), verify=args.verify, skills=args.skills)
    except ForgeError as exc:
        report = {"ok": False, "error": str(exc), "diagnostics": [x.as_dict() for x in exc.diagnostics]}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2
    except (OSError, ValueError) as exc:
        print("Erreur : %s" % exc, file=sys.stderr)
        return 2
    if args.command == "show":
        if args.path not in result.files:
            print("Fichier non prevu : " + args.path, file=sys.stderr)
            return 1
        sys.stdout.write(result.files[args.path])
        return 0
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
