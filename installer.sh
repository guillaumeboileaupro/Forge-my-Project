#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
# shellcheck source=scripts/linux-python.sh
. "$SCRIPT_DIR/scripts/linux-python.sh"

forge_require_linux

for required_file in start.py start.sh server.py; do
    if [ ! -f "$SCRIPT_DIR/$required_file" ]; then
        echo "Erreur : fichier requis absent : $SCRIPT_DIR/$required_file" >&2
        exit 1
    fi
done

PYTHON=$(forge_find_python)
VERSION=$(forge_python_version "$PYTHON")

echo "Forge-my-Project est pret."
echo "Python retenu : $PYTHON ($VERSION)"
echo "Demarrage : $SCRIPT_DIR/start.sh"
echo "Aucun paquet, acces reseau ou privilege administrateur n'est requis."
