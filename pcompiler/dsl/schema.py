"""
Pydantic models defining the DSL schema for prompt specifications.

A PromptSpec is the top-level object parsed from a YAML file. It contains
all the information needed to compile a prompt for any target model.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Tone(str, Enum):
    """Allowed tone values for prompt output."""
    FORMAL = "formal"
    INFORMAL = "informal"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    NEUTRAL = "neutral"


class SecurityLevel(str, Enum):
    """Level of security sanitization applied to user inputs."""
    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"


class CoTPolicy(str, Enum):
    """Chain-of-thought insertion policy."""
    ALWAYS = "always"
    AUTO = "auto"
    NEVER = "never"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class Constraints(BaseModel):
    """Constraints governing the compiled prompt behaviour."""
    max_tokens: int | None = Field(None, gt=0, description="Max output tokens.")
    tone: Tone = Field(Tone.NEUTRAL, description="Desired output tone.")
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    top_p: float | None = Field(None, ge=0.0, le=1.0)
    cot_policy: CoTPolicy = Field(CoTPolicy.AUTO, description="Chain-of-thought policy.")
    include_risks: bool = False
    include_citations: bool = False
    include_confidence: bool = False

    @model_validator(mode="after")
    def _validate_sampling(self) -> "Constraints":
        """Warn if both temperature and top_p are set (generally discouraged)."""
        # We allow it but could emit a warning downstream.
        return self


class FewShotExample(BaseModel):
    """A single few-shot example pair."""
    input: str = Field(..., min_length=1)
    output: str = Field(..., min_length=1)
    explanation: str | None = None


class OutputSchema(BaseModel):
    """Describes the expected output format via JSON Schema."""
    type: str = Field("object", description="Root JSON Schema type.")
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    additional_properties: bool = Field(False, alias="additionalProperties")

    model_config = {"populate_by_name": True}


class SecurityPolicy(BaseModel):
    """Security rules applied during compilation."""
    level: SecurityLevel = SecurityLevel.MODERATE
    block_code_execution: bool = True
    block_system_prompt_leak: bool = True
    block_instruction_override: bool = True


class CustomInstruction(BaseModel):
    """A user-defined instruction with optional priority."""
    text: str = Field(..., min_length=1)
    priority: int = Field(0, ge=0, le=100, description="Higher = more important (0-100).")


class ContextSourceType(str, Enum):
    """Types of context sources supported by pCompiler."""
    STATIC = "static"
    DYNAMIC = "dynamic"
    VECTOR_STORE = "vector_store"
    WEB_SEARCH = "web_search"
    LOCAL_FILE = "local_file"


class ContextSource(BaseModel):
    """Definition of a single context source."""
    type: ContextSourceType = ContextSourceType.STATIC
    value: str | None = None
    query: str | None = None
    max_tokens: int | None = Field(None, gt=0)
    priority: int = Field(50, ge=0, le=100)
    config: dict[str, Any] = Field(default_factory=dict)


class ContextConfig(BaseModel):
    """Container for multiple context sources and optimization settings."""
    sources: list[ContextSource] = Field(default_factory=list)
    combine_strategy: str = Field("ranked", description="How to merge sources: 'ranked' or 'ordered'.")
    max_total_tokens: int | None = Field(None, gt=0)


# ---------------------------------------------------------------------------
# Top-level PromptSpec
# ---------------------------------------------------------------------------

class PromptSpec(BaseModel):
    """
    Top-level prompt specification — the main artefact of the DSL.

    Example YAML::

        task: summarize
        input_type: legal_contract
        model_target: gpt-4o
        constraints:
          max_tokens: 500
          tone: formal
          include_risks: true
        instructions:
          - text: "Summarize the key clauses and risks."
            priority: 80
        context:
          sources:
            - type: static
              value: "The user is a senior legal partner."
            - type: local_file
              value: "contract_terms.txt"
          max_total_tokens: 2000
        few_shot_examples:
          - input: "Contract clause about liability…"
            output: "The liability clause limits…"
        output_schema:
          type: object
          properties:
            summary:
              type: string
            risks:
              type: array
              items:
                type: string
          required: [summary]
        security:
          level: strict
    """

    task: str = Field(..., min_length=1, description="Name of the task (e.g. summarize, classify).")
    input_type: str = Field("text", description="Semantic type of the input data.")
    model_target: str = Field("gpt-4o", description="Target model identifier.")
    context: str | ContextConfig | None = Field(
        None, description="Static context or dynamic context configuration."
    )
    user_input_template: str | None = Field(
        None,
        description="Template for user input (use {input} placeholder).",
    )

    constraints: Constraints = Field(default_factory=Constraints)
    instructions: list[CustomInstruction] = Field(default_factory=list)
    few_shot_examples: list[FewShotExample] = Field(default_factory=list)
    output_schema: OutputSchema | None = None
    security: SecurityPolicy = Field(default_factory=SecurityPolicy)

    # --- Metadata ---
    version: str = Field("1.0", description="Spec version for traceability.")
    description: str | None = Field(None, description="Human-readable description.")
    tags: list[str] = Field(default_factory=list)
