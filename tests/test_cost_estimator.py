"""Tests for the cost estimator and pricing updater modules."""

import json
import pytest
from pathlib import Path

from pcompiler.ir.nodes import PromptIR, SectionKind
from pcompiler.models.registry import ModelProfile, ModelRegistry
from pcompiler.analysis.cost_estimator import CostEstimate, CostEstimator
from pcompiler.analysis.pricing_updater import PricingUpdater, UpdateResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the ModelRegistry singleton before each test."""
    ModelRegistry.reset()
    yield
    ModelRegistry.reset()


@pytest.fixture
def registry():
    return ModelRegistry()


@pytest.fixture
def sample_ir():
    """A simple IR with known token count."""
    ir = PromptIR(task="test", model_target="gpt-4o")
    # ~100 tokens each (400 chars / 4 = 100 tokens)
    ir.add(SectionKind.SYSTEM, "A" * 400)
    ir.add(SectionKind.USER_INPUT, "B" * 400)
    return ir


# ---------------------------------------------------------------------------
# CostEstimator tests
# ---------------------------------------------------------------------------

class TestCostEstimate:
    def test_to_dict(self):
        est = CostEstimate(
            model="test-model",
            provider="test",
            input_tokens=1000,
            output_tokens=500,
            input_cost_usd=0.0025,
            output_cost_usd=0.005,
            total_cost_usd=0.0075,
            estimated_latency_ms=5000.0,
        )
        d = est.to_dict()
        assert d["model"] == "test-model"
        assert d["provider"] == "test"
        assert d["input_tokens"] == 1000
        assert d["output_tokens"] == 500
        assert d["total_cost_usd"] == 0.0075
        assert d["currency"] == "USD"


class TestCostEstimator:
    def test_basic_estimate(self, registry, sample_ir):
        """Verify cost calculation with known tokens and pricing."""
        estimator = CostEstimator(registry)
        est = estimator.estimate(sample_ir, "gpt-4o", expected_output_tokens=1000)

        assert est.model == "gpt-4o"
        assert est.provider == "openai"
        assert est.input_tokens == 200  # 800 chars / 4
        assert est.output_tokens == 1000

        # Input: 200 / 1M * 2.50 = 0.0005
        assert est.input_cost_usd == pytest.approx(200 / 1_000_000 * 2.50)
        # Output: 1000 / 1M * 10.00 = 0.01
        assert est.output_cost_usd == pytest.approx(1000 / 1_000_000 * 10.00)
        assert est.total_cost_usd == pytest.approx(est.input_cost_usd + est.output_cost_usd)

    def test_default_output_tokens(self, registry, sample_ir):
        """Without expected_output_tokens, uses model's max_output_tokens."""
        estimator = CostEstimator(registry)
        profile = registry.get("gpt-4o")
        est = estimator.estimate(sample_ir, "gpt-4o")

        assert est.output_tokens == profile.max_output_tokens

    def test_custom_output_tokens(self, registry, sample_ir):
        """Custom output tokens override the default."""
        estimator = CostEstimator(registry)
        est = estimator.estimate(sample_ir, "gpt-4o", expected_output_tokens=500)
        assert est.output_tokens == 500

    def test_latency_estimate(self, registry, sample_ir):
        """Verify latency is output_tokens * avg_latency_ms_per_output_token."""
        estimator = CostEstimator(registry)
        est = estimator.estimate(sample_ir, "gpt-4o", expected_output_tokens=100)
        profile = registry.get("gpt-4o")
        expected_latency = 100 * profile.avg_latency_ms_per_output_token
        assert est.estimated_latency_ms == pytest.approx(expected_latency)

    def test_zero_price_model(self, registry, sample_ir):
        """A model with 0.0 pricing returns 0 cost."""
        registry.register(ModelProfile(
            name="free-model",
            provider="test",
            max_context_tokens=8000,
            max_output_tokens=2000,
            input_price_per_mtok=0.0,
            output_price_per_mtok=0.0,
        ))
        estimator = CostEstimator(registry)
        est = estimator.estimate(sample_ir, "free-model", expected_output_tokens=100)
        assert est.total_cost_usd == 0.0

    def test_compare_returns_sorted(self, registry, sample_ir):
        """compare() returns estimates sorted by total cost ascending."""
        estimator = CostEstimator(registry)
        models = registry.list_models()
        estimates = estimator.compare(sample_ir, models, expected_output_tokens=500)

        assert len(estimates) == len(models)
        # Sorted by cost
        for i in range(len(estimates) - 1):
            assert estimates[i].total_cost_usd <= estimates[i + 1].total_cost_usd

    def test_compare_all_models_default(self, registry, sample_ir):
        """compare() without model list uses all registered models."""
        estimator = CostEstimator(registry)
        estimates = estimator.compare(sample_ir, expected_output_tokens=500)
        assert len(estimates) == len(registry.list_models())

    def test_unknown_model_raises(self, registry, sample_ir):
        """Estimating for unknown model raises KeyError."""
        estimator = CostEstimator(registry)
        with pytest.raises(KeyError, match="Unknown model"):
            estimator.estimate(sample_ir, "nonexistent-model")


