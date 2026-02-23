"""
OpenAI backend plugin — compiles prompts for GPT models.

Generates the Chat Completions API message format with support for
JSON mode, function calling schemas, and optimized GPT parameters.
"""

from __future__ import annotations

from typing import Any

from pcompiler.ir.nodes import PromptIR, SectionKind
from pcompiler.models.registry import ModelProfile
from pcompiler.plugins.base import BackendPlugin, CompiledPrompt


class OpenAIPlugin(BackendPlugin):
    """Backend plugin for OpenAI GPT models."""

    def name(self) -> str:
        return "openai"

    def supported_models(self) -> list[str]:
        return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]

    def emit(self, ir: PromptIR, profile: ModelProfile) -> CompiledPrompt:
        messages: list[dict[str, str]] = []
        parameters: dict[str, Any] = {}
        warnings: list[str] = []

        # --- System message ---
        system_parts: list[str] = []
        for section in ir.sections:
            if section.kind == SectionKind.SECURITY_PREAMBLE:
                system_parts.append(section.content)
            elif section.kind == SectionKind.SYSTEM:
                system_parts.append(section.content)

        if system_parts:
            messages.append({
                "role": "system",
                "content": self.format_system_prompt("\n\n".join(system_parts)),
            })

        # --- Build user message content ---
        user_parts: list[str] = []

        # Context
        for section in ir.get_sections(SectionKind.CONTEXT):
            user_parts.append(f"## Context\n{section.content}")

        # Instructions
        instructions = ir.get_sections(SectionKind.INSTRUCTIONS)
        if instructions:
            instr_text = "\n".join(f"- {s.content}" for s in instructions)
            user_parts.append(f"## Instructions\n{instr_text}")

        # Output format
        for section in ir.get_sections(SectionKind.OUTPUT_FORMAT):
            user_parts.append(f"## Output Format\n{section.content}")

        # Chain of thought
        for section in ir.get_sections(SectionKind.CHAIN_OF_THOUGHT):
            user_parts.append(f"## Reasoning\n{section.content}")

        # Few-shot examples
        examples = ir.get_sections(SectionKind.EXAMPLES)
        if examples:
            example_lines: list[str] = ["## Examples"]
            for i, ex in enumerate(examples, 1):
                example_lines.append(f"\n### Example {i}\n{ex.content}")
            user_parts.append("\n".join(example_lines))

        # User input
        for section in ir.get_sections(SectionKind.USER_INPUT):
            user_parts.append(f"## Input\n{section.content}")

        if user_parts:
            messages.append({
                "role": "user",
                "content": "\n\n".join(user_parts),
            })

        # --- Parameters ---
        parameters["model"] = profile.name

        # Temperature / top_p from IR metadata
        temp = ir.metadata.get("temperature", profile.default_temperature)
        top_p = ir.metadata.get("top_p", profile.default_top_p)
        parameters["temperature"] = temp
        if top_p < 1.0:
            parameters["top_p"] = top_p

        max_tokens = ir.metadata.get("max_tokens")
        if max_tokens:
            parameters["max_tokens"] = max_tokens

        # JSON mode
        output_schema = ir.metadata.get("output_schema")
        if output_schema and profile.supports_json_mode:
            parameters["response_format"] = {"type": "json_object"}

        # Token budget check
        estimated = ir.total_estimated_tokens()
        if estimated > profile.max_context_tokens * 0.9:
            warnings.append(
                f"Estimated token count ({estimated:,}) approaches the "
                f"context limit ({profile.max_context_tokens:,})."
            )

        # --- Flat text version ---
        prompt_text = "\n\n".join(
            f"[{m['role'].upper()}]\n{m['content']}" for m in messages
        )

        return CompiledPrompt(
            payload={"messages": messages},
            parameters=parameters,
            prompt_text=prompt_text,
            warnings=warnings,
            model_target=profile.name,
            plugin_used=self.name(),
        )
