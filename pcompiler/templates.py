"""
Template engine wrapper for Jinja2.
"""

from __future__ import annotations

from typing import Any
from jinja2 import Environment, StrictUndefined, TemplateError


class TemplateEngine:
    """
    Wrapper around Jinja2 for rendering prompt templates.
    """

    def __init__(self) -> None:
        # We use StrictUndefined to raise errors if a variable is missing
        self.env = Environment(undefined=StrictUndefined)

    def render(self, template_str: str, context: dict[str, Any]) -> str:
        """
        Render a Jinja2 template string with the given context.

        Args:
            template_str: The template string (e.g. "Hello {{ name }}").
            context: Variables to inject.

        Returns:
            The rendered string.

        Raises:
            TemplateError: If rendering fails (e.g. missing variable, syntax error).
        """
        try:
            template = self.env.from_string(template_str)
            return template.render(**context)
        except TemplateError as e:
            # Re-raise or wrap if we want custom error handling
            raise e
