"""
Semantic compression.

Removes redundant content, merges duplicate sections, and warns when
the estimated token count exceeds the model's context window.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pcompiler.ir.nodes import IRNode, PromptIR, SectionKind
from pcompiler.models.registry import ModelProfile


@dataclass
class CompressionResult:
    """Result of the compression pass."""
    ir: PromptIR
    tokens_before: int = 0
    tokens_after: int = 0
    warnings: list[str] = field(default_factory=list)
    sections_removed: int = 0


def compress(ir: PromptIR, profile: ModelProfile) -> CompressionResult:
    """Compress the IR by removing redundancies.

    Current strategies:
    1. Deduplicate identical sections.
    2. Merge sections of the same kind that are adjacent.
    3. Warn if token estimate exceeds the context window.
    """
    tokens_before = ir.total_estimated_tokens()
    warnings: list[str] = []
    sections_removed = 0

    # --- 1. Deduplicate identical content within the same kind ---
    seen: set[tuple[SectionKind, str]] = set()
    deduped: list[IRNode] = []
    for node in ir.sections:
        key = (node.kind, node.content.strip())
        if key in seen:
            sections_removed += 1
            continue
        seen.add(key)
        deduped.append(node)

    # --- 2. Merge adjacent sections of the same kind ---
    merged: list[IRNode] = []
    for node in deduped:
        if merged and merged[-1].kind == node.kind:
            # Merge content
            merged[-1] = IRNode(
                kind=node.kind,
                content=merged[-1].content + "\n" + node.content,
                priority=max(merged[-1].priority, node.priority),
                metadata={**merged[-1].metadata, **node.metadata},
            )
            sections_removed += 1
        else:
            merged.append(node)

    new_ir = PromptIR(
        task=ir.task,
        model_target=ir.model_target,
        sections=merged,
        metadata=dict(ir.metadata),
    )

    tokens_after = new_ir.total_estimated_tokens()

    # --- 3. Context window check ---
    if tokens_after > profile.max_context_tokens:
        warnings.append(
            f"Estimated tokens ({tokens_after:,}) EXCEED the context window "
            f"({profile.max_context_tokens:,}). The prompt may be truncated."
        )
    elif tokens_after > profile.max_context_tokens * 0.8:
        warnings.append(
            f"Estimated tokens ({tokens_after:,}) are near 80 % of the context "
            f"window ({profile.max_context_tokens:,})."
        )

    return CompressionResult(
        ir=new_ir,
        tokens_before=tokens_before,
        tokens_after=tokens_after,
        warnings=warnings,
        sections_removed=sections_removed,
    )
