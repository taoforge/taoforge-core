"""Mutation structural validator — checks well-formedness without evaluating improvement."""

from __future__ import annotations

from taoforge.mutation.types import MutationDelta, MutationType

# Maximum allowed mutation delta size (bytes)
MAX_DELTA_SIZE = 100 * 1024 * 1024  # 100 MB


class MutationValidator:
    """Validates mutation deltas for structural integrity.

    Checks well-formedness, size constraints, and type compatibility.
    Does NOT verify whether the mutation actually improves the agent
    — that's the evaluation engine's job.
    """

    def __init__(self, max_delta_size: int = MAX_DELTA_SIZE, max_compound_parts: int = 4) -> None:
        self.max_delta_size = max_delta_size
        self.max_compound_parts = max_compound_parts

    def validate(self, delta: MutationDelta) -> list[str]:
        """Run all structural validation checks. Returns list of errors."""
        errors = []

        # Basic structure
        errors.extend(delta.validate())

        # Type-specific checks
        if delta.mutation_type not in MutationType:
            errors.append(f"Unknown mutation type: {delta.mutation_type}")

        # Compound-specific checks
        if delta.is_compound:
            errors.extend(self._validate_compound(delta))

        # Size constraint (when diff_hash indicates actual data)
        if delta.parameters.get("delta_size_bytes", 0) > self.max_delta_size:
            errors.append(
                f"Delta size {delta.parameters['delta_size_bytes']} exceeds "
                f"maximum {self.max_delta_size} bytes."
            )

        return errors

    def _validate_compound(self, delta: MutationDelta) -> list[str]:
        """Validate compound mutation constraints."""
        errors = []
        if not delta.compound_parts:
            errors.append("Compound mutation has no parts.")
            return errors

        if len(delta.compound_parts) > self.max_compound_parts:
            errors.append(
                f"Compound mutation has {len(delta.compound_parts)} parts, "
                f"max is {self.max_compound_parts}."
            )

        # Check for duplicate types
        types_seen = set()
        for part in delta.compound_parts:
            if part.mutation_type in types_seen:
                errors.append(f"Duplicate mutation type in compound: {part.mutation_type}")
            types_seen.add(part.mutation_type)

            # Nested compounds not allowed
            if part.is_compound:
                errors.append("Nested compound mutations are not allowed.")

        return errors

    def is_valid(self, delta: MutationDelta) -> bool:
        """Quick boolean check for validity."""
        return len(self.validate(delta)) == 0
