#!/usr/bin/env bash
# Launcher for this specific utility.
# Always runs relative to this file, so it works from any directory.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Launch this utility's main CLI
exec python3 -m app.cli.main_cli "$@"
