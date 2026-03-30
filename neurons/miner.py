"""TaoForge Miner — entry point for the miner neuron.

Agents propose self-improvements (mutations) in response to validator challenges.
"""

from __future__ import annotations

import logging
import random
import uuid

from taoforge.agent import Agent, AgentConfig, create_agent
from taoforge.agent.mutator import AgentMutator
from taoforge.base.config import MinerConfig
from taoforge.base.miner import BaseMinerNeuron
from taoforge.evaluation.engine import BenchmarkEngine
from taoforge.evaluation.suite import BenchmarkSuite
from taoforge.evaluation.task import CodeGenerationTask, PlanningTask, TextReasoningTask
from taoforge.mutation.types import MutationDelta, MutationType
from taoforge.zk.bridge import generate_proof
from taoforge.utils.hashing import hash_score

logger = logging.getLogger(__name__)


class TaoForgeMiner(BaseMinerNeuron):
    """TaoForge miner: proposes self-improvement mutations."""

    def __init__(self, config: MinerConfig, agent_config: AgentConfig | None = None) -> None:
        super().__init__(config)

        # Initialize agent
        self.agent_config = agent_config or AgentConfig(runtime="local_llm")
        self.agent: Agent | None = None
        self.mutator = AgentMutator()
        self.engine = BenchmarkEngine()
        self._suite = self._build_default_suite()

    def load_agent(self, agent_config: AgentConfig | None = None) -> None:
        """Load the miner's agent."""
        if agent_config:
            self.agent_config = agent_config
        self.agent = create_agent(self.agent_config)
        self.agent.load()
        logger.info(f"Agent loaded: {self.agent}")

    async def handle_proposal(self, data: dict) -> dict:
        """Handle an improvement proposal challenge from a validator.

        Full self-improvement cycle:
        1. Run baseline eval on current agent
        2. Select and apply a mutation
        3. Evaluate the mutated agent
        4. If improved, generate ZK proofs and return proposal
        """
        challenge_id = data.get("challenge_id", "")
        benchmark_id = data.get("benchmark_id", "")

        logger.info(f"Received challenge | id={challenge_id} | benchmark={benchmark_id}")

        if self.agent is None:
            return {"proposal_id": None, "challenge_id": challenge_id, "error": "No agent loaded"}

        # 1. Baseline eval
        baseline_result = self.engine.run_suite(self.agent, self._suite)
        baseline_score = baseline_result.aggregate_score

        # 2. Select mutation
        mutation_type, delta = self._select_and_create_mutation()

        # 3. Apply mutation (clone agent state first)
        original_state_hash = self.agent.get_state_hash()
        self.mutator.apply_mutation(self.agent, delta)

        # 4. Delta eval
        delta_result = self.engine.run_suite(self.agent, self._suite)
        delta_score = delta_result.aggregate_score

        improvement = delta_score - baseline_score

        if improvement <= 0:
            # Revert — no improvement
            logger.info(f"No improvement ({improvement:.4f}). Reverting mutation.")
            # TODO: Restore agent from checkpoint
            return {"proposal_id": None, "challenge_id": challenge_id, "improvement": improvement}

        # 5. Generate ZK proofs
        baseline_proof = generate_proof(
            circuit_type="baseline",
            private_inputs={"weights_hash": original_state_hash, "score": baseline_score},
            public_inputs={"benchmark_id": benchmark_id, "score_hash": hash_score(baseline_score)},
        )
        delta_proof = generate_proof(
            circuit_type="improvement",
            private_inputs={"weights_hash": self.agent.get_state_hash(), "score": delta_score},
            public_inputs={
                "benchmark_id": benchmark_id,
                "score_base_hash": hash_score(baseline_score),
                "score_delta_hash": hash_score(delta_score),
                "improvement_claim": improvement,
            },
        )

        # 6. Build proposal response
        proposal_id = str(uuid.uuid4())
        logger.info(
            f"IMPROVEMENT FOUND | proposal={proposal_id} | "
            f"{baseline_score:.4f} -> {delta_score:.4f} (+{improvement:.4f}) | "
            f"mutation={mutation_type.value}"
        )

        return {
            "proposal_id": proposal_id,
            "challenge_id": challenge_id,
            "agent_hotkey": self.keypair.public_key_hex,
            "mutation_type": mutation_type.value,
            "improvement_claim": improvement,
            "baseline_score_hash": hash_score(baseline_score),
            "delta_score_hash": hash_score(delta_score),
            "baseline_proof_bytes": baseline_proof.proof.proof_bytes if baseline_proof.success else None,
            "delta_proof_bytes": delta_proof.proof.proof_bytes if delta_proof.success else None,
            "bond_amount": self.miner_config.min_bond,
            "mutation_description": delta.description,
        }

    async def handle_benchmark(self, data: dict) -> dict:
        """Handle a benchmark re-evaluation challenge."""
        if self.agent is None:
            return {"challenge_id": data.get("challenge_id"), "error": "No agent loaded"}

        result = self.engine.run_suite(self.agent, self._suite)
        return {
            "challenge_id": data.get("challenge_id"),
            "task_scores": {ts.task_id: ts.score for ts in result.task_scores},
            "aggregate_score": result.aggregate_score,
        }

    def _select_and_create_mutation(self) -> tuple[MutationType, MutationDelta]:
        """Select a mutation type and create a delta."""
        # Weighted random selection — prompt mutations are safest for early iterations
        weights = {
            MutationType.PROMPT_CHAIN_REFACTOR: 0.4,
            MutationType.INFERENCE_PIPELINE: 0.3,
            MutationType.TOOL_GRAPH_REWIRE: 0.15,
            MutationType.LORA_MERGE: 0.1,
            MutationType.MEMORY_INDEX_REBUILD: 0.05,
        }
        mutation_type = random.choices(list(weights.keys()), list(weights.values()))[0]

        delta = self._create_mutation_delta(mutation_type)
        return mutation_type, delta

    def _create_mutation_delta(self, mutation_type: MutationType) -> MutationDelta:
        """Create a concrete mutation delta for the selected type."""
        if mutation_type == MutationType.PROMPT_CHAIN_REFACTOR:
            # Generate a new system prompt variation
            variations = [
                "You are a precise and thorough assistant. Think step by step before answering.",
                "You are an expert problem solver. Break complex problems into parts.",
                "You are a clear communicator. Be concise but complete in your answers.",
                "You are a careful analyst. Consider multiple perspectives before responding.",
            ]
            return MutationDelta(
                mutation_type=mutation_type,
                description="Prompt chain refactor — trying new system prompt",
                parameters={"system_prompt": random.choice(variations)},
            )

        elif mutation_type == MutationType.INFERENCE_PIPELINE:
            return MutationDelta(
                mutation_type=mutation_type,
                description="Inference pipeline tuning — adjusting temperature/top_p",
                parameters={
                    "temperature": random.uniform(0.3, 1.0),
                    "top_p": random.uniform(0.8, 1.0),
                },
            )

        elif mutation_type == MutationType.TOOL_GRAPH_REWIRE:
            return MutationDelta(
                mutation_type=mutation_type,
                description="Tool graph rewire — updating tool definitions",
                parameters={"tools": []},  # TODO: Generate useful tool configs
            )

        else:
            return MutationDelta(
                mutation_type=mutation_type,
                description=f"Mutation: {mutation_type.value}",
            )

    def _build_default_suite(self) -> BenchmarkSuite:
        """Build the default benchmark suite for self-evaluation."""
        suite = BenchmarkSuite(suite_id="taoforge_default_v0.1")
        suite.add_task(TextReasoningTask(
            "reasoning_basic",
            "What are three key differences between a list and a tuple in Python?",
            expected_keywords=["immutable", "mutable", "tuple", "list"],
        ))
        suite.add_task(TextReasoningTask(
            "reasoning_logic",
            "If all roses are flowers and some flowers fade quickly, can we conclude that some roses fade quickly?",
            expected_keywords=["cannot", "conclude", "not necessarily"],
        ))
        suite.add_task(CodeGenerationTask(
            "code_fizzbuzz",
            "Write a Python function called fizzbuzz(n) that returns 'Fizz' for multiples of 3, 'Buzz' for multiples of 5, 'FizzBuzz' for multiples of both, and the number as a string otherwise.",
            test_cases=[
                {"function": "fizzbuzz", "input": [3], "expected": "Fizz"},
                {"function": "fizzbuzz", "input": [5], "expected": "Buzz"},
                {"function": "fizzbuzz", "input": [15], "expected": "FizzBuzz"},
                {"function": "fizzbuzz", "input": [7], "expected": "7"},
            ],
        ))
        suite.add_task(PlanningTask(
            "planning_basic",
            "Deploy a web application to production",
            constraints=["Must have zero downtime", "Must include rollback plan"],
            expected_steps=5,
        ))
        return suite


