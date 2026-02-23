"""
Plugin system for model-specific backends.

Provides the ``BackendPlugin`` abstract base class and ``PluginManager``
for discovering, loading and dispatching to the correct backend.
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

if sys.version_info >= (3, 12):
    from importlib.metadata import entry_points
else:
    from importlib.metadata import entry_points

from pcompiler.ir.nodes import PromptIR
from pcompiler.models.registry import ModelProfile


# ---------------------------------------------------------------------------
# Compiled output
# ---------------------------------------------------------------------------

@dataclass
class CompiledPrompt:
    """The final output of the compilation pipeline."""

    # Model-specific payload (messages list, string, etc.)
    payload: Any

    # Recommended API parameters
    parameters: dict[str, Any] = field(default_factory=dict)

    # Human-readable, flat-text version of the prompt
    prompt_text: str = ""

    # Warnings emitted during compilation
    warnings: list[str] = field(default_factory=list)

    # Compilation trace (populated by the observability layer)
    trace: dict[str, Any] = field(default_factory=dict)

    # Metadata
    model_target: str = ""
    plugin_used: str = ""


# ---------------------------------------------------------------------------
# BackendPlugin ABC
# ---------------------------------------------------------------------------

class BackendPlugin(ABC):
    """Abstract base class that every model backend must implement."""

    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this plugin (e.g. ``'openai'``)."""

    @abstractmethod
    def supported_models(self) -> list[str]:
        """List of model identifiers this plugin can handle."""

    @abstractmethod
    def emit(self, ir: PromptIR, profile: ModelProfile) -> CompiledPrompt:
        """Transform an IR into a model-specific compiled prompt."""

    # -- Optional helpers (with defaults) ----------------------------------

    def format_system_prompt(self, text: str) -> str:
        """Format a system prompt string (override for model quirks)."""
        return text.strip()

    def format_few_shot(self, examples: list[dict[str, str]]) -> list[dict[str, str]]:
        """Format few-shot examples (override if the model needs special tags)."""
        return examples

    def build_delimiter(self, label: str) -> str:
        """Build a delimiter / separator string."""
        return f"\n--- {label} ---\n"


# ---------------------------------------------------------------------------
# PluginManager
# ---------------------------------------------------------------------------

class PluginManager:
    """Discovers, loads and dispatches backend plugins.

    Plugins are discovered via:
    1. Python ``entry_points(group='pcompiler.plugins')``
    2. Manual registration with :meth:`register`
    """

    def __init__(self, *, auto_discover: bool = True) -> None:
        self._plugins: dict[str, BackendPlugin] = {}
        self._model_map: dict[str, str] = {}  # model_name → plugin_name
        if auto_discover:
            self._discover()

    # -- Discovery ---------------------------------------------------------

    def _discover(self) -> None:
        """Load plugins from installed entry points."""
        try:
            eps = entry_points(group="pcompiler.plugins")
        except TypeError:
            # Python < 3.12 fallback
            eps = entry_points().get("pcompiler.plugins", [])

        for ep in eps:
            try:
                plugin_cls = ep.load()
                if isinstance(plugin_cls, type) and issubclass(plugin_cls, BackendPlugin):
                    self.register(plugin_cls())
            except Exception:
                # Don't crash on broken third-party plugins
                pass

    # -- Registration ------------------------------------------------------

    def register(self, plugin: BackendPlugin) -> None:
        """Register a plugin instance."""
        name = plugin.name()
        self._plugins[name] = plugin
        for model in plugin.supported_models():
            self._model_map[model.lower()] = name

    # -- Lookup ------------------------------------------------------------

    def get_plugin_for_model(self, model_name: str) -> BackendPlugin:
        """Return the plugin that handles *model_name*.

        Raises:
            KeyError: If no plugin supports the requested model.
        """
        key = model_name.lower()
        if key not in self._model_map:
            available = ", ".join(sorted(self._model_map))
            raise KeyError(
                f"No plugin registered for model '{model_name}'. "
                f"Available models: {available}"
            )
        return self._plugins[self._model_map[key]]

    def get_plugin(self, plugin_name: str) -> BackendPlugin:
        """Return a plugin by its name."""
        if plugin_name not in self._plugins:
            available = ", ".join(sorted(self._plugins))
            raise KeyError(
                f"Plugin '{plugin_name}' not found. Available: {available}"
            )
        return self._plugins[plugin_name]

    def list_plugins(self) -> list[str]:
        """Return sorted list of registered plugin names."""
        return sorted(self._plugins)

    def list_supported_models(self) -> list[str]:
        """Return sorted list of all supported model identifiers."""
        return sorted(self._model_map)
