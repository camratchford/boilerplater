#!/bin/bash

THIS_FILE="$(realpath "$0")"
THIS_DIR="$(dirname "$THIS_FILE")"
PROJECT_ROOT="$THIS_DIR"/..

"$PROJECT_ROOT"/venv/bin/python3 -m build \
  --outdir "$PROJECT_ROOT"/dist \
  --wheel \
  "$PROJECT_ROOT"

"$PROJECT_ROOT"/venv/bin/python3 -m build \
  --outdir "$PROJECT_ROOT"/dist \
  --sdist \
  "$PROJECT_ROOT"

