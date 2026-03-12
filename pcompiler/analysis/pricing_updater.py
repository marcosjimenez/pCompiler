"""
Pricing updater for model configurations.

Maintains reference pricing data for known models and can update
``config.json`` with the latest prices automatically.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PriceChange:
    """A single pricing change for a model."""

    model: str
    provider: str
    field: str
    old_value: float
    new_value: float


@dataclass
class UpdateResult:
    """Summary of a pricing update operation."""

    updated_models: list[str] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)
    changes: list[PriceChange] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return len(self.changes)


# ---------------------------------------------------------------------------
# Reference pricing data (USD per million tokens)
# ---------------------------------------------------------------------------
# Keep this dictionary up-to-date with the latest public pricing.
# Structured as: provider -> model -> {input, output, latency}

_REFERENCE_PRICING: dict[str, dict[str, dict[str, float]]] = {
    "openai": {
        "gpt-5.3": {
            "input_price_per_mtok": 5.00,
            "output_price_per_mtok": 20.00,
            "avg_latency_ms_per_output_token": 12,
        },
        "gpt-5.2": {
            "input_price_per_mtok": 3.00,
            "output_price_per_mtok": 15.00,
            "avg_latency_ms_per_output_token": 14,
        },
        "gpt-5.1": {
            "input_price_per_mtok": 2.50,
            "output_price_per_mtok": 10.00,
            "avg_latency_ms_per_output_token": 15,
        },
        "gpt-4.1": {
            "input_price_per_mtok": 2.00,
            "output_price_per_mtok": 8.00,
            "avg_latency_ms_per_output_token": 18,
        },
        "gpt-4o": {
            "input_price_per_mtok": 2.50,
            "output_price_per_mtok": 10.00,
            "avg_latency_ms_per_output_token": 18,
        },
        "gpt-4o-mini": {
            "input_price_per_mtok": 0.15,
            "output_price_per_mtok": 0.60,
            "avg_latency_ms_per_output_token": 10,
        },
    },
    "anthropic": {
        "claude-opus-4.6": {
            "input_price_per_mtok": 15.00,
            "output_price_per_mtok": 75.00,
            "avg_latency_ms_per_output_token": 25,
        },
        "claude-sonnet-4.5": {
            "input_price_per_mtok": 3.00,
            "output_price_per_mtok": 15.00,
            "avg_latency_ms_per_output_token": 20,
        },
        "claude-haiku-4.5": {
            "input_price_per_mtok": 0.80,
            "output_price_per_mtok": 4.00,
            "avg_latency_ms_per_output_token": 12,
        },
    },
    "google": {
        "gemini-3-pro": {
            "input_price_per_mtok": 1.25,
            "output_price_per_mtok": 5.00,
            "avg_latency_ms_per_output_token": 16,
        },
        "gemini-2.5-pro": {
            "input_price_per_mtok": 1.25,
            "output_price_per_mtok": 10.00,
            "avg_latency_ms_per_output_token": 18,
        },
        "gemini-2.5-flash": {
            "input_price_per_mtok": 0.15,
            "output_price_per_mtok": 0.60,
            "avg_latency_ms_per_output_token": 8,
        },
    },
    "mistral": {
        "mistral-large-3": {
            "input_price_per_mtok": 2.00,
            "output_price_per_mtok": 6.00,
            "avg_latency_ms_per_output_token": 15,
        },
        "ministral-3-14b": {
            "input_price_per_mtok": 0.10,
            "output_price_per_mtok": 0.10,
            "avg_latency_ms_per_output_token": 8,
        },
        "ministral-3-8b": {
            "input_price_per_mtok": 0.10,
            "output_price_per_mtok": 0.10,
            "avg_latency_ms_per_output_token": 6,
        },
        "ministral-3-3b": {
            "input_price_per_mtok": 0.04,
            "output_price_per_mtok": 0.04,
            "avg_latency_ms_per_output_token": 5,
        },
        "mixtral-8x22b": {
            "input_price_per_mtok": 2.00,
            "output_price_per_mtok": 6.00,
            "avg_latency_ms_per_output_token": 20,
        },
        "mixtral-8x7b": {
            "input_price_per_mtok": 0.70,
            "output_price_per_mtok": 0.70,
            "avg_latency_ms_per_output_token": 12,
        },
    },
}

_PRICING_FIELDS = [
    "input_price_per_mtok",
    "output_price_per_mtok",
    "avg_latency_ms_per_output_token",
]


class PricingUpdater:
    """Updates config.json with the latest reference pricing data.

    Usage::

        updater = PricingUpdater()
        result = updater.update_config(Path("config.json"))
        print(f"Updated {len(result.updated_models)} models")
    """

    def __init__(
        self,
        reference_pricing: dict[str, dict[str, dict[str, float]]] | None = None,
    ) -> None:
        self._pricing = reference_pricing or _REFERENCE_PRICING

    def get_latest_prices(self) -> dict[str, dict[str, dict[str, float]]]:
        """Return the current reference pricing data.

        Returns:
            Nested dict: ``provider -> model -> pricing_fields``.
        """
        return dict(self._pricing)

    def update_config(
        self,
        config_path: Path,
        *,
        dry_run: bool = False,
    ) -> UpdateResult:
        """Read config.json, update pricing fields, and optionally save.

        Args:
            config_path: Path to the config JSON file.
            dry_run: If ``True``, compute changes but do not write the file.

        Returns:
            An :class:`UpdateResult` summarising what changed.

        Raises:
            FileNotFoundError: If *config_path* does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        result = UpdateResult()

        for provider, models in data.items():
            if not isinstance(models, list):
                continue

            provider_prices = self._pricing.get(provider, {})

            for model_entry in models:
                model_name = model_entry.get("name", "")
                if model_name in provider_prices:
                    ref = provider_prices[model_name]
                    updated = False

                    for pricing_field in _PRICING_FIELDS:
                        old_val = model_entry.get(pricing_field, 0.0)
                        new_val = ref.get(pricing_field, 0.0)

                        if old_val != new_val:
                            result.changes.append(PriceChange(
                                model=model_name,
                                provider=provider,
                                field=pricing_field,
                                old_value=old_val,
                                new_value=new_val,
                            ))
                            model_entry[pricing_field] = new_val
                            updated = True
                        elif pricing_field not in model_entry:
                            # Field missing entirely — add it
                            model_entry[pricing_field] = new_val
                            updated = True

                    if updated and model_name not in result.updated_models:
                        result.updated_models.append(model_name)
                else:
                    if model_name and model_name not in result.not_found:
                        result.not_found.append(model_name)

        if not dry_run and (result.total_changes > 0 or result.updated_models):
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.write("\n")

        return result
