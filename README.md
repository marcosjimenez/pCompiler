# pCompiler

[![Version](https://img.shields.io/badge/version-0.4.0-blue.svg)](pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

**pCompiler** is a declarative prompt engineering framework that transforms high-level DSL definitions into optimized, model-specific LLM prompts. It bridges the gap between raw text prompting and structured, versioned, and secure prompt management.

## 🚀 Key Features

- **DSL Generation**: Auto-generate YAML specs from natural language prompts.
- **Declarative YAML DSL**: Define prompts as typed, versionable specifications.
- **Context Engineering (RAG)**: Dynamic retrieval from static text, local files, vector stores, and web search.
- **Auto-Evals System**: Built-in automated metrics (`exact_match`, `regex`) and LLM-as-a-judge for quantitative prompt refinement.
- **Multi-Model Optimization**: Auto-reordering, semantic compression, and Chain-of-Thought (CoT) policies tailored for OpenAI, Anthropic, Gemini, and more.
- **Built-in Security**: Anti-injection policies, system/user separation, and input sanitization.
- **Deep Observability**: Full compilation traces, SHA-256 versioning, and reproducibility logs.
- **Extensible Plugin System**: Easily add custom backends, optimizers, or context providers.

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/marcosjimenez/pCompiler.git
cd pCompiler

# Install in editable mode
pip install -e "."
```

## 🛠 Quick Start

1. **Generate your prompt specification:**

```bash
# Describe what you want and generate the DSL YAML
pcompile create "Summarize a medical report focusing on patient history." --output medical.yaml
```

2. **Define your prompt (`summarize.yaml`):** (Or refine the generated file)

```yaml
task: summarize
model_target: gpt-4o
version: "1.2.0"

context:
  sources:
    - type: static
      value: "The user is a legal expert."
    - type: local_file
      value: "knowledge_base.txt"
  max_total_tokens: 1500

instructions:
  - text: "Summarize the contract focusing on liability clauses."
    priority: 100
  - text: "Use formal legal terminology."
    priority: 80

evals:
  threshold: 0.9
  cases:
    - name: "Short liability"
      input: { input: "Clause 1: Party A is liable for..." }
      expected: "Liability assigned to Party A"
      metrics: [includes, llm_judge]
```

3. **Compile it:**

```bash
# Generate the optimized payload
pcompile compile summarize.yaml --target gpt-4o
```

4. **Validate it:**

```bash
# Check for ambiguities, contradictions, and injection risks
pcompile validate summarize.yaml
```

5. **Run Evals:**

```bash
# Run automated tests to ensure quality
pcompile eval summarize.yaml --mock
```

## 📖 Documentation

- [**DSL Specification**](docs/dsl.md): Full reference for the YAML schema.
- [**Auto-Evals Guide**](docs/evals.md): How to build and run automated prompt quality tests.
- [**Context Engineering**](docs/dsl.md#context): Strategies for RAG and dynamic background information.
- [**CLI Reference**](docs/cli.md): Detailed usage for all `pcompile` commands.
- [**CI/CD Integration**](docs/cicd.md): Automating validation and testing in your pipeline.
- [**Packaging**](docs/packaging.md): How to build and distribute pCompiler.

## 🐍 Python API

```python
from pcompiler.compiler import PromptCompiler

compiler = PromptCompiler()

# Compile a file
result = compiler.compile_file("summarize.yaml", target="claude-3-5-sonnet")

print(f"Compiled Prompt:\n{result.prompt_text}")
print(f"API Payload: {result.payload}")
```

## 🧪 Testing

```bash
python -m pytest tests/ -v
```

---
*Created by the pCompiler Team. Optimize your prompts, automate your evaluations.*