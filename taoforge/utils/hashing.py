"""Hashing utilities — SHA-256 commitments and Merkle helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def hash_score(score: float) -> str:
    """Create a SHA-256 hash commitment to a score value."""
    data = str(score).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def hash_weights(weights: bytes | str) -> str:
    """Create a SHA-256 hash of model weights or weight identifier."""
    if isinstance(weights, str):
        weights = weights.encode("utf-8")
    return hashlib.sha256(weights).hexdigest()


def hash_dict(data: dict[str, Any]) -> str:
    """Create a deterministic SHA-256 hash of a dictionary."""
    serialized = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def compute_merkle_root(items: list[str]) -> str:
    """Compute a Merkle root from a list of hex-encoded hashes.

    Args:
        items: List of hex-encoded hash strings.

    Returns:
        Hex-encoded Merkle root hash.
    """
    if not items:
        return hashlib.sha256(b"").hexdigest()

    if len(items) == 1:
        return items[0]

    # Pad to even length
    layer = list(items)
    if len(layer) % 2 != 0:
        layer.append(layer[-1])

    while len(layer) > 1:
        next_layer = []
        for i in range(0, len(layer), 2):
            combined = bytes.fromhex(layer[i]) + bytes.fromhex(layer[i + 1])
            next_layer.append(hashlib.sha256(combined).hexdigest())
        layer = next_layer

    return layer[0]
