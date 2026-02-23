# Auto-Evals Guide

The Auto-Evals system in `pCompiler` allows you to quantitatively measure the performance of your prompts using automated metrics and LLM-based judging.

## Overview

By defining test cases directly in your DSL files, you can ensure that changes to instructions, templates, or context selection do not degrade the quality of the generated responses.

## Defining Evaluations

Evaluations are defined in the `evals` section of your YAML prompt specification.

```yaml
evals:
  threshold: 0.8          # Global pass/fail threshold (0.0 to 1.0)
  judge_model: "gpt-4o"   # Model to use if 'llm_judge' metric is used
  cases:
    - name: "Brief Invoice Extraction"
      input:
        invoice_text: "Invoice #9981 - Total: $50.00"
      expected: "9981"
      metrics: [includes, regex]
```

### Metrics Reference

| Metric | Description | Expected Value Required |
| --- | --- | --- |
| `exact_match` | Checks if the output exactly matches the expected string (ignoring whitespace). | Yes |
| `includes` | Checks if the expected string is present anywhere in the output. | Yes |
| `regex` | Validates the output against a regular expression pattern provided in `expected`. | Yes |
| `llm_judge` | Uses a separate LLM call to grade the response quality (0.0 to 1.0). | No (Optional) |
| `semantic` | (Upcoming) Uses embeddings to calculate semantic similarity. | Yes |

## Running Evaluations

Use the `eval` command in the CLI to execute test cases.

```bash
# Run evaluations for a specific file
pcompile eval examples/evals_demo.yaml

# Run with mock execution (no API costs, useful for pipeline testing)
pcompile eval examples/evals_demo.yaml --mock
```

### Understanding the Report

When you run `pcompile eval`, a summary table is displayed:

- **Test Case**: The name defined in the YAML.
- **Output**: A preview of the LLM response.
- **Score**: The average score across all specified metrics for that case.
- **Pass/Fail**: Indicates if the average score meets the defined `threshold`.

The command will exit with code `0` if all test cases pass, or code `1` if the success rate is less than 100%.

## Best Practices

1. **Use golden datasets**: Provide high-quality `expected` answers for heuristic metrics like `includes`.
2. **LLM Judge for intent**: Use `llm_judge` for creative or complex tasks where exact matches are impossible.
3. **CI/CD Integration**: Run `pcompile eval` as a build step to prevent prompt regressions.
