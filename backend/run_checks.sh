#!/bin/bash
set -e

if [ ! -f "manage.py" ]; then
    echo "Error: run from backend/ directory"
    exit 1
fi

echo "Running tests..."
python manage.py test --settings=config.settings_test

echo "Checking formatting..."
pip install -q black isort flake8 mypy django-stubs djangorestframework-stubs types-requests 2>/dev/null || true

black --check . --exclude="migrations|venv|env|.venv"
isort --check-only . --skip migrations --skip venv --skip env --skip .venv
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

echo "Type checking..."
export PYTHONPATH=$PWD
mypy .

echo "Done."
