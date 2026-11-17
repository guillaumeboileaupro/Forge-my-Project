#!/bin/sh

# Fonctions POSIX partagees par installer.sh et start.sh.

forge_require_linux() {
    if [ "$(uname -s 2>/dev/null || true)" != "Linux" ]; then
        echo "Erreur : Forge-my-Project est pris en charge uniquement sous Linux." >&2
        return 1
    fi
}

forge_python_version() {
    "$1" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null
}

forge_python_supported() {
    "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
        >/dev/null 2>&1
}

forge_find_python() {
    if [ -n "${FORGE_PYTHON:-}" ]; then
        if [ ! -x "$FORGE_PYTHON" ] || ! forge_python_supported "$FORGE_PYTHON"; then
            echo "Erreur : FORGE_PYTHON doit designer un Python 3.11+ executable : $FORGE_PYTHON" >&2
            return 1
        fi
        printf '%s\n' "$FORGE_PYTHON"
        return 0
    fi

    for forge_candidate in python3.14 python3.13 python3.12 python3.11 python3 python; do
        forge_path=$(command -v "$forge_candidate" 2>/dev/null || true)
        if [ -n "$forge_path" ] && forge_python_supported "$forge_path"; then
            printf '%s\n' "$forge_path"
            return 0
        fi
    done

    if [ -n "${HOME:-}" ]; then
        for forge_candidate in python3.14 python3.13 python3.12 python3.11 python3 python; do
            forge_path="$HOME/.local/bin/$forge_candidate"
            if [ -x "$forge_path" ] && forge_python_supported "$forge_path"; then
                printf '%s\n' "$forge_path"
                return 0
            fi
        done
    fi

    echo "Erreur : Python 3.11 ou plus recent est requis." >&2
    echo "Installez Python avec le gestionnaire de paquets de votre distribution, puis relancez installer.sh." >&2
    return 1
}
