"""
Output schema validation.

Validates that the user-provided output_schema is a well-formed JSON Schema
and checks compatibility with the target model's capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import jsonschema

from pcompiler.dsl.schema import OutputSchema
from pcompiler.models.registry import ModelProfile


@dataclass
class SchemaValidationResult:
    """Result of output schema validation."""
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_output_schema(
    schema: OutputSchema | None,
    profile: ModelProfile,
) -> SchemaValidationResult:
    """Validate the output schema against JSON Schema spec and model support."""

    result = SchemaValidationResult()

    if schema is None:
        return result

    # 1. Validate it's a well-formed JSON Schema
    schema_dict = {
        "type": schema.type,
        "properties": schema.properties,
        "required": schema.required,
        "additionalProperties": schema.additional_properties,
    }

    try:
        jsonschema.Draft7Validator.check_schema(schema_dict)
    except jsonschema.SchemaError as exc:
        result.valid = False
        result.errors.append(f"Invalid JSON Schema: {exc.message}")
        return result

    # 2. Check required fields reference existing properties
    for req in schema.required:
        if req not in schema.properties:
            result.valid = False
            result.errors.append(
                f"Required field '{req}' is not defined in properties."
            )

    # 3. Model compatibility
    if not profile.supports_json_mode:
        result.warnings.append(
            f"Model '{profile.name}' does not support native JSON mode. "
            "The output schema will be enforced via prompt instructions only."
        )

    return result
