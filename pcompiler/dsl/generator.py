"""
Module for generating PromptSpec objects from natural language prompts using LLMs.
"""

from __future__ import annotations

import yaml
from typing import Any, Callable

from pcompiler.dsl.schema import PromptSpec


DSL_GENERATION_SYSTEM_PROMPT = """
You are an expert prompt engineer and pCompiler DSL specialist.
Your task is to take a natural language description of a prompt's purpose and convert it into a valid pCompiler DSL YAML specification.

The pCompiler DSL schema includes:
- task (required): The name of the task (e.g., summarize, classify, extract, translate, analyze, generate).
- input_type (optional): The semantic type of input data (default: "text").
- model_target (optional): The target model identifier (default: "gpt-4o").
- description (optional): A human-readable description of the prompt.
- instructions (optional): A list of objects with 'text' and 'priority' (0-100).
- constraints (optional): Includes 'max_tokens', 'tone' (formal, informal, technical, creative, neutral), 'temperature', 'top_p', 'cot_policy' (always, auto, never), 'include_risks', 'include_citations', 'include_confidence'.
- few_shot_examples (optional): A list of objects with 'input', 'output', and optional 'explanation'.
- output_schema (optional): Describes the expected JSON output format with 'type', 'properties', 'required', and 'additionalProperties'.
- security (optional): Includes 'level' (strict, moderate, permissive), 'block_code_execution', 'block_system_prompt_leak', 'block_instruction_override'.
- evals (optional): Configuration for running evaluations with 'cases' (name, input, expected, metrics).

Respond ONLY with the raw YAML content. Do not include markdown code blocks or explanations.
"""


class DslGenerator:
    """Generates PromptSpec objects from natural language prompts."""

    def __init__(self, executor: Callable[[str, str], str] | None = None) -> None:
        """
        Initialize the generator.
        
        :param executor: A callable that takes (system_prompt, user_prompt) and returns the LLM response.
                         If None, a mock executor will be used.
        """
        self.executor = executor or self._mock_executor

    def _mock_executor(self, system: str, user: str) -> str:
        """Default mock executor for when no real LLM is available."""
        # A simple heuristic to generate something somewhat relevant for the mock
        if "summarize" in user.lower():
            task = "summarize"
            instr = "Summarize the input concisely."
        elif "classify" in user.lower():
            task = "classify"
            instr = "Classify the input into categories."
        else:
            task = "generate"
            instr = "Perform the task as described."

        mock_yaml = f"""task: {task}
description: Generated from prompt: {user}
model_target: gpt-4o
instructions:
  - text: "{instr}"
    priority: 100
constraints:
  tone: neutral
  cot_policy: auto
"""
        return mock_yaml

    def generate_yaml(self, prompt: str) -> str:
        """
        Generate a YAML string representation of a PromptSpec from a prompt.
        """
        yaml_content = self.executor(DSL_GENERATION_SYSTEM_PROMPT, prompt)
        
        # Clean up the output if it accidentally contains markdown blocks
        yaml_content = yaml_content.strip()
        if yaml_content.startswith("```"):
            lines = yaml_content.splitlines()
            if lines[0].startswith("```yaml"):
                yaml_content = "\n".join(lines[1:-1])
            elif lines[0].startswith("```"):
                 yaml_content = "\n".join(lines[1:-1])

        return yaml_content

    def generate_spec(self, prompt: str) -> PromptSpec:
        """
        Generate a PromptSpec object from a prompt.
        """
        yaml_str = self.generate_yaml(prompt)
        data = yaml.safe_load(yaml_str)
        return PromptSpec.model_validate(data)
