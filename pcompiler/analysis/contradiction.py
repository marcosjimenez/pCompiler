"""
Contradiction detection in prompt specifications.

Detects conflicting constraints or mutually exclusive instructions
in the prompt specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pcompiler.dsl.schema import PromptSpec


@dataclass
class Contradiction:
    """A single detected contradiction."""
    field1: str
    field2: str
    message: str
    severity: str = "error"  # "warning" | "error"


@dataclass
class ContradictionReport:
    """Result of contradiction analysis."""
    contradictions: list[Contradiction] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return len(self.contradictions) == 0


# Tone pairs that conflict
_CONFLICTING_TONES: set[frozenset[str]] = {
    frozenset({"formal", "informal"}),
    frozenset({"formal", "creative"}),
    frozenset({"technical", "informal"}),
}

# Instruction keyword pairs that are typically contradictory
_CONTRADICTORY_PATTERNS: list[tuple[str, str, str]] = [
    ("concise", "detailed", "Instructions ask for both 'concise' and 'detailed' output."),
    ("brief", "comprehensive", "Instructions ask for both 'brief' and 'comprehensive'."),
    ("short", "exhaustive", "Instructions ask for both 'short' and 'exhaustive'."),
    ("formal", "casual", "Instructions mix 'formal' and 'casual' tone."),
    ("always", "never", "Instructions contain both 'always' and 'never' for the same concept."),
    ("include", "exclude", "Instructions ask to both 'include' and 'exclude' something."),
    ("json", "plain text", "Instructions require both 'json' and 'plain text' output."),
    ("no explanation", "explain", "Instructions ask for 'no explanation' but also to 'explain'."),
]


def detect_contradictions(spec: PromptSpec) -> ContradictionReport:
    """Analyse a PromptSpec for contradictory instructions or constraints."""

    contradictions: list[Contradiction] = []

    # 1. Temperature vs. deterministic expectations
    if spec.constraints.temperature is not None:
        if spec.constraints.temperature < 0.1 and spec.constraints.tone.value == "creative":
            contradictions.append(Contradiction(
                field1="constraints.temperature",
                field2="constraints.tone",
                message=(
                    f"Temperature={spec.constraints.temperature} is very low "
                    "but tone is 'creative'. Low temperature discourages creative output."
                ),
                severity="warning",
            ))
        if spec.constraints.temperature > 1.5 and spec.constraints.tone.value == "formal":
            contradictions.append(Contradiction(
                field1="constraints.temperature",
                field2="constraints.tone",
                message=(
                    f"Temperature={spec.constraints.temperature} is very high "
                    "but tone is 'formal'. High temperature may produce erratic output."
                ),
                severity="warning",
            ))

    # 2. Both temperature and top_p set
    if spec.constraints.temperature is not None and spec.constraints.top_p is not None:
        contradictions.append(Contradiction(
            field1="constraints.temperature",
            field2="constraints.top_p",
            message=(
                "Both temperature and top_p are set. Most providers recommend "
                "setting only one of these parameters."
            ),
            severity="warning",
        ))

    # 3. Instruction-level contradictions (keyword pairs)
    if spec.instructions:
        all_text = " ".join(instr.text.lower() for instr in spec.instructions)
        for word_a, word_b, msg in _CONTRADICTORY_PATTERNS:
            if word_a in all_text and word_b in all_text:
                contradictions.append(Contradiction(
                    field1=f"instructions ('{word_a}')",
                    field2=f"instructions ('{word_b}')",
                    message=msg,
                ))

    return ContradictionReport(contradictions=contradictions)
