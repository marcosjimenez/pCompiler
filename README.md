# pCompiler

[![Version](https://img.shields.io/badge/version-0.4.0-blue.svg)](pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

**pCompiler** is a declarative prompt engineering framework that transforms high-level DSL definitions into optimized, model-specific LLM prompts. It bridges the gap between raw text prompting and structured, versioned, and secure prompt management.

---

## 🌟 What the project does

pCompiler allows developers to treat prompts as code. By defining prompts in a structured YAML Domain Specific Language (DSL), you can:

- **Generate** starting specifications from natural language descriptions.
- **Validate** prompts for ambiguities, contradictions, and security risks.
- **Optimize** content for specific LLM backends (OpenAI, Anthropic, Gemini).
- **Automate** quality control with built-in evaluation suites.
- **Deploy** versioned, reproducible prompt payloads to your applications.

## ✨ Why pCompiler?

In a world where LLM prompts are increasingly complex and critical to application logic, pCompiler provides the tools to make them robust:

- **Type Safety & Validation**: Uses Pydantic to ensure your specifications are always valid.
- **Smart Optimization**: Automatically applies semantic compression, Chain-of-Thought policies, and section reordering tailored to each model's strengths.
- **Security by Design**: Native protection against prompt injection and system prompt leakage.
- **Collaborative Engineering**: Versioned YAML files make it easy for teams to track changes and collaborate via Git.
- **RAG Ready**: Built-in support for multiple context sources, including local files, vector stores, and web search.

## 🚀 How to get started

### Installation

```bash
# Clone the repository
git clone https://github.com/marcosjimenez/pCompiler.git
cd pCompiler

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Quick Start

1. **Auto-generate a DSL spec:**
   ```bash
   pcompile create "Summarize a medical report focusing on patient history." --output medical.yaml
   ```

2. **Refine your DSL specification (`medical.yaml`):**
   ```yaml
   task: summarize
   model_target: gpt-4o
   constraints:
     tone: professional
     cot_policy: auto
   instructions:
     - text: "Highlight patient history and active medications."
       priority: 100
   ```

3. **Compile to a model-ready payload:**
   ```bash
   pcompile compile medical.yaml --target gpt-4o
   ```

4. **Run automated evaluations:**
   ```bash
   pcompile eval medical.yaml --mock
   ```

## 📖 Where to get help

- [**DSL Reference**](docs/dsl.md): Detailed documentation of the YAML schema and attributes.
- [**CLI Guide**](docs/cli.md): Full list of commands and options.
- [**Auto-Evals System**](docs/evals.md): How to build and run automated prompt quality tests.
- [**Context Engineering**](docs/dsl.md#context): Strategies for RAG and dynamic background information.
- [**Integrated CI/CD**](docs/cicd.md): Automating validation and testing in your pipeline.
- [**Packaging**](docs/packaging.md): How to build and distribute pCompiler on your own registry.

## 👥 Who maintains & contributes

### Maintainer
- **Marcos Jiménez** - [GitHub Profile](https://github.com/marcosjimenez)

### Contributing
We welcome contributions! Please feel free to open an issue or pull request to suggest improvements or report bugs.

---

*pCompiler — Optimize your prompts, automate your evaluations.*