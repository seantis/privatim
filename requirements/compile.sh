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
    "$@"

# uv no longer accepts editable requirements in constraint files.
tmp_constraints=$(mktemp)
trap 'rm -f "${tmp_constraints}"' EXIT
sed '/^-e \./d' requirements.txt > "${tmp_constraints}"

echo "Building tests_requirements.txt"
uv pip compile requirements/test.in \
    -c "${tmp_constraints}" \
    -o tests_requirements.txt \
    "$@"

sed -i "s|${tmp_constraints}|requirements.txt|g" tests_requirements.txt
