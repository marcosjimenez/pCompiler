# Cost and Latency Estimation

pCompiler includes a built-in "Cost and Latency Estimator" that allows you to calculate the economic cost and expected response time of executing a prompt **before** actually sending it to the LLM API. 

This is incredibly useful for:
- Managing budgets for large batch-processing jobs.
- Selecting the most cost-effective model for a specific task.
- Understanding latency implications before deploying a prompt to production.

## How it works

The estimator relies on two core pieces of information:
1. **Token Estimation**: pCompiler's Intermediate Representation (IR) accurately estimates the total number of input tokens the compiled prompt will consume.
2. **Reference Pricing**: The `config.json` file contains updated pricing data (`input_price_per_mtok`, `output_price_per_mtok`) and latency metrics (`avg_latency_ms_per_output_token`) for each registered model.

Using these metrics, the estimator calculates the expected cost and latency based on your prompt's size and the target model's rates.

---

## Estimating a Prompt

To estimate the cost and latency of a prompt, use the `pcompile estimate` command:

```bash
pcompile estimate my_prompt.yaml
```

**Output example:**
```
Cost Estimate — gpt-4o
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Metric        ┃         Value ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Provider      │        openai │
│ Input Tokens  │           450 │
│ Output Tokens │        16,384 │
│ Input Cost    │     $0.001125 │
│ Output Cost   │     $0.163840 │
│ Total Cost    │     $0.164965 │
│ Est. Latency  │    294,912 ms │
└───────────────┴───────────────┘
```

### Providing Expected Output Tokens

By default, the estimator assumes the model will generate its maximum output capacity (`max_output_tokens`). To get a more realistic estimate, tell the compiler how many tokens you actually expect the response to be:

```bash
pcompile estimate my_prompt.yaml --output-tokens 500
```

---

## Comparing Models

If you want to find the most cost-effective model for your prompt, use the `--compare` flag. This will run the estimator against **all available models** registered in your `config.json`.

```bash
pcompile estimate my_prompt.yaml --output-tokens 500 --compare
```

**Output example:**
```
Cost & Latency Comparison
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Model             ┃ Provider  ┃ Input Tokens ┃ Output Tokens ┃  Input Cost ┃ Output Cost ┃  Total Cost ┃  Latency ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ ministral-3-3b    │ mistral   │          450 │           500 │   $0.000018 │   $0.000020 │   $0.000038 │ 2,500 ms │
│ gemini-2.5-flash  │ google    │          450 │           500 │   $0.000067 │   $0.000300 │   $0.000367 │ 4,000 ms │
│ gpt-4o-mini       │ openai    │          450 │           500 │   $0.000067 │   $0.000300 │   $0.000367 │ 5,000 ms │
│ claude-haiku-4.5  │ anthropic │          450 │           500 │   $0.000360 │   $0.002000 │   $0.002360 │ 6,000 ms │
│ gpt-4o            │ openai    │          450 │           500 │   $0.001125 │   $0.005000 │   $0.006125 │ 9,000 ms │
└───────────────────┴───────────┴──────────────┴───────────────┴─────────────┴─────────────┴─────────────┴──────────┘
```

---

## Keeping Prices Up to Date

LLM API pricing changes frequently. pCompiler holds a set of reference prices in its updater module. To automatically sync your `config.json` file with the latest known prices, run:

```bash
pcompile update-pricing
```

This command will scan all models in your `config.json` and update their pricing fields if they differ from the reference data.

### Dry Run

If you want to see what prices would be updated without actually modifying the `config.json` file, use the `--dry-run` flag:

```bash
pcompile update-pricing --dry-run
```
