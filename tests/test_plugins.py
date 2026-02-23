"""Tests for the plugin system and backend plugins."""

import pytest

from pcompiler.ir.nodes import PromptIR, SectionKind
from pcompiler.models.registry import ModelRegistry
from pcompiler.plugins.anthropic_plugin import AnthropicPlugin
from pcompiler.plugins.base import BackendPlugin, CompiledPrompt, PluginManager
from pcompiler.plugins.google_plugin import GooglePlugin
from pcompiler.plugins.openai_plugin import OpenAIPlugin


@pytest.fixture
def registry():
    return ModelRegistry()


@pytest.fixture
def sample_ir():
    ir = PromptIR(task="summarize", model_target="gpt-4o")
    ir.metadata["temperature"] = 0.5
    ir.metadata["top_p"] = 1.0
    ir.metadata["max_tokens"] = 200
    ir.add(SectionKind.SYSTEM, "You are a helpful summarizer.")
    ir.add(SectionKind.INSTRUCTIONS, "Summarize the document.")
    ir.add(SectionKind.CONTEXT, "This is a legal contract about liability.")
    ir.add(SectionKind.USER_INPUT, "Please summarize the above.")
    ir.add(SectionKind.EXAMPLES, "Input: Contract X.\nOutput: Summary of X.")
    return ir


class TestPluginManager:
    def test_auto_discover(self):
        pm = PluginManager(auto_discover=True)
        # Built-in plugins should be discovered
        assert len(pm.list_plugins()) >= 3

    def test_manual_register(self):
        pm = PluginManager(auto_discover=False)
        pm.register(OpenAIPlugin())
        assert "openai" in pm.list_plugins()

    def test_get_plugin_for_model(self):
        pm = PluginManager(auto_discover=False)
        pm.register(OpenAIPlugin())
        plugin = pm.get_plugin_for_model("gpt-4o")
        assert plugin.name() == "openai"

    def test_unknown_model_error(self):
        pm = PluginManager(auto_discover=False)
        with pytest.raises(KeyError, match="No plugin"):
            pm.get_plugin_for_model("unknown-model")

    def test_list_supported_models(self):
        pm = PluginManager(auto_discover=False)
        pm.register(OpenAIPlugin())
        pm.register(AnthropicPlugin())
        models = pm.list_supported_models()
        assert "gpt-4o" in models
        assert "claude-3.5-sonnet" in models


class TestOpenAIPlugin:
    def test_emit(self, registry, sample_ir):
        plugin = OpenAIPlugin()
        profile = registry.get("gpt-4o")
        result = plugin.emit(sample_ir, profile)

        assert isinstance(result, CompiledPrompt)
        assert result.plugin_used == "openai"
        assert result.model_target == "gpt-4o"
        assert "messages" in result.payload
        assert result.parameters["model"] == "gpt-4o"
        assert result.parameters["temperature"] == 0.5
        assert result.parameters["max_tokens"] == 200

    def test_system_message_present(self, registry, sample_ir):
        plugin = OpenAIPlugin()
        profile = registry.get("gpt-4o")
        result = plugin.emit(sample_ir, profile)

        messages = result.payload["messages"]
        assert messages[0]["role"] == "system"
        assert "summarizer" in messages[0]["content"]

    def test_json_mode(self, registry):
        ir = PromptIR(task="test", model_target="gpt-4o")
        ir.metadata["temperature"] = 0.7
        ir.metadata["top_p"] = 1.0
        ir.metadata["output_schema"] = {"type": "object"}
        ir.add(SectionKind.SYSTEM, "Test")

        plugin = OpenAIPlugin()
        profile = registry.get("gpt-4o")
        result = plugin.emit(ir, profile)

        assert result.parameters.get("response_format") == {"type": "json_object"}


class TestAnthropicPlugin:
    def test_emit(self, registry, sample_ir):
        plugin = AnthropicPlugin()
        sample_ir.model_target = "claude-3.5-sonnet"
        profile = registry.get("claude-3.5-sonnet")
        result = plugin.emit(sample_ir, profile)

        assert result.plugin_used == "anthropic"
        assert "system" in result.payload
        assert "messages" in result.payload
        assert result.parameters["model"] == "claude-3.5-sonnet"

    def test_xml_tags(self, registry, sample_ir):
        plugin = AnthropicPlugin()
        sample_ir.model_target = "claude-3.5-sonnet"
        profile = registry.get("claude-3.5-sonnet")
        result = plugin.emit(sample_ir, profile)

        user_content = result.payload["messages"][0]["content"]
        assert "<context>" in user_content
        assert "<instructions>" in user_content


class TestGooglePlugin:
    def test_emit(self, registry, sample_ir):
        plugin = GooglePlugin()
        sample_ir.model_target = "gemini-1.5-pro"
        profile = registry.get("gemini-1.5-pro")
        result = plugin.emit(sample_ir, profile)

        assert result.plugin_used == "google"
        assert "contents" in result.payload
        assert result.parameters["model"] == "gemini-1.5-pro"
        assert "generationConfig" in result.parameters

    def test_system_instruction(self, registry, sample_ir):
        plugin = GooglePlugin()
        sample_ir.model_target = "gemini-1.5-pro"
        profile = registry.get("gemini-1.5-pro")
        result = plugin.emit(sample_ir, profile)

        assert result.payload["systemInstruction"]  # non-empty
