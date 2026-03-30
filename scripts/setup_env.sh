#!/bin/bash
set -e

echo "=== TaoForge Dev Environment Setup ==="

# Python environment
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Rust ZK circuits (optional — requires Rust toolchain)
if command -v cargo &> /dev/null; then
    echo "Building ZK circuits..."
    pip install maturin
    cd zk_circuits && maturin develop && cd ..
    echo "ZK circuits built successfully."
else
    echo "Rust toolchain not found — skipping ZK circuit build."
    echo "Install from https://rustup.rs/ to build ZK circuits."
fi

echo "=== Setup complete ==="
