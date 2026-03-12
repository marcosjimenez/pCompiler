"""
Model profiles and a registry that maps model identifiers to their
capabilities and optimal default parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True)
class ModelProfile:
    """Describes a specific LLM's capabilities and defaults."""

    name: str
    provider: str
    max_context_tokens: int
    max_output_tokens: int
    supports_system_prompt: bool = True
    supports_json_mode: bool = False
    supports_function_calling: bool = False
    supports_vision: bool = False
    default_temperature: float = 0.7
    default_top_p: float = 1.0
    input_price_per_mtok: float = 0.0
    output_price_per_mtok: float = 0.0
    avg_latency_ms_per_output_token: float = 0.0
    optimal_section_order: list[str] = field(default_factory=lambda: [
        "SECURITY_PREAMBLE", "SYSTEM", "CONTEXT", "INSTRUCTIONS",
        "EXAMPLES", "OUTPUT_FORMAT", "CHAIN_OF_THOUGHT", "USER_INPUT",
    ])
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Built-in profiles
# ---------------------------------------------------------------------------

_BUILTIN_PROFILES: dict[str, ModelProfile] = {
    "gpt-4o": ModelProfile(
        name="gpt-4o",
        provider="openai",
        max_context_tokens=128_000,
        max_output_tokens=16_384,
        supports_system_prompt=True,
        supports_json_mode=True,
        supports_function_calling=True,
        supports_vision=True,
        default_temperature=0.7,
    ),
    "gpt-4o-mini": ModelProfile(
        name="gpt-4o-mini",
        provider="openai",
        max_context_tokens=128_000,
        max_output_tokens=16_384,
        supports_system_prompt=True,
        supports_json_mode=True,
        supports_function_calling=True,
        supports_vision=True,
        default_temperature=0.7,
    ),
    "claude-3.5-sonnet": ModelProfile(
        name="claude-3.5-sonnet",
        provider="anthropic",
        max_context_tokens=200_000,
        max_output_tokens=8_192,
        supports_system_prompt=True,
        supports_json_mode=False,
        supports_function_calling=True,
        supports_vision=True,
        default_temperature=0.7,
        extra={"thinking_tags": True},
    ),
    "claude-3-opus": ModelProfile(
        name="claude-3-opus",
        provider="anthropic",
        max_context_tokens=200_000,
        max_output_tokens=4_096,
        supports_system_prompt=True,
        supports_json_mode=False,
        supports_function_calling=True,
        supports_vision=True,
        default_temperature=0.7,
        extra={"thinking_tags": True},
    ),
    "gemini-1.5-pro": ModelProfile(
        name="gemini-1.5-pro",
        provider="google",
        max_context_tokens=1_000_000,
        max_output_tokens=8_192,
        supports_system_prompt=True,
        supports_json_mode=True,
        supports_function_calling=True,
        supports_vision=True,
        default_temperature=0.7,
        extra={"response_mime_type": "application/json"},
    ),
    "gemini-2.0-flash": ModelProfile(
        name="gemini-2.0-flash",
        provider="google",
        max_context_tokens=1_000_000,
        max_output_tokens=8_192,
        supports_system_prompt=True,
        supports_json_mode=True,
        supports_function_calling=True,
        supports_vision=True,
        default_temperature=0.7,
        extra={"response_mime_type": "application/json"},
    ),
}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class ModelRegistry:
    """Singleton-style registry of model profiles.

    Usage::

        registry = ModelRegistry()
        profile = registry.get("gpt-4o")
    """

    _instance: ModelRegistry | None = None
    _profiles: dict[str, ModelProfile]

    def __new__(cls) -> ModelRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._profiles = cls._load_profiles()
        return cls._instance

    @classmethod
    def _load_profiles(cls) -> dict[str, ModelProfile]:
        profiles = dict(_BUILTIN_PROFILES)
        config_path = Path("config.json")
        
        if config_path.is_file():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if isinstance(data, dict):
                    loaded_profiles = {}
                    for provider, models in data.items():
                        if isinstance(models, list):
                            for item in models:
                                item_dict = cast(dict[str, Any], item)
                                item_dict["provider"] = provider
                                profile = ModelProfile(**item_dict)
                                loaded_profiles[profile.name] = profile
                    if loaded_profiles:
                        profiles = loaded_profiles
            except Exception:
                pass
                
        return profiles

    # -- public API --------------------------------------------------------

    def get(self, name: str) -> ModelProfile:
        """Return the profile for *name*, or raise ``KeyError``."""
        if name not in self._profiles:
            available = ", ".join(sorted(self._profiles))
            raise KeyError(
                f"Unknown model '{name}'. Available: {available}"
            )
        return self._profiles[name]

    def register(self, profile: ModelProfile) -> None:
        """Register (or overwrite) a model profile."""
        self._profiles[profile.name] = profile

    def list_models(self) -> list[str]:
        """Return sorted list of registered model names."""
        return sorted(self._profiles)

    def list_providers(self) -> list[str]:
        """Return unique sorted provider names."""
        return sorted({p.provider for p in self._profiles.values()})

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (useful in tests)."""
        cls._instance = None
