#!/bin/sh
# The Python quality gate. The test service and CI run this same script.
set -eu

ruff check .
ruff format --check .
mypy
pytest --cov --cov-report=term --cov-report=xml --cov-fail-under=92
coverage report --include='api/domain/*' --fail-under=94
