"""
Orchestrates context retrieval, ranking, and pruning.
"""

from __future__ import annotations

from typing import Any

from pcompiler.dsl.schema import ContextConfig, ContextSource, ContextSourceType
from pcompiler.plugins.context import ContextProvider, MockVectorStoreProvider


class ContextManager:
    """Manages retrieval and processing of dynamic context."""

    def __init__(self) -> None:
        self._providers: dict[str, ContextProvider] = {}
        # Register default mock provider for now
        self.register_provider(MockVectorStoreProvider())
        self.register_provider(MockVectorStoreProvider(), name="vector_store")

    def register_provider(self, provider: ContextProvider, name: str | None = None) -> None:
        """Register a context provider."""
        self._providers[name or provider.name()] = provider

    def resolve_context(self, config: ContextConfig | str) -> str:
        """Fetch and merge all context sources defined in the config."""
        if isinstance(config, str):
            return config

        snippets: list[tuple[str, int]] = []  # (text, priority)

        for source in config.sources:
            text = self._resolve_source(source)
            if text:
                snippets.append((text, source.priority))

        if not snippets:
            return ""

        # Formatting and merging
        if config.combine_strategy == "ranked":
            # Sort by priority descending
            snippets.sort(key=lambda x: x[1], reverse=True)

        merged_text = "\n\n".join(s[0] for s in snippets)

        # TODO: Implement token-aware pruning if config.max_total_tokens is set
        if config.max_total_tokens:
            # Simple character-based approximation for now, 
            # ideally use a tokenizer plugin
            limit = config.max_total_tokens * 4
            if len(merged_text) > limit:
                merged_text = merged_text[:limit] + "..."

        return merged_text

    def _resolve_source(self, source: ContextSource) -> str | None:
        """Resolve a single context source based on its type."""
        if source.type == ContextSourceType.STATIC:
            return source.value

        if source.type == ContextSourceType.LOCAL_FILE:
            return self._resolve_local_file(source)

        if source.type == ContextSourceType.VECTOR_STORE:
            provider = self._providers.get("vector_store")
            if provider:
                return provider.retrieve(source.query or "", source.config)
            return f"[Error: No vector_store provider registered]"

        if source.type == ContextSourceType.WEB_SEARCH:
            provider = self._providers.get("web_search")
            if provider:
                return provider.retrieve(source.query or "", source.config)
            return f"[Error: No web_search provider registered]"

        return None

    def _resolve_local_file(self, source: ContextSource) -> str | None:
        """Read context from a local file."""
        if not source.value:
            return None
        try:
            with open(source.value, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            # We might want to add this to tracing later
            return f"[Error loading context from {source.value}: {e}]"
