#!/usr/bin/env bash
set -euo pipefail

# change to scripts directory
cd $(dirname "$0")
# change to base directory
cd ..

# make sure virtual env is active
if [ -z "${VIRTUAL_ENV:-}" ]; then
    source env/bin/activate
fi

echo "Building requirements.txt"
echo "-e privatim @ ." | uv pip compile setup.cfg - \
    -o requirements.txt \
    --no-emit-package setuptools \
    "$@"

echo "Building tests_requirements.txt"
uv pip compile setup.cfg \
    --extra test \
    --extra mypy \
    -o tests_requirements.txt \
    -c requirements.txt \
    "$@"