def main() -> None:
    """Entry point for the TaoForge miner."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="TaoForge Miner")
    parser.add_argument("--model", type=str, default=os.environ.get("TAOFORGE_MODEL", ""),
                        help="Model name/path for local LLM or API model name")
    parser.add_argument("--provider", type=str, default=os.environ.get("TAOFORGE_PROVIDER", ""),
                        choices=["openai", "anthropic", "local", ""],
                        help="Agent provider: openai, anthropic, or local")
    parser.add_argument("--device", type=str, default=os.environ.get("TAOFORGE_DEVICE", "auto"),
                        help="Device for local LLM (auto/cuda/cpu)")
    parser.add_argument("--port", type=int, default=None, help="Override listen port")
    parser.add_argument("--host", type=str, default=None, help="Override listen host")
    parser.add_argument("--seed-peers", type=str, nargs="*", default=None,
                        help="Seed peers (host:port)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    config = MinerConfig()
    if args.port:
        config.port = args.port
    if args.host:
        config.host = args.host
    if args.seed_peers:
        config.seed_peers = args.seed_peers

    miner = TaoForgeMiner(config)

    # Determine agent configuration
    model = args.model
    provider = args.provider

    if provider in ("openai", "anthropic"):
        agent_config = AgentConfig(
            runtime="api",
            api_provider=provider,
            api_model=model or ("gpt-4o-mini" if provider == "openai" else "claude-sonnet-4-6"),
            system_prompt="You are a helpful assistant.",
        )
        miner.load_agent(agent_config)
    elif provider == "local" or (model and not provider):
        agent_config = AgentConfig(
            runtime="local_llm",
            model_name_or_path=model or "microsoft/phi-3-mini-4k-instruct",
            device=args.device,
        )
        miner.load_agent(agent_config)
    else:
        logger.warning(
            "No agent configured. Set --model/--provider or "
            "TAOFORGE_MODEL/TAOFORGE_PROVIDER env vars. "
            "Miner will start but reject proposals until an agent is loaded."
        )

    miner.run()


if __name__ == "__main__":
    main()
