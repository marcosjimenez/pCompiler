"""
Intermediate Representation (IR) for compiled prompts.

The IR is a model-agnostic, ordered collection of sections that backends
transform into the final model-specific payload.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class SectionKind(Enum):
    """Types of sections in a compiled prompt IR."""
    SYSTEM = auto()
    CONTEXT = auto()
    INSTRUCTIONS = auto()
    EXAMPLES = auto()
    USER_INPUT = auto()
    OUTPUT_FORMAT = auto()
    CHAIN_OF_THOUGHT = auto()
    SECURITY_PREAMBLE = auto()


@dataclass
class IRNode:
    """A single section / block inside the prompt IR."""

    kind: SectionKind
    content: str
    priority: int = 50
    metadata: dict[str, Any] = field(default_factory=dict)

    def estimated_tokens(self) -> int:
        """Rough token estimate (≈ 4 chars per token for English)."""
        return max(1, len(self.content) // 4)


@dataclass
class PromptIR:
    """
    The full Intermediate Representation of a prompt.

    Backends iterate over ``sections`` (in order) to build the final payload.
    """

    task: str
    model_target: str
    sections: list[IRNode] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def add(self, kind: SectionKind, content: str, *, priority: int = 50,
            **meta: Any) -> None:
        """Append a new section to the IR."""
        self.sections.append(IRNode(kind=kind, content=content,
                                     priority=priority, metadata=meta))

    def get_sections(self, kind: SectionKind) -> list[IRNode]:
        """Return all sections of a given kind."""
        return [s for s in self.sections if s.kind == kind]

    def total_estimated_tokens(self) -> int:
        """Sum of estimated tokens across all sections."""
        return sum(s.estimated_tokens() for s in self.sections)

    def sorted_by_priority(self) -> list[IRNode]:
        """Return sections sorted by descending priority."""
        return sorted(self.sections, key=lambda s: s.priority, reverse=True)
