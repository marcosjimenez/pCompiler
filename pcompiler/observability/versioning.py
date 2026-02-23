"""
Prompt versioning.

Computes content hashes for prompt specs and compiled results to enable
version comparison and exact reproducibility of past compilations.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PromptVersion:
    """Immutable version fingerprint of a prompt compilation."""

    spec_hash: str
    result_hash: str
    model_target: str
    spec_version: str

    def matches(self, other: "PromptVersion") -> bool:
        """Check if two versions produced the same result."""
        return self.result_hash == other.result_hash

    def spec_changed(self, other: "PromptVersion") -> bool:
        """Check if the source spec changed between versions."""
        return self.spec_hash != other.spec_hash


def compute_hash(data: dict[str, Any]) -> str:
    """Compute a stable SHA-256 hash of a dict."""
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def create_version(
    spec_dict: dict[str, Any],
    result_dict: dict[str, Any],
    model_target: str,
    spec_version: str = "1.0",
) -> PromptVersion:
    """Create a PromptVersion from the raw spec and result dicts."""
    return PromptVersion(
        spec_hash=compute_hash(spec_dict),
        result_hash=compute_hash(result_dict),
        model_target=model_target,
        spec_version=spec_version,
    )
