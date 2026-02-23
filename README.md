# pCompiler

A prompt compiler that transforms declarative DSL definitions into optimised, model-specific LLM prompts.

## Features

- **YAML DSL** — define prompts as typed, versionable specs
- **Plugin system** — extensible backends for OpenAI, Anthropic, Google (and custom)
- **Static analysis** — ambiguity detection, contradiction checking, injection risk scoring
- **Optimization** — instruction reordering, semantic compression, auto chain-of-thought
- **Security** — input sanitization, anti-injection policies, system/user separation
- **Observability** — compilation traces, SHA-256 versioning, full reproducibility

## Quick Start

```bash
pip install -e ".[dev]"

# Compile a prompt spec
pcompile compile examples/summarize_contract.yaml --target gpt-4o

# Validate only (no compilation)
pcompile validate examples/summarize_contract.yaml

# List available models
pcompile models
```

## Documentation

For detailed information, see:
- [CLI Reference](docs/cli.md) — Detailed guide for all `pcompile` commands and parameters.
- [DSL Specification](docs/dsl.md) — Full specification of the YAML prompt definition language.

## DSL Example

```yaml
task: summarize
input_type: legal_contract
model_target: gpt-4o
constraints:
  max_tokens: 500
  tone: formal
  include_risks: true
instructions:
  - text: "Summarize the key clauses."
    priority: 80
security:
  level: strict
```

## Tests

```bash
python -m pytest tests/ -v
```

## Using as Python API

```python
from pcompiler.compiler import PromptCompiler

compiler = PromptCompiler()
result = compiler.compile_file("examples/summarize_contract.yaml", target="gpt-4o")
print(result.prompt_text)        # plain text
print(result.payload)            # model specific payload
print(result.parameters)         # recommended parameters
```