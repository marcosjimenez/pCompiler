"""Tests for optimization passes."""

import pytest

from pcompiler.dsl.schema import CoTPolicy
from pcompiler.ir.nodes import PromptIR, SectionKind
from pcompiler.models.registry import ModelRegistry
from pcompiler.optimizer.cache import PromptCache
from pcompiler.optimizer.compress import compress
from pcompiler.optimizer.cot import insert_chain_of_thought
from pcompiler.optimizer.reorder import reorder_sections
from pcompiler.plugins.base import CompiledPrompt


@pytest.fixture
def registry():
    return ModelRegistry()


class TestReorder:
    def test_reorders_by_profile(self, registry):
        profile = registry.get("gpt-4o")
        ir = PromptIR(task="test", model_target="gpt-4o")
        ir.add(SectionKind.USER_INPUT, "user data")
        ir.add(SectionKind.SYSTEM, "system text")
        ir.add(SectionKind.INSTRUCTIONS, "do this")

        result = reorder_sections(ir, profile)
        kinds = [s.kind for s in result.sections]
        # SYSTEM should come before INSTRUCTIONS, which should come before USER_INPUT
        assert kinds.index(SectionKind.SYSTEM) < kinds.index(SectionKind.INSTRUCTIONS)
        assert kinds.index(SectionKind.INSTRUCTIONS) < kinds.index(SectionKind.USER_INPUT)

    def test_preserves_content(self, registry):
        profile = registry.get("gpt-4o")
        ir = PromptIR(task="test", model_target="gpt-4o")
        ir.add(SectionKind.INSTRUCTIONS, "instruction A")
        ir.add(SectionKind.SYSTEM, "system")

        result = reorder_sections(ir, profile)
        contents = {s.content for s in result.sections}
        assert "instruction A" in contents
        assert "system" in contents


class TestCompress:
    def test_deduplication(self, registry):
        profile = registry.get("gpt-4o")
        ir = PromptIR(task="test", model_target="gpt-4o")
        ir.add(SectionKind.INSTRUCTIONS, "Do X.")
        ir.add(SectionKind.INSTRUCTIONS, "Do X.")  # duplicate
        ir.add(SectionKind.INSTRUCTIONS, "Do Y.")

        result = compress(ir, profile)
        assert result.sections_removed >= 1
        assert result.tokens_after <= result.tokens_before

    def test_adjacent_merge(self, registry):
        profile = registry.get("gpt-4o")
        ir = PromptIR(task="test", model_target="gpt-4o")
        ir.add(SectionKind.CONTEXT, "Part A.")
        ir.add(SectionKind.CONTEXT, "Part B.")

        result = compress(ir, profile)
        # After dedup, the two unique CONTEXT sections should be merged
        ctx = result.ir.get_sections(SectionKind.CONTEXT)
        assert len(ctx) == 1
        assert "Part A" in ctx[0].content
        assert "Part B" in ctx[0].content


class TestChainOfThought:
    def test_always_inserts(self):
        ir = PromptIR(task="summarize", model_target="gpt-4o")
        result = insert_chain_of_thought(ir, CoTPolicy.ALWAYS)
        cot = result.get_sections(SectionKind.CHAIN_OF_THOUGHT)
        assert len(cot) == 1

    def test_never_skips(self):
        ir = PromptIR(task="classify", model_target="gpt-4o")
        result = insert_chain_of_thought(ir, CoTPolicy.NEVER, "classify")
        cot = result.get_sections(SectionKind.CHAIN_OF_THOUGHT)
        assert len(cot) == 0

    def test_auto_with_recommended(self):
        ir = PromptIR(task="classify", model_target="gpt-4o")
        result = insert_chain_of_thought(ir, CoTPolicy.AUTO, "classify")
        cot = result.get_sections(SectionKind.CHAIN_OF_THOUGHT)
        assert len(cot) == 1  # classify template recommends CoT

    def test_auto_without_recommended(self):
        ir = PromptIR(task="summarize", model_target="gpt-4o")
        result = insert_chain_of_thought(ir, CoTPolicy.AUTO, "summarize")
        cot = result.get_sections(SectionKind.CHAIN_OF_THOUGHT)
        assert len(cot) == 0  # summarize does NOT recommend CoT

    def test_no_double_insert(self):
        ir = PromptIR(task="test", model_target="gpt-4o")
        ir.add(SectionKind.CHAIN_OF_THOUGHT, "Existing CoT")
        result = insert_chain_of_thought(ir, CoTPolicy.ALWAYS)
        cot = result.get_sections(SectionKind.CHAIN_OF_THOUGHT)
        assert len(cot) == 1


class TestCache:
    def test_put_and_get(self):
        cache = PromptCache(max_size=10)
        key = cache.make_key({"task": "test"}, "gpt-4o")
        prompt = CompiledPrompt(payload={"test": True}, prompt_text="test")
        cache.put(key, prompt)
        assert cache.get(key) is prompt

    def test_miss(self):
        cache = PromptCache()
        assert cache.get("nonexistent") is None

    def test_lru_eviction(self):
        cache = PromptCache(max_size=2)
        p = CompiledPrompt(payload={}, prompt_text="")

        k1 = cache.make_key({"a": 1}, "m")
        k2 = cache.make_key({"a": 2}, "m")
        k3 = cache.make_key({"a": 3}, "m")
        cache.put(k1, p)
        cache.put(k2, p)
        cache.put(k3, p)

        assert cache.size == 2
        assert cache.get(k1) is None  # evicted
        assert cache.get(k3) is not None

    def test_stats(self):
        cache = PromptCache(max_size=10)
        key = cache.make_key({"x": 1}, "m")
        cache.put(key, CompiledPrompt(payload={}, prompt_text=""))

        cache.get(key)  # hit
        cache.get("missing")  # miss

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
