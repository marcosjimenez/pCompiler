"""
Google backend plugin — compiles prompts for Gemini models.

Generates the Gemini API content format with parts, system instruction
support, and response_mime_type for JSON enforcement.
"""

from __future__ import annotations

from typing import Any

from pcompiler.ir.nodes import PromptIR, SectionKind
from pcompiler.models.registry import ModelProfile
from pcompiler.plugins.base import BackendPlugin, CompiledPrompt


class GooglePlugin(BackendPlugin):
    """Backend plugin for Google Gemini models."""

    def name(self) -> str:
        return "google"

    def emit(self, ir: PromptIR, profile: ModelProfile) -> CompiledPrompt:
        system_instruction = ""
        contents: list[dict[str, Any]] = []
        parameters: dict[str, Any] = {}
        generation_config: dict[str, Any] = {}
        warnings: list[str] = []

        # --- System instruction (Gemini supports it natively) ---
        system_parts: list[str] = []
        for section in ir.sections:
            if section.kind == SectionKind.SECURITY_PREAMBLE:
                system_parts.append(section.content)
            elif section.kind == SectionKind.SYSTEM:
                system_parts.append(section.content)

        system_instruction = "\n\n".join(system_parts)

        # --- User content ---
        user_parts: list[str] = []

        # Context
        for section in ir.get_sections(SectionKind.CONTEXT):
            user_parts.append(f"**Context:**\n{section.content}")

        # Instructions
        instructions = ir.get_sections(SectionKind.INSTRUCTIONS)
        if instructions:
            instr_text = "\n".join(f"• {s.content}" for s in instructions)
            user_parts.append(f"**Instructions:**\n{instr_text}")

        # Output format
        for section in ir.get_sections(SectionKind.OUTPUT_FORMAT):
            user_parts.append(f"**Output Format:**\n{section.content}")

        # Chain of thought
        for section in ir.get_sections(SectionKind.CHAIN_OF_THOUGHT):
            user_parts.append(
                f"**Reasoning:**\n{section.content}\n"
                "Think step by step before providing your answer."
            )

        # Few-shot examples
        examples = ir.get_sections(SectionKind.EXAMPLES)
        if examples:
            example_lines = ["**Examples:**"]
            for i, ex in enumerate(examples, 1):
                example_lines.append(f"\n*Example {i}:*\n{ex.content}")
            user_parts.append("\n".join(example_lines))

        # User input
        for section in ir.get_sections(SectionKind.USER_INPUT):
            user_parts.append(f"**Input:**\n{section.content}")

        if user_parts:
            contents.append({
                "role": "user",
                "parts": [{"text": "\n\n".join(user_parts)}],
            })

        # --- Generation config ---
        temp = ir.metadata.get("temperature", profile.default_temperature)
        top_p = ir.metadata.get("top_p", profile.default_top_p)
        generation_config["temperature"] = temp
        generation_config["topP"] = top_p

        max_tokens = ir.metadata.get("max_tokens")
        if max_tokens:
            generation_config["maxOutputTokens"] = max_tokens

        # JSON mode via response_mime_type
        output_schema = ir.metadata.get("output_schema")
        if output_schema and profile.supports_json_mode:
            generation_config["responseMimeType"] = "application/json"

        parameters["model"] = profile.name
        parameters["generationConfig"] = generation_config
        if system_instruction:
            parameters["systemInstruction"] = {
                "parts": [{"text": system_instruction}],
            }

        # Token budget check
        estimated = ir.total_estimated_tokens()
        if estimated > profile.max_context_tokens * 0.9:
            warnings.append(
                f"Estimated token count ({estimated:,}) approaches the "
                f"context limit ({profile.max_context_tokens:,})."
            )

        # --- Flat text version ---
        flat_parts = []
        if system_instruction:
            flat_parts.append(f"[SYSTEM INSTRUCTION]\n{system_instruction}")
        for c in contents:
            role = c["role"].upper()
            text = "\n".join(p["text"] for p in c["parts"])
            flat_parts.append(f"[{role}]\n{text}")
        prompt_text = "\n\n".join(flat_parts)

        return CompiledPrompt(
            payload={"contents": contents, "systemInstruction": system_instruction},
            parameters=parameters,
            prompt_text=prompt_text,
            warnings=warnings,
            model_target=profile.name,
            plugin_used=self.name(),
        )
