#!/bin/bash
set -e

echo "=== Building TaoForge ZK Circuits ==="

if ! command -v cargo &> /dev/null; then
    echo "Error: Rust toolchain not found. Install from https://rustup.rs/"
    exit 1
fi

if ! command -v maturin &> /dev/null; then
    pip install maturin
fi

cd zk_circuits
maturin develop --release
echo "=== ZK circuits built and installed ==="
