"""
Built-in task definitions and system prompt templates.

These are used when the DSL specifies a known ``task`` name (e.g. "summarize")
to automatically inject appropriate system prompts and instructions.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TaskTemplate:
    """Predefined template for a common task type."""

    name: str
    system_prompt: str
    default_instructions: list[str] = field(default_factory=list)
    recommended_cot: bool = False
    description: str = ""


# ---------------------------------------------------------------------------
# Built-in templates
# ---------------------------------------------------------------------------

BUILTIN_TASKS: dict[str, TaskTemplate] = {
    "summarize": TaskTemplate(
        name="summarize",
        description="Summarize the given input concisely.",
        system_prompt=(
            "You are an expert summarizer. Your task is to produce clear, "
            "accurate, and concise summaries that capture the essential "
            "information from the provided input."
        ),
        default_instructions=[
            "Read the input carefully and identify the key points.",
            "Produce a summary that is faithful to the original content.",
            "Do not add information not present in the source.",
        ],
        recommended_cot=False,
    ),
    "classify": TaskTemplate(
        name="classify",
        description="Classify input into predefined categories.",
        system_prompt=(
            "You are a precise text classifier. Analyse the input and assign "
            "it to the most appropriate category. Justify your choice briefly."
        ),
        default_instructions=[
            "Analyse the input to determine its primary topic and intent.",
            "Select the single best matching category.",
            "Provide a brief justification for your classification.",
        ],
        recommended_cot=True,
    ),
    "extract": TaskTemplate(
        name="extract",
        description="Extract structured data from unstructured input.",
        system_prompt=(
            "You are a data extraction specialist. Parse the input and "
            "extract the requested fields accurately. Return only the "
            "extracted data in the specified format."
        ),
        default_instructions=[
            "Identify the requested fields in the input.",
            "Extract values exactly as they appear (do not paraphrase).",
            "If a field is not found, return null for that field.",
        ],
        recommended_cot=False,
    ),
    "translate": TaskTemplate(
        name="translate",
        description="Translate text between languages.",
        system_prompt=(
            "You are a professional translator. Produce natural, fluent "
            "translations that preserve the meaning, tone, and nuance of "
            "the original text."
        ),
        default_instructions=[
            "Translate the input faithfully preserving meaning and tone.",
            "Use natural idiomatic expressions in the target language.",
            "Do not add or remove information from the original.",
        ],
        recommended_cot=False,
    ),
    "analyze": TaskTemplate(
        name="analyze",
        description="Provide in-depth analysis of the input.",
        system_prompt=(
            "You are an analytical expert. Provide thorough, well-structured "
            "analysis of the input, identifying patterns, implications, and "
            "key insights."
        ),
        default_instructions=[
            "Examine the input from multiple perspectives.",
            "Identify key patterns, trends, and implications.",
            "Support your analysis with evidence from the input.",
            "Structure your response with clear sections.",
        ],
        recommended_cot=True,
    ),
    "generate": TaskTemplate(
        name="generate",
        description="Generate creative or structured content.",
        system_prompt=(
            "You are a skilled content creator. Generate high-quality "
            "content that meets the specified requirements and constraints."
        ),
        default_instructions=[
            "Follow the provided constraints and format requirements.",
            "Produce original, well-structured content.",
            "Ensure consistency in tone and style throughout.",
        ],
        recommended_cot=False,
    ),
}


def get_task_template(task_name: str) -> TaskTemplate | None:
    """Return the built-in template for *task_name*, or ``None``."""
    return BUILTIN_TASKS.get(task_name.lower())
