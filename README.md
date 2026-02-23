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
print(result.prompt_text)        # texto plano
print(result.payload)            # payload específico del modelo
print(result.parameters)         # hiperparámetros recomendados
```

## License

MIT License

Copyright (c) 2026 Juan Marcos Jiménez Montes

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
