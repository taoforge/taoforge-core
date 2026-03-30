"""Tests for the mutation framework."""

import pytest

from taoforge.mutation.applicator import MutationApplicator
from taoforge.mutation.compound import CompoundMutation
from taoforge.mutation.types import AgentState, MutationDelta, MutationType
from taoforge.mutation.validator import MutationValidator


def test_mutation_type_enum():
    assert MutationType.LORA_MERGE.value == "lora_merge"
    assert MutationType.COMPOUND.value == "compound"


def test_mutation_delta_validate():
    delta = MutationDelta(
        mutation_type=MutationType.LORA_MERGE,
        description="Test merge",
    )
    assert delta.validate() == []


def test_mutation_delta_missing_description():
    delta = MutationDelta(mutation_type=MutationType.LORA_MERGE, description="")
    errors = delta.validate()
    assert len(errors) > 0


def test_compound_mutation_compose():
    cm = CompoundMutation(max_parts=4)
    parts = [
        MutationDelta(mutation_type=MutationType.LORA_MERGE, description="LoRA"),
        MutationDelta(mutation_type=MutationType.PROMPT_CHAIN_REFACTOR, description="Prompt"),
    ]
    compound = cm.compose(parts)
    assert compound.is_compound
    assert len(compound.compound_parts) == 2


def test_compound_mutation_max_parts():
    cm = CompoundMutation(max_parts=2)
    parts = [
        MutationDelta(mutation_type=MutationType.LORA_MERGE, description="a"),
        MutationDelta(mutation_type=MutationType.PROMPT_CHAIN_REFACTOR, description="b"),
        MutationDelta(mutation_type=MutationType.TOOL_GRAPH_REWIRE, description="c"),
    ]
    with pytest.raises(ValueError, match="max is 2"):
        cm.compose(parts)


def test_mutation_applicator_dispatch():
    applicator = MutationApplicator()
    state = AgentState(agent_id="test", weights_hash="abc")
    delta = MutationDelta(
        mutation_type=MutationType.LORA_MERGE,
        description="Test",
        diff_hash="new_hash",
    )
    new_state = applicator.apply(state, delta)
    assert new_state.agent_id == "test"


def test_mutation_validator():
    v = MutationValidator()
    delta = MutationDelta(
        mutation_type=MutationType.LORA_MERGE,
        description="Valid mutation",
    )
    assert v.is_valid(delta)


def test_mutation_validator_nested_compound():
    v = MutationValidator()
    inner = MutationDelta(mutation_type=MutationType.COMPOUND, description="nested", compound_parts=[])
    outer = MutationDelta(
        mutation_type=MutationType.COMPOUND,
        description="outer",
        compound_parts=[inner],
    )
    assert not v.is_valid(outer)
