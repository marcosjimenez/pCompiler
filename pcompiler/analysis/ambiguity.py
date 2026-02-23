"""
Ambiguity detection for prompt specifications.

Scans instructions and content for vague or ambiguous language patterns
and produces warnings with a clarity score.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pcompiler.ir.nodes import PromptIR, SectionKind


# Patterns that indicate vague / ambiguous language
_VAGUE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bmaybe\b", re.I), "Vague adverb 'maybe' — be explicit."),
    (re.compile(r"\bperhaps\b", re.I), "Vague adverb 'perhaps'."),
    (re.compile(r"\bprobably\b", re.I), "'probably' introduces ambiguity."),
    (re.compile(r"\bmight\b", re.I), "'might' is uncertain — prefer 'must' or 'should'."),
    (re.compile(r"\bcould\b", re.I), "'could' is ambiguous — state a clear instruction."),
    (re.compile(r"\bsome\b", re.I), "'some' is imprecise — specify a quantity or criteria."),
    (re.compile(r"\bsomething\b", re.I), "'something' is vague — be specific."),
    (re.compile(r"\betc\.?\b", re.I), "'etc.' hides details — list items explicitly."),
    (re.compile(r"\band so on\b", re.I), "'and so on' is vague."),
    (re.compile(r"\bif possible\b", re.I), "'if possible' – state whether it is required or optional."),
    (re.compile(r"\btry to\b", re.I), "'try to' — prefer a definitive instruction."),
    (re.compile(r"\bquizás\b", re.I), "'quizás' introduce ambigüedad."),
    (re.compile(r"\bprobablemente\b", re.I), "'probablemente' es impreciso."),
    (re.compile(r"\btal vez\b", re.I), "'tal vez' es vago."),
]

# Short instructions are prone to under-specification
_MIN_INSTRUCTION_LENGTH = 20


@dataclass
class AmbiguityWarning:
    """A single ambiguity finding."""
    section: str
    message: str
    severity: str = "warning"  # "info" | "warning" | "error"


@dataclass
class AmbiguityReport:
    """Result of ambiguity analysis."""
    warnings: list[AmbiguityWarning] = field(default_factory=list)
    clarity_score: float = 1.0  # 0.0 (very ambiguous) … 1.0 (clear)

    @property
    def is_clean(self) -> bool:
        return len(self.warnings) == 0


def analyze_ambiguity(ir: PromptIR) -> AmbiguityReport:
    """Scan the IR for vague or ambiguous language."""

    warnings: list[AmbiguityWarning] = []
    total_sections = len(ir.sections)
    hits = 0

    for node in ir.sections:
        section_label = node.kind.name

        # 1. Pattern-based vagueness detection
        for pattern, msg in _VAGUE_PATTERNS:
            if pattern.search(node.content):
                warnings.append(AmbiguityWarning(
                    section=section_label,
                    message=msg,
                ))
                hits += 1

        # 2. Very short instructions
        if node.kind == SectionKind.INSTRUCTIONS:
            if len(node.content.strip()) < _MIN_INSTRUCTION_LENGTH:
                warnings.append(AmbiguityWarning(
                    section=section_label,
                    message=(
                        f"Instruction is very short ({len(node.content.strip())} chars). "
                        "Consider adding more detail."
                    ),
                    severity="info",
                ))
                hits += 1

    # Clarity score: penalise by ratio of findings to sections
    if total_sections > 0:
        score = max(0.0, 1.0 - (hits / (total_sections * 3)))
    else:
        score = 1.0

    return AmbiguityReport(warnings=warnings, clarity_score=round(score, 2))
