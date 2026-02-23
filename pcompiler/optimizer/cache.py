"""
Subprompt caching / memoization.

Caches compiled prompts by hashing the (spec + target) key, so that
repeated compilations of the same spec skip the pipeline.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from typing import Any

from pcompiler.plugins.base import CompiledPrompt


class PromptCache:
    """LRU-style in-memory cache for compiled prompts.

    Usage::

        cache = PromptCache(max_size=128)
        key = cache.make_key(spec_dict, "gpt-4o")
        hit = cache.get(key)
        if hit is None:
            result = compiler.compile(...)
            cache.put(key, result)
    """

    def __init__(self, max_size: int = 256) -> None:
        self._max_size = max_size
        self._store: OrderedDict[str, CompiledPrompt] = OrderedDict()
        self._hits = 0
        self._misses = 0

    # -- Key generation ----------------------------------------------------

    @staticmethod
    def make_key(spec_dict: dict[str, Any], target: str) -> str:
        """Produce a SHA-256 hash key for a (spec, target) pair."""
        canonical = json.dumps(spec_dict, sort_keys=True, default=str) + "|" + target
        return hashlib.sha256(canonical.encode()).hexdigest()

    # -- Cache ops ---------------------------------------------------------

    def get(self, key: str) -> CompiledPrompt | None:
        """Retrieve a cached result (and promote it in the LRU)."""
        if key in self._store:
            self._store.move_to_end(key)
            self._hits += 1
            return self._store[key]
        self._misses += 1
        return None

    def put(self, key: str, value: CompiledPrompt) -> None:
        """Store a compiled prompt. Evicts oldest entry if full."""
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def invalidate(self, key: str) -> None:
        """Remove a specific key from the cache."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Clear the entire cache."""
        self._store.clear()
        self._hits = 0
        self._misses = 0

    # -- Stats -------------------------------------------------------------

    @property
    def size(self) -> int:
        return len(self._store)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 4),
        }
