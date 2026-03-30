#!/bin/bash
set -e

export TAOFORGE_HOST=${TAOFORGE_HOST:-0.0.0.0}
export TAOFORGE_PORT=${TAOFORGE_PORT:-8091}
export TAOFORGE_KEY_FILE=${TAOFORGE_KEY_FILE:-~/.taoforge/miner.key}

python -m neurons.miner "$@"
