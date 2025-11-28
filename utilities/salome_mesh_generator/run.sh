#!/usr/bin/env bash
# Wrapper para lanzar el generador de malla.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Si no hay argumentos, entra en modo interactivo
if [ $# -eq 0 ]; then
  exec python3 -m meshgen.cli --interactive
else
  exec python3 -m meshgen.cli "$@"
fi