# ---------------------------------------------------------------------------
# PricingUpdater tests
# ---------------------------------------------------------------------------

class TestPricingUpdater:
    def test_get_latest_prices(self):
        """get_latest_prices returns pricing for all providers."""
        updater = PricingUpdater()
        prices = updater.get_latest_prices()
        assert "openai" in prices
        assert "anthropic" in prices
        assert "google" in prices
        assert "mistral" in prices
        # Each provider has models
        assert len(prices["openai"]) > 0

    def test_update_config(self, tmp_path):
        """update_config writes updated pricing to config file."""
        config_path = tmp_path / "config.json"
        config_data = {
            "openai": [
                {
                    "name": "gpt-4o",
                    "max_context_tokens": 128000,
                    "input_price_per_mtok": 0.0,
                    "output_price_per_mtok": 0.0,
                    "avg_latency_ms_per_output_token": 0.0,
                }
            ]
        }
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        updater = PricingUpdater()
        result = updater.update_config(config_path)

        assert "gpt-4o" in result.updated_models
        assert result.total_changes > 0

        # Verify file was updated
        updated = json.loads(config_path.read_text(encoding="utf-8"))
        model = updated["openai"][0]
        assert model["input_price_per_mtok"] > 0
        assert model["output_price_per_mtok"] > 0

    def test_update_config_dry_run(self, tmp_path):
        """dry_run=True computes changes but does not write the file."""
        config_path = tmp_path / "config.json"
        original = {
            "openai": [
                {
                    "name": "gpt-4o",
                    "max_context_tokens": 128000,
                    "input_price_per_mtok": 0.0,
                    "output_price_per_mtok": 0.0,
                }
            ]
        }
        original_text = json.dumps(original)
        config_path.write_text(original_text, encoding="utf-8")

        updater = PricingUpdater()
        result = updater.update_config(config_path, dry_run=True)

        assert result.total_changes > 0
        # File should NOT have changed
        assert config_path.read_text(encoding="utf-8") == original_text

    def test_models_not_found(self, tmp_path):
        """Models not in reference pricing appear in not_found."""
        config_path = tmp_path / "config.json"
        config_data = {
            "openai": [
                {
                    "name": "custom-unknown-model",
                    "max_context_tokens": 8000,
                }
            ]
        }
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        updater = PricingUpdater()
        result = updater.update_config(config_path)

        assert "custom-unknown-model" in result.not_found
        assert len(result.updated_models) == 0

    def test_no_changes_when_up_to_date(self, tmp_path):
        """No changes reported when prices match reference data."""
        updater = PricingUpdater()
        ref = updater.get_latest_prices()

        # Build a config that already matches reference pricing
        config_data = {}
        for provider, models in ref.items():
            config_data[provider] = []
            for model_name, pricing in models.items():
                entry = {"name": model_name, "max_context_tokens": 128000}
                entry.update(pricing)
                config_data[provider].append(entry)

        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        result = updater.update_config(config_path)
        assert result.total_changes == 0
