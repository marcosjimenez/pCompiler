"""
YAML parser that reads DSL files and produces validated PromptSpec objects.
"""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

import yaml
from pydantic import ValidationError

from pcompiler.dsl.schema import PromptSpec


class ParseError(Exception):
    """Raised when a DSL file cannot be parsed or validated."""

    def __init__(self, message: str, errors: list[dict] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


def parse_string(yaml_str: str) -> PromptSpec:
    """Parse a YAML string into a validated :class:`PromptSpec`.

    Raises:
        ParseError: If the YAML is malformed or fails Pydantic validation.
    """
    try:
        raw = yaml.safe_load(yaml_str)
    except yaml.YAMLError as exc:
        raise ParseError(f"Invalid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise ParseError("DSL document must be a YAML mapping (dict) at the top level.")

    try:
        return PromptSpec.model_validate(raw)
    except ValidationError as exc:
        friendly = [
            {
                "field": " → ".join(str(p) for p in e["loc"]),
                "message": e["msg"],
                "type": e["type"],
            }
            for e in exc.errors()
        ]
        raise ParseError(
            f"Validation failed with {len(friendly)} error(s):\n"
            + "\n".join(f"  • {err['field']}: {err['message']}" for err in friendly),
            errors=friendly,
        ) from exc


def parse_file(path: str | Path) -> PromptSpec:
    """Parse a YAML file into a validated :class:`PromptSpec`.

    Raises:
        ParseError: If the file cannot be read or contains invalid DSL.
        FileNotFoundError: If *path* does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"DSL file not found: {path}")
    return parse_string(path.read_text(encoding="utf-8"))


def parse_stream(stream: TextIO) -> PromptSpec:
    """Parse from an open file-like stream."""
    return parse_string(stream.read())
