#!/bin/bash
set -e

echo "Running bot tests..."
export PYTHONPATH=$PWD
pytest -W ignore::DeprecationWarning tests/

echo "Checking formatting..."
pip install -q black isort flake8 2>/dev/null || true

black --check . --exclude="venv|env|.venv"
isort --profile black --check-only . --skip venv --skip env --skip .venv
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics


