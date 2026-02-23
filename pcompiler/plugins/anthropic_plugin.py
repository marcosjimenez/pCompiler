"""
Anthropic backend plugin — compiles prompts for Claude models.

Generates the Messages API format with separate system parameter,
thinking tags for chain-of-thought, and Claude-optimized parameters.
"""

from __future__ import annotations

from typing import Any

from pcompiler.ir.nodes import PromptIR, SectionKind
from pcompiler.models.registry import ModelProfile
from pcompiler.plugins.base import BackendPlugin, CompiledPrompt


class AnthropicPlugin(BackendPlugin):
    """Backend plugin for Anthropic Claude models."""

    def name(self) -> str:
        return "anthropic"

    def supported_models(self) -> list[str]:
        return [
            "claude-3.5-sonnet", "claude-3-opus", "claude-3-sonnet",
            "claude-3-haiku", "claude-3.5-haiku",
        ]

    def emit(self, ir: PromptIR, profile: ModelProfile) -> CompiledPrompt:
        system_text = ""
        messages: list[dict[str, str]] = []
        parameters: dict[str, Any] = {}
        warnings: list[str] = []

        # --- System (separate parameter in Claude API) ---
        system_parts: list[str] = []
        for section in ir.sections:
            if section.kind == SectionKind.SECURITY_PREAMBLE:
                system_parts.append(section.content)
            elif section.kind == SectionKind.SYSTEM:
                system_parts.append(section.content)

        system_text = "\n\n".join(system_parts)

        # --- User message ---
        user_parts: list[str] = []

        # Context
        for section in ir.get_sections(SectionKind.CONTEXT):
            user_parts.append(f"<context>\n{section.content}\n</context>")

        # Instructions (Claude responds well to XML tags)
        instructions = ir.get_sections(SectionKind.INSTRUCTIONS)
        if instructions:
            instr_lines = "\n".join(f"- {s.content}" for s in instructions)
            user_parts.append(f"<instructions>\n{instr_lines}\n</instructions>")

        # Output format
        for section in ir.get_sections(SectionKind.OUTPUT_FORMAT):
            user_parts.append(f"<output_format>\n{section.content}\n</output_format>")

        # Chain of thought — Claude supports <thinking> blocks
        cot_sections = ir.get_sections(SectionKind.CHAIN_OF_THOUGHT)
        if cot_sections:
            cot_text = "\n".join(s.content for s in cot_sections)
            user_parts.append(
                f"<thinking_instructions>\n{cot_text}\n"
                "Before answering, reason step by step inside <thinking> tags."
                "\n</thinking_instructions>"
            )

        # Few-shot examples
        examples = ir.get_sections(SectionKind.EXAMPLES)
        if examples:
            example_lines: list[str] = []
            for i, ex in enumerate(examples, 1):
                example_lines.append(f"<example index=\"{i}\">\n{ex.content}\n</example>")
            user_parts.append("<examples>\n" + "\n".join(example_lines) + "\n</examples>")

        # User input
        for section in ir.get_sections(SectionKind.USER_INPUT):
            user_parts.append(f"<user_input>\n{section.content}\n</user_input>")

        if user_parts:
            messages.append({
                "role": "user",
                "content": "\n\n".join(user_parts),
            })

        # --- Parameters ---
        parameters["model"] = profile.name
        parameters["max_tokens"] = ir.metadata.get("max_tokens", profile.max_output_tokens)

        temp = ir.metadata.get("temperature", profile.default_temperature)
        top_p = ir.metadata.get("top_p", profile.default_top_p)
        parameters["temperature"] = temp
        if top_p < 1.0:
            parameters["top_p"] = top_p

        if system_text:
            parameters["system"] = system_text

        # Token budget check
        estimated = ir.total_estimated_tokens()
        if estimated > profile.max_context_tokens * 0.9:
            warnings.append(
                f"Estimated token count ({estimated:,}) approaches the "
                f"context limit ({profile.max_context_tokens:,})."
            )

        # --- Flat text version ---
        flat_parts = []
        if system_text:
            flat_parts.append(f"[SYSTEM]\n{system_text}")
        for m in messages:
            flat_parts.append(f"[{m['role'].upper()}]\n{m['content']}")
        prompt_text = "\n\n".join(flat_parts)

        return CompiledPrompt(
            payload={"system": system_text, "messages": messages},
            parameters=parameters,
            prompt_text=prompt_text,
            warnings=warnings,
            model_target=profile.name,
            plugin_used=self.name(),
        )

    def format_system_prompt(self, text: str) -> str:
        return text.strip()

    def build_delimiter(self, label: str) -> str:
        return f"\n<{label.lower().replace(' ', '_')}>\n"
