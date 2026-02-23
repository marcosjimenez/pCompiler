"""
Chain-of-thought (CoT) auto-insertion.

Inserts a CoT section into the IR based on the configured policy (always,
auto, never) and the task template's recommendation.
"""

from __future__ import annotations

from pcompiler.dsl.examples import get_task_template
from pcompiler.dsl.schema import CoTPolicy
from pcompiler.ir.nodes import PromptIR, SectionKind


# Default CoT instruction text
_COT_TEXT = (
    "Think step by step. Before giving your final answer, break down "
    "the problem and reason through each component carefully."
)


def insert_chain_of_thought(
    ir: PromptIR,
    policy: CoTPolicy,
    task_name: str | None = None,
) -> PromptIR:
    """Conditionally insert a chain-of-thought section.

    - ``ALWAYS``: insert CoT regardless of task.
    - ``NEVER``: never insert.
    - ``AUTO``: insert only if the task template recommends it.

    Returns:
        A *new* PromptIR (original is not mutated).
    """
    should_insert = False

    if policy == CoTPolicy.ALWAYS:
        should_insert = True
    elif policy == CoTPolicy.NEVER:
        should_insert = False
    elif policy == CoTPolicy.AUTO:
        # Check task template recommendation
        if task_name:
            template = get_task_template(task_name)
            if template and template.recommended_cot:
                should_insert = True

    # Don't double-insert
    if should_insert and not ir.get_sections(SectionKind.CHAIN_OF_THOUGHT):
        new_ir = PromptIR(
            task=ir.task,
            model_target=ir.model_target,
            sections=list(ir.sections),
            metadata=dict(ir.metadata),
        )
        new_ir.add(SectionKind.CHAIN_OF_THOUGHT, _COT_TEXT, priority=40)
        return new_ir

    return ir
