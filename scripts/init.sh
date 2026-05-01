#!/bin/bash

THIS_FILE="$(realpath "$0")"
THIS_DIR="$(dirname "$THIS_FILE")"

cd "$THIS_DIR"/.. || exit 1

python3 -m venv venv

venv/bin/pip install --upgrade pip setuptools setuptools-scm wheel
venv/bin/pip install --upgrade -e .'[development]'

cd - | /dev/null
