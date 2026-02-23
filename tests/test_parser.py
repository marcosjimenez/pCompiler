"""Tests for DSL parser and schema validation."""

import pytest

from pcompiler.dsl.parser import ParseError, parse_string
from pcompiler.dsl.schema import CoTPolicy, PromptSpec, Tone


class TestParseString:
    """Tests for parse_string()."""

    def test_minimal_spec(self):
        spec = parse_string("task: summarize")
        assert spec.task == "summarize"
        assert spec.model_target == "gpt-4o"  # default
        assert spec.constraints.tone == Tone.NEUTRAL

    def test_full_spec(self):
        yaml_str = """
task: classify
input_type: customer_feedback
model_target: claude-3.5-sonnet
constraints:
  max_tokens: 200
  tone: formal
  temperature: 0.3
  cot_policy: always
instructions:
  - text: "Classify the text."
    priority: 80
few_shot_examples:
  - input: "Great product!"
    output: "positive"
output_schema:
  type: object
  properties:
    label:
      type: string
  required:
    - label
security:
  level: strict
"""
        spec = parse_string(yaml_str)
        assert spec.task == "classify"
        assert spec.model_target == "claude-3.5-sonnet"
        assert spec.constraints.max_tokens == 200
        assert spec.constraints.tone == Tone.FORMAL
        assert spec.constraints.temperature == 0.3
        assert spec.constraints.cot_policy == CoTPolicy.ALWAYS
        assert len(spec.instructions) == 1
        assert spec.instructions[0].priority == 80
        assert len(spec.few_shot_examples) == 1
        assert spec.output_schema is not None
        assert spec.output_schema.required == ["label"]
        assert spec.security.level.value == "strict"

    def test_invalid_yaml(self):
        with pytest.raises(ParseError, match="Invalid YAML"):
            parse_string("{{{{invalid: [")

    def test_non_dict_yaml(self):
        with pytest.raises(ParseError, match="mapping"):
            parse_string("- just\n- a\n- list")

    def test_missing_task(self):
        with pytest.raises(ParseError, match="task"):
            parse_string("input_type: text")

    def test_invalid_tone(self):
        with pytest.raises(ParseError):
            parse_string("task: x\nconstraints:\n  tone: screaming")

    def test_temperature_out_of_range(self):
        with pytest.raises(ParseError):
            parse_string("task: x\nconstraints:\n  temperature: 5.0")

    def test_empty_instruction_text(self):
        with pytest.raises(ParseError):
            parse_string('task: x\ninstructions:\n  - text: ""')

    def test_default_security_policy(self):
        spec = parse_string("task: test")
        assert spec.security.level.value == "moderate"
        assert spec.security.block_code_execution is True

    def test_tags_and_version(self):
        spec = parse_string("task: t\nversion: '2.0'\ntags:\n  - a\n  - b")
        assert spec.version == "2.0"
        assert spec.tags == ["a", "b"]
