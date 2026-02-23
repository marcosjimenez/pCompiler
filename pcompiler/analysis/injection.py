"""
Prompt injection risk analyser.

Scans user input templates and instructions for common injection
patterns and assigns a risk score with mitigation suggestions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class InjectionFinding:
    """A single injection risk finding."""
    pattern_name: str
    matched_text: str
    risk: RiskLevel
    suggestion: str
    location: str = ""


@dataclass
class InjectionReport:
    """Full injection analysis report."""
    findings: list[InjectionFinding] = field(default_factory=list)
    overall_risk: RiskLevel = RiskLevel.LOW

    @property
    def is_clean(self) -> bool:
        return len(self.findings) == 0


# ---------------------------------------------------------------------------
# Injection patterns
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str, RiskLevel, str]] = [
    # Direct overrides
    (
        re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)", re.I),
        "instruction_override",
        RiskLevel.CRITICAL,
        "User input contains an instruction override attempt. Apply strict sandboxing.",
    ),
    (
        re.compile(r"forget\s+(everything|all|your)\s+(instructions?|rules?|constraints?)", re.I),
        "forget_instructions",
        RiskLevel.CRITICAL,
        "Attempt to erase system instructions. This must be blocked.",
    ),
    (
        re.compile(r"you\s+are\s+now\s+(a|an|the)\b", re.I),
        "role_hijack",
        RiskLevel.HIGH,
        "Attempt to redefine the model's role. Consider blocking role changes in user input.",
    ),
    (
        re.compile(r"(system\s*prompt|system\s*message|system\s*instruction)", re.I),
        "system_prompt_reference",
        RiskLevel.HIGH,
        "User input references the system prompt. This may be a leak attempt.",
    ),
    (
        re.compile(r"(repeat|display|show|print|output)\s+(the\s+)?(system|initial|original)\s+(prompt|message|instructions?)", re.I),
        "system_prompt_leak",
        RiskLevel.CRITICAL,
        "Direct attempt to extract the system prompt.",
    ),
    # Code execution
    (
        re.compile(r"(execute|run|eval)\s+(this\s+)?(code|script|command)", re.I),
        "code_execution",
        RiskLevel.HIGH,
        "User input asks to execute code. Ensure code execution is disabled.",
    ),
    # Delimiter manipulation
    (
        re.compile(r"```\s*(system|assistant)", re.I),
        "delimiter_injection",
        RiskLevel.MEDIUM,
        "User input contains role-like code fences that might confuse the model.",
    ),
    # Markdown / formatting abuse
    (
        re.compile(r"\[SYSTEM\]|\[INST\]|\[/INST\]|<\|im_start\|>|<\|im_end\|>", re.I),
        "special_token_injection",
        RiskLevel.CRITICAL,
        "User input contains model-specific special tokens.",
    ),
    # Jailbreak keywords
    (
        re.compile(r"(DAN|Do Anything Now|jailbreak|bypass\s+filters?)", re.I),
        "jailbreak_keyword",
        RiskLevel.HIGH,
        "Known jailbreak keywords detected.",
    ),
]


def analyze_injection_risk(
    *texts: str,
    location: str = "user_input",
) -> InjectionReport:
    """Scan one or more text fragments for injection patterns."""

    findings: list[InjectionFinding] = []
    max_risk = RiskLevel.LOW

    risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]

    for text in texts:
        for pattern, name, risk, suggestion in _INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                findings.append(InjectionFinding(
                    pattern_name=name,
                    matched_text=match.group(0),
                    risk=risk,
                    suggestion=suggestion,
                    location=location,
                ))
                if risk_order.index(risk) > risk_order.index(max_risk):
                    max_risk = risk

    return InjectionReport(findings=findings, overall_risk=max_risk)
