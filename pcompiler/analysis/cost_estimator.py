"""
Cost and latency estimator for prompt compilation.

Estimates the economic cost and expected latency of executing a prompt
based on token counts and per-model pricing from the ModelRegistry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pcompiler.ir.nodes import PromptIR
from pcompiler.models.registry import ModelProfile, ModelRegistry


@dataclass
class CostEstimate:
    """Result of a cost estimation for a single model."""

    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    estimated_latency_ms: float
    currency: str = "USD"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the estimate to a dictionary."""
        return {
            "model": self.model,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "input_cost_usd": round(self.input_cost_usd, 6),
            "output_cost_usd": round(self.output_cost_usd, 6),
            "total_cost_usd": round(self.total_cost_usd, 6),
            "estimated_latency_ms": round(self.estimated_latency_ms, 1),
            "currency": self.currency,
        }


class CostEstimator:
    """Estimates cost and latency for prompt execution.

    Usage::

        estimator = CostEstimator()
        ir = ...  # a PromptIR instance
        estimate = estimator.estimate(ir, "gpt-4o")
        print(f"Estimated cost: ${estimate.total_cost_usd:.4f}")
    """

    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self.registry = registry or ModelRegistry()

    def estimate(
        self,
        ir: PromptIR,
        model_name: str,
        *,
        expected_output_tokens: int | None = None,
    ) -> CostEstimate:
        """Estimate cost and latency for a prompt on the given model.

        Args:
            ir: The intermediate representation of the prompt.
            model_name: Target model identifier.
            expected_output_tokens: Expected output token count.
                If ``None``, uses the model's ``max_output_tokens``.

        Returns:
            A :class:`CostEstimate` with the breakdown.

        Raises:
            KeyError: If the model is not found in the registry.
        """
        profile = self.registry.get(model_name)
        return self._estimate_for_profile(ir, profile, expected_output_tokens)

    def compare(
        self,
        ir: PromptIR,
        model_names: list[str] | None = None,
        *,
        expected_output_tokens: int | None = None,
    ) -> list[CostEstimate]:
        """Compare cost estimates across multiple models.

        Args:
            ir: The intermediate representation of the prompt.
            model_names: Models to compare. If ``None``, compares all
                registered models.
            expected_output_tokens: Expected output token count (shared
                across all models for fair comparison).

        Returns:
            A list of :class:`CostEstimate` sorted by total cost (cheapest first).
        """
        if model_names is None:
            model_names = self.registry.list_models()

        estimates = []
        for name in model_names:
            profile = self.registry.get(name)
            est = self._estimate_for_profile(ir, profile, expected_output_tokens)
            estimates.append(est)

        return sorted(estimates, key=lambda e: e.total_cost_usd)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _estimate_for_profile(
        self,
        ir: PromptIR,
        profile: ModelProfile,
        expected_output_tokens: int | None,
    ) -> CostEstimate:
        """Core estimation logic."""
        input_tokens = ir.total_estimated_tokens()
        output_tokens = (
            expected_output_tokens
            if expected_output_tokens is not None
            else profile.max_output_tokens
        )

        # Prices are per million tokens
        input_cost = (input_tokens / 1_000_000) * profile.input_price_per_mtok
        output_cost = (output_tokens / 1_000_000) * profile.output_price_per_mtok

        latency_ms = output_tokens * profile.avg_latency_ms_per_output_token

        return CostEstimate(
            model=profile.name,
            provider=profile.provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost_usd=input_cost,
            output_cost_usd=output_cost,
            total_cost_usd=input_cost + output_cost,
            estimated_latency_ms=latency_ms,
        )
