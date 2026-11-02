#!/bin/sh
set -eu

cd "$(dirname "$0")"

if [ -x .venv/bin/python ]; then
    exec .venv/bin/python -B src/main.py "$@"
fi

exec python3 -B src/main.py "$@"
