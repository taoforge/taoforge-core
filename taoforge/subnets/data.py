"""Metagraph data layer — fetch, cache, and query Bittensor subnet snapshots."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"


@dataclass
class NeuronInfo:
    """Information about a single neuron (miner or validator) in a subnet."""

    uid: int = 0
    hotkey: str = ""
    coldkey: str = ""
    stake: float = 0.0
    rank: float = 0.0
    trust: float = 0.0
    incentive: float = 0.0
    emission: float = 0.0
    dividends: float = 0.0
    is_validator: bool = False
    active: bool = True
    last_update: int = 0


@dataclass
class MetagraphSnapshot:
    """A point-in-time snapshot of a Bittensor subnet's metagraph."""

    netuid: int = 0
    network: str = "finney"
    block: int = 0
    timestamp: float = 0.0
    neurons: list[NeuronInfo] = field(default_factory=list)
    # weights[validator_uid] = {miner_uid: weight_value}
    weights: dict[int, dict[int, float]] = field(default_factory=dict)
    # bonds[validator_uid] = {miner_uid: bond_value}
    bonds: dict[int, dict[int, float]] = field(default_factory=dict)

    # --- Computed properties ---

    @property
    def total_stake(self) -> float:
        return sum(n.stake for n in self.neurons)

    @property
    def active_count(self) -> int:
        return sum(1 for n in self.neurons if n.active)

    @property
    def validator_count(self) -> int:
        return sum(1 for n in self.neurons if n.is_validator)

    @property
    def miner_count(self) -> int:
        return sum(1 for n in self.neurons if not n.is_validator)

    def stake_distribution(self) -> dict[int, float]:
        """Map of uid -> fraction of total stake."""
        total = self.total_stake
        if total == 0:
            return {}
        return {n.uid: n.stake / total for n in self.neurons if n.stake > 0}

    def top_validators(self, n: int = 10) -> list[NeuronInfo]:
        validators = [neuron for neuron in self.neurons if neuron.is_validator]
        return sorted(validators, key=lambda x: x.stake, reverse=True)[:n]

    def top_miners(self, n: int = 10) -> list[NeuronInfo]:
        miners = [neuron for neuron in self.neurons if not neuron.is_validator]
        return sorted(miners, key=lambda x: x.incentive, reverse=True)[:n]

    def get_neuron(self, uid: int) -> Optional[NeuronInfo]:
        for n in self.neurons:
            if n.uid == uid:
                return n
        return None

    def get_neuron_by_hotkey(self, hotkey: str) -> Optional[NeuronInfo]:
        for n in self.neurons:
            if n.hotkey == hotkey:
                return n
        return None

    def gini_coefficient(self) -> float:
        """Compute Gini coefficient of stake distribution (0=equal, 1=concentrated)."""
        stakes = sorted(n.stake for n in self.neurons if n.stake > 0)
        if not stakes:
            return 0.0
        n = len(stakes)
        cumulative = sum((2 * (i + 1) - n - 1) * s for i, s in enumerate(stakes))
        total = sum(stakes)
        if total == 0:
            return 0.0
        return cumulative / (n * total)

    def total_emission(self) -> float:
        return sum(n.emission for n in self.neurons)

    def avg_incentive(self) -> float:
        miners = [n for n in self.neurons if not n.is_validator and n.incentive > 0]
        if not miners:
            return 0.0
        return sum(m.incentive for m in miners) / len(miners)

    # --- Prompt summary for agent context ---

    def to_prompt_summary(self, max_neurons: int = 20) -> str:
        """Format metagraph data as text for agent prompts."""
        lines = [
            f"=== Subnet {self.netuid} Metagraph (block {self.block}) ===",
            f"Network: {self.network}",
            f"Total neurons: {len(self.neurons)} ({self.active_count} active)",
            f"Validators: {self.validator_count} | Miners: {self.miner_count}",
            f"Total stake: {self.total_stake:.4f} TAO",
            f"Total emission: {self.total_emission():.6f}",
            f"Stake Gini coefficient: {self.gini_coefficient():.4f}",
            f"Average miner incentive: {self.avg_incentive():.6f}",
            "",
        ]

        # Top validators
        top_v = self.top_validators(min(max_neurons // 2, 10))
        if top_v:
            lines.append(f"--- Top {len(top_v)} Validators (by stake) ---")
            for v in top_v:
                lines.append(
                    f"  UID {v.uid} | hotkey={v.hotkey[:12]}... | "
                    f"stake={v.stake:.4f} | trust={v.trust:.4f} | "
                    f"dividends={v.dividends:.6f}"
                )
            lines.append("")

        # Top miners
        top_m = self.top_miners(min(max_neurons // 2, 10))
        if top_m:
            lines.append(f"--- Top {len(top_m)} Miners (by incentive) ---")
            for m in top_m:
                lines.append(
                    f"  UID {m.uid} | hotkey={m.hotkey[:12]}... | "
                    f"incentive={m.incentive:.6f} | emission={m.emission:.6f} | "
                    f"rank={m.rank:.4f}"
                )
            lines.append("")

        # Weight matrix sample (top 3 validators -> their top 5 weight targets)
        if self.weights:
            lines.append("--- Weight Matrix Sample (top validators -> top targets) ---")
            sorted_v_uids = sorted(self.weights.keys())[:3]
            for v_uid in sorted_v_uids:
                w = self.weights[v_uid]
                top_targets = sorted(w.items(), key=lambda x: x[1], reverse=True)[:5]
                targets_str = ", ".join(f"UID {uid}:{weight:.4f}" for uid, weight in top_targets)
                lines.append(f"  Validator UID {v_uid} -> [{targets_str}]")
            lines.append("")

        # Stake distribution stats
        dist = self.stake_distribution()
        if dist:
            top_holders = sorted(dist.items(), key=lambda x: x[1], reverse=True)[:5]
            lines.append("--- Stake Concentration ---")
            for uid, frac in top_holders:
                lines.append(f"  UID {uid}: {frac*100:.2f}% of total stake")
            top5_share = sum(frac for _, frac in top_holders)
            lines.append(f"  Top 5 hold {top5_share*100:.1f}% of total stake")

        return "\n".join(lines)

    # --- Serialization ---

    def to_dict(self) -> dict:
        return {
            "netuid": self.netuid,
            "network": self.network,
            "block": self.block,
            "timestamp": self.timestamp,
            "neurons": [asdict(n) for n in self.neurons],
            "weights": {str(k): {str(k2): v2 for k2, v2 in v.items()} for k, v in self.weights.items()},
            "bonds": {str(k): {str(k2): v2 for k2, v2 in v.items()} for k, v in self.bonds.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> MetagraphSnapshot:
        neurons = [NeuronInfo(**n) for n in data.get("neurons", [])]
        weights = {
            int(k): {int(k2): v2 for k2, v2 in v.items()}
            for k, v in data.get("weights", {}).items()
        }
        bonds = {
            int(k): {int(k2): v2 for k2, v2 in v.items()}
            for k, v in data.get("bonds", {}).items()
        }
        return cls(
            netuid=data.get("netuid", 0),
            network=data.get("network", "finney"),
            block=data.get("block", 0),
            timestamp=data.get("timestamp", 0.0),
            neurons=neurons,
            weights=weights,
            bonds=bonds,
        )


class MetagraphFetcher:
    """Fetches metagraph data from live Bittensor network or cached files."""

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else _SNAPSHOTS_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self, netuid: int, network: str = "finney") -> MetagraphSnapshot:
        """Fetch a metagraph snapshot. Tries live first, falls back to cache."""
        # Try live fetch
        try:
            snapshot = self._fetch_live(netuid, network)
            # Cache the result
            cache_path = self.cache_dir / f"sn{netuid}_{snapshot.block}.json"
            self.save_snapshot(snapshot, cache_path)
            logger.info(f"Fetched live metagraph for SN{netuid} at block {snapshot.block}")
            return snapshot
        except Exception as e:
            logger.warning(f"Live fetch failed for SN{netuid}: {e}. Trying cache...")

        # Fall back to cached
        return self._load_latest_cached(netuid)

    def _fetch_live(self, netuid: int, network: str) -> MetagraphSnapshot:
        """Fetch live metagraph via bittensor SDK."""
        try:
            from bittensor.core.metagraph import Metagraph
        except ImportError:
            raise RuntimeError(
                "bittensor SDK not installed. Install with: pip install bittensor "
                "or use cached snapshots."
            )

        mg = Metagraph(netuid=netuid, network=network, sync=True, lite=False)

        neurons = []
        for i in range(len(mg.uids)):
            uid = int(mg.uids[i])
            neurons.append(NeuronInfo(
                uid=uid,
                hotkey=str(mg.hotkeys[i]) if i < len(mg.hotkeys) else "",
                coldkey=str(mg.coldkeys[i]) if i < len(mg.coldkeys) else "",
                stake=float(mg.S[i]) if i < len(mg.S) else 0.0,
                rank=float(mg.R[i]) if i < len(mg.R) else 0.0,
                trust=float(mg.T[i]) if i < len(mg.T) else 0.0,
                incentive=float(mg.I[i]) if i < len(mg.I) else 0.0,
                emission=float(mg.E[i]) if i < len(mg.E) else 0.0,
                dividends=float(mg.D[i]) if i < len(mg.D) else 0.0,
                is_validator=bool(mg.validator_permit[i]) if i < len(mg.validator_permit) else False,
                active=bool(mg.active[i]) if i < len(mg.active) else True,
            ))

        # Extract weights matrix
        weights: dict[int, dict[int, float]] = {}
        if hasattr(mg, 'W') and mg.W is not None:
            import numpy as np
            w_matrix = np.array(mg.W)
            for v_idx in range(w_matrix.shape[0]):
                if neurons[v_idx].is_validator:
                    row = {}
                    for m_idx in range(w_matrix.shape[1]):
                        val = float(w_matrix[v_idx, m_idx])
                        if val > 0:
                            row[int(mg.uids[m_idx])] = val
                    if row:
                        weights[int(mg.uids[v_idx])] = row

        # Extract bonds matrix
        bonds: dict[int, dict[int, float]] = {}
        if hasattr(mg, 'B') and mg.B is not None:
            import numpy as np
            b_matrix = np.array(mg.B)
            for v_idx in range(b_matrix.shape[0]):
                if neurons[v_idx].is_validator:
                    row = {}
                    for m_idx in range(b_matrix.shape[1]):
                        val = float(b_matrix[v_idx, m_idx])
                        if val > 0:
                            row[int(mg.uids[m_idx])] = val
                    if row:
                        bonds[int(mg.uids[v_idx])] = row

        return MetagraphSnapshot(
            netuid=netuid,
            network=network,
            block=int(mg.block) if hasattr(mg, 'block') else 0,
            timestamp=time.time(),
            neurons=neurons,
            weights=weights,
            bonds=bonds,
        )

    def _load_latest_cached(self, netuid: int) -> MetagraphSnapshot:
        """Load the most recent cached snapshot for a subnet."""
        pattern = f"sn{netuid}_*.json"
        files = sorted(self.cache_dir.glob(pattern), reverse=True)

        if not files:
            raise FileNotFoundError(
                f"No cached snapshot found for SN{netuid} in {self.cache_dir}. "
                f"Run with bittensor SDK to generate one, or place a snapshot file there."
            )

        return self.load_cached(files[0])

    def load_cached(self, path: str | Path) -> MetagraphSnapshot:
        """Load a metagraph snapshot from a JSON file."""
        path = Path(path)
        data = json.loads(path.read_text())
        snapshot = MetagraphSnapshot.from_dict(data)
        logger.info(f"Loaded cached snapshot: SN{snapshot.netuid} block={snapshot.block} ({len(snapshot.neurons)} neurons)")
        return snapshot

    def save_snapshot(self, snapshot: MetagraphSnapshot, path: str | Path) -> None:
        """Save a metagraph snapshot to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshot.to_dict(), indent=2))

    def list_cached(self, netuid: int | None = None) -> list[Path]:
        """List cached snapshot files."""
        if netuid is not None:
            return sorted(self.cache_dir.glob(f"sn{netuid}_*.json"))
        return sorted(self.cache_dir.glob("sn*_*.json"))
