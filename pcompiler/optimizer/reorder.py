"""
Instruction reordering optimization.

Reorders IR sections according to the target model's optimal section order
as defined in its ModelProfile.
"""

from __future__ import annotations

from pcompiler.ir.nodes import PromptIR, SectionKind
from pcompiler.models.registry import ModelProfile


# Default ordering when the model profile doesn't specify one
_DEFAULT_ORDER: list[str] = [
    "SECURITY_PREAMBLE", "SYSTEM", "CONTEXT", "INSTRUCTIONS",
    "EXAMPLES", "OUTPUT_FORMAT", "CHAIN_OF_THOUGHT", "USER_INPUT",
]


def reorder_sections(ir: PromptIR, profile: ModelProfile) -> PromptIR:
    """Return a *new* PromptIR with sections reordered optimally.

    Sections of the same kind preserve their relative ordering.
    """
    order = profile.optimal_section_order or _DEFAULT_ORDER
    kind_priority = {name: idx for idx, name in enumerate(order)}

    # Stable sort: sections with equal kind-priority keep their insertion order
    sorted_sections = sorted(
        ir.sections,
        key=lambda node: kind_priority.get(node.kind.name, 999),
    )

    return PromptIR(
        task=ir.task,
        model_target=ir.model_target,
        sections=sorted_sections,
        metadata=dict(ir.metadata),
    )
