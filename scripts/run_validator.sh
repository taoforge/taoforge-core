#!/bin/bash
set -e

export TAOFORGE_HOST=${TAOFORGE_HOST:-0.0.0.0}
export TAOFORGE_PORT=${TAOFORGE_PORT:-8092}
export TAOFORGE_KEY_FILE=${TAOFORGE_KEY_FILE:-~/.taoforge/validator.key}
export TAOFORGE_SEED_PEERS=${TAOFORGE_SEED_PEERS:-localhost:8091}

python -m neurons.validator "$@"
