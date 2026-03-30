"""IPFS utilities — pin and fetch mutation deltas."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def pin_mutation_delta(delta_bytes: bytes, api_url: str = "/ip4/127.0.0.1/tcp/5001") -> str:
    """Pin a mutation delta to IPFS and return the CID.

    Args:
        delta_bytes: The mutation delta payload to pin.
        api_url: IPFS API multiaddr.

    Returns:
        IPFS CID string.
    """
    try:
        import ipfshttpclient

        client = ipfshttpclient.connect(api_url)
        result = client.add_bytes(delta_bytes)
        logger.info(f"Mutation delta pinned to IPFS | CID={result}")
        return result
    except ImportError:
        logger.warning("ipfshttpclient not installed — IPFS pinning unavailable.")
        return ""
    except Exception as e:
        logger.error(f"IPFS pin failed: {e}")
        return ""


def fetch_mutation_delta(cid: str, api_url: str = "/ip4/127.0.0.1/tcp/5001") -> Optional[bytes]:
    """Fetch a mutation delta from IPFS by CID.

    Args:
        cid: IPFS content identifier.
        api_url: IPFS API multiaddr.

    Returns:
        The mutation delta bytes, or None if fetch fails.
    """
    try:
        import ipfshttpclient

        client = ipfshttpclient.connect(api_url)
        data = client.cat(cid)
        return data
    except ImportError:
        logger.warning("ipfshttpclient not installed — IPFS fetch unavailable.")
        return None
    except Exception as e:
        logger.error(f"IPFS fetch failed for CID {cid}: {e}")
        return None
