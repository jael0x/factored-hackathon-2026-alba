#!/bin/sh
# The four oracle flows in a browser (IMPLEMENTATION.md W7), on a copy of the compose stack that starts empty and
# loads data/raw/ every run, so no earlier case changes what a flow sees.
set -eu

cd "$(dirname "$0")/.."

compose() {
  docker compose -p alba-e2e -f compose.yaml -f compose.e2e.yaml --profile e2e "$@"
}

compose down -v --remove-orphans
trap 'compose down -v --remove-orphans' EXIT
compose build
compose run --rm e2e
