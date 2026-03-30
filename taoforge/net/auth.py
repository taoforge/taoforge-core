"""Ed25519 keypair management and request signing for TaoForge nodes."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


@dataclass
class Keypair:
    """An Ed25519 keypair for node identity and request signing."""

    private_key: Ed25519PrivateKey
    public_key: Ed25519PublicKey

    @property
    def public_key_hex(self) -> str:
        """Hex-encoded public key (node identity)."""
        raw = self.public_key.public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        return raw.hex()

    @property
    def node_id(self) -> str:
        """Short node ID derived from public key."""
        return self.public_key_hex[:16]

    def sign(self, data: bytes) -> bytes:
        """Sign data with the private key."""
        return self.private_key.sign(data)

    def verify(self, signature: bytes, data: bytes) -> bool:
        """Verify a signature against this keypair's public key."""
        try:
            self.public_key.verify(signature, data)
            return True
        except Exception:
            return False

    @classmethod
    def generate(cls) -> Keypair:
        """Generate a new random keypair."""
        private = Ed25519PrivateKey.generate()
        return cls(private_key=private, public_key=private.public_key())

    @classmethod
    def from_file(cls, path: str | Path) -> Keypair:
        """Load a keypair from a PEM file."""
        path = Path(path)
        pem_data = path.read_bytes()
        private = serialization.load_pem_private_key(pem_data, password=None)
        if not isinstance(private, Ed25519PrivateKey):
            raise TypeError("Key file does not contain an Ed25519 private key.")
        return cls(private_key=private, public_key=private.public_key())

    def save(self, path: str | Path) -> None:
        """Save the private key to a PEM file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pem = self.private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        path.write_bytes(pem)

    @classmethod
    def load_or_create(cls, path: str | Path) -> Keypair:
        """Load an existing keypair or generate and save a new one."""
        path = Path(path)
        if path.exists():
            return cls.from_file(path)
        kp = cls.generate()
        kp.save(path)
        return kp


def sign_request(keypair: Keypair, method: str, path: str, body: bytes) -> dict[str, str]:
    """Create signed headers for an HTTP request.

    Returns headers dict with:
    - X-Node-ID: public key hex
    - X-Timestamp: unix timestamp
    - X-Signature: hex-encoded signature of (method|path|timestamp|body_hash)
    """
    timestamp = str(int(time.time()))
    body_hash = hashlib.sha256(body).hexdigest()
    payload = f"{method}|{path}|{timestamp}|{body_hash}".encode()
    signature = keypair.sign(payload)

    return {
        "X-Node-ID": keypair.public_key_hex,
        "X-Timestamp": timestamp,
        "X-Signature": signature.hex(),
    }


def verify_request(
    public_key_hex: str,
    method: str,
    path: str,
    body: bytes,
    timestamp: str,
    signature_hex: str,
    max_age_seconds: int = 300,
) -> bool:
    """Verify a signed HTTP request.

    Checks signature validity and timestamp freshness.
    """
    # Check timestamp freshness
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > max_age_seconds:
            return False
    except ValueError:
        return False

    # Reconstruct payload
    body_hash = hashlib.sha256(body).hexdigest()
    payload = f"{method}|{path}|{timestamp}|{body_hash}".encode()

    # Verify signature
    try:
        raw_key = bytes.fromhex(public_key_hex)
        public_key = Ed25519PublicKey.from_public_bytes(raw_key)
        signature = bytes.fromhex(signature_hex)
        public_key.verify(signature, payload)
        return True
    except Exception:
        return False
