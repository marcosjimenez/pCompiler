# pCompiler Plugin System

The pCompiler plugin system allows you to easily extend the framework to support new LLM backends and manage the models associated with them. This guide covers how to use existing plugins, how to write your own, and how to update or add model configurations.

## Using Current Plugins

pCompiler comes with built-in plugins for several major LLM providers:

- **OpenAI** (`openai`): Supports GPT-4, GPT-4o, etc.
- **Anthropic** (`anthropic`): Supports Claude 3, Claude 3.5 Sonnet, etc.
- **Google** (`google`): Supports Gemini 1.5 Pro, 2.0 Flash, etc.

You don't need to manually configure plugins in your daily usage. The `PluginManager` automatically discovers and dispatches them based on the `model_target` specified in your YAML DSL file. 

Example DSL specifying a model target:
```yaml
task: "analyze_sentiment"
model_target: "gpt-4o"
```
Under the hood, pCompiler looks up `gpt-4o` in the model registry, determines that it belongs to the `openai` provider, and routes the compilation to the OpenAI plugin.

---

## Creating New Plugins

If you want to add support for a different LLM provider (e.g., Mistral, Cohere, or a local model via vLLM/Ollama), you can create a new backend plugin.

### 1. Implement the `BackendPlugin` Interface
Create a class that inherits from `BackendPlugin` (located in `pcompiler.plugins.base`). You must implement two abstract methods:
- `name()`: Returns a unique string identifier for the provider (e.g., `'mistral'`).
- `emit(ir: PromptIR, profile: ModelProfile) -> CompiledPrompt`: The core compilation logic that turns the pCompiler Intermediate Representation (`PromptIR`) into the specific `CompiledPrompt` format your model expects.

```python
from typing import Any
from pcompiler.ir.nodes import PromptIR, SectionKind
from pcompiler.models.registry import ModelProfile
from pcompiler.plugins.base import BackendPlugin, CompiledPrompt

class MistralPlugin(BackendPlugin):
    def name(self) -> str:
        return "mistral"

    def emit(self, ir: PromptIR, profile: ModelProfile) -> CompiledPrompt:
        # 1. Transform IR sections into the provider's specific API format
        messages = []
        for section in ir.sections:
            if section.kind == SectionKind.SYSTEM:
                messages.append({"role": "system", "content": section.content})
            elif section.kind == SectionKind.INSTRUCTIONS:
                messages.append({"role": "user", "content": section.content})

        # 2. Extract and format parameters
        parameters = {
            "model": profile.name,
            "temperature": ir.metadata.get("temperature", profile.default_temperature)
        }

        # 3. Create flat text for observability
        prompt_text = "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in messages)

        # 4. Return the compiled object
        return CompiledPrompt(
            payload={"messages": messages},
            parameters=parameters,
            prompt_text=prompt_text,
            model_target=profile.name,
            plugin_used=self.name(),
        )
```

### 2. Register Your Plugin
You can register your plugin in two ways:

**Option A: Manual Registration (Programmatic)**
```python
from pcompiler.plugins.base import PluginManager
from my_package.mistral_plugin import MistralPlugin

manager = PluginManager()
manager.register(MistralPlugin())
```

**Option B: Auto-Discovery (Entry Points)**
If you are distributing your plugin as a Python package, expose it via the `pcompiler.plugins` entry point in your `pyproject.toml` or `setup.py`:
```toml
[project.entry-points."pcompiler.plugins"]
mistral = "my_package.mistral_plugin:MistralPlugin"
```
pCompiler will automatically discover and load it when starting.

---

## Updating Plugin Models

pCompiler's available models are configured externally in the `config.json` file located in the root of the project. This allows you to add or modify models without changing the codebase.

To add a new model for an existing plugin (or for a new plugin you just created), simply append a new JSON object to the array within the provider's key in the `config.json` file.

### Example: Adding a new model
Open `config.json` and insert a new object mapping inside the provider key:

```json
{
  "mistral": [
    {
      "name": "mistral-large-latest",
    "max_context_tokens": 32000,
    "max_output_tokens": 8192,
    "supports_system_prompt": true,
    "supports_json_mode": true,
      "supports_function_calling": true,
      "supports_vision": false,
      "default_temperature": 0.7
    }
  ]
}
```

### Configuration Fields
- `name` (string): The identifier used in your DSL `model_target`.
- `provider` (inferred from key): The root dictionary key that maps to the `name()` returned by the associated plugin.
- `max_context_tokens` (int): Context window capacity.
- `max_output_tokens` (int): Maximum output generation limit.
- `supports_system_prompt` (bool): Whether the model accepts a dedicated system prompt.
- `supports_json_mode` (bool): Signals if structured JSON outputs are natively supported.
- `supports_function_calling` (bool): Signals support for tool/function calling.
- `supports_vision` (bool): Signals if image/vision inputs are accepted.
- `default_temperature` (float): Fallback temperature setting if not overridden in the DSL.
- `extra` (object, optional): Any specific extra configurations (e.g. `thinking_tags`).
