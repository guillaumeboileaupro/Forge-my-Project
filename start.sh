#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
# shellcheck source=scripts/linux-python.sh
. "$SCRIPT_DIR/scripts/linux-python.sh"

forge_require_linux
PYTHON=$(forge_find_python)

exec "$PYTHON" "$SCRIPT_DIR/start.py" "$@"
