# CI/CD Integration Guide

Integrating `pCompiler` into your CI/CD pipeline ensures that prompt specifications are valid, secure, and follow best practices before they are deployed or used in production.

## Core Command for CI

The primary command for CI/CD is `pcompile validate`. This command performs static analysis and returns a non-zero exit code if critical errors are found.

```bash
pcompile validate path/to/your/prompts/
```

> [!TIP]
> You can run `validate` on individual files or directories (if supported by your CI script). Currently, `pcompile validate` expects a single file. For multiple files, use a loop in your CI shell.

## GitHub Actions Example

Create a file named `.github/workflows/prompt-validation.yml`:

```yaml
name: Validate Prompts

on:
  push:
    branches: [ main ]
    paths:
      - 'prompts/**.yaml'
  pull_request:
    branches: [ main ]
    paths:
      - 'prompts/**.yaml'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-cache: 'pip'

      - name: Install pCompiler
        run: |
          pip install pcompiler

      - name: Validate all prompt specs
        run: |
          for file in prompts/*.yaml; do
            echo "Validating $file..."
            pcompile validate "$file"
          done
```

## GitLab CI Example

```yaml
validate_prompts:
  image: python:3.11
  stage: test
  script:
    - pip install pcompiler
    - |
      for file in prompts/*.yaml; do
        pcompile validate "$file"
      done
  only:
    changes:
      - prompts/*.yaml
```

## Best Practices

### 1. Versioning
Always include the `version` field in your YAML specs. `pCompiler` uses this for traceability. In CI, you might want to check that the version is incremented when a prompt changes.

### 2. Security Thresholds
Use the `security.level` in your YAML specs to enforce strict checks. If a prompt fails the `strict` validation in CI, the build will fail, preventing potentially vulnerable prompts from reaching production.

### 3. Automated Regression Testing
Combine `pcompile validate` with your own unit tests that run the compilation and verify the output against a set of expectations.

```python
from pcompiler.compiler import PromptCompiler

def test_prompt_compilation():
    compiler = PromptCompiler()
    result = compiler.compile_file("prompts/summarize.yaml")
    assert "Summarize" in result.prompt_text
    assert result.model_target == "gpt-4o"
```
