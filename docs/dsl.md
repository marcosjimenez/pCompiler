# YAML DSL Specification

The `pCompiler` uses a declarative YAML Domain Specific Language (DSL) to define prompt specifications. This allows prompts to be versioned, validated, and optimized for different LLM providers.

> [!TIP]
> You can automatically generate a starting DSL specification from a natural language prompt using the `pcompile create` command. See the [CLI Reference](cli.md#create) for details.

## Root Attributes

| Attribute | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `task` | `string` | **Yes** | Name of the task (e.g., `summarize`, `code_generation`). |
| `input_type` | `string` | No | Semantic type of input (e.g., `legal_contract`, `customer_email`). Default: `text`. |
| `model_target` | `string` | No | Target model identifier. Default: `gpt-4o`. |
| `context` | `string` or `Object` | No | Static context or dynamic context configuration (sources, ranking, pruning). |
| `user_input_template` | `string` | No | Template for the user input. Use `{input}` placeholder. |
| `constraints` | `Object` | No | Constraints governing the output behavior. |
| `instructions` | `Array` | No | List of custom instructions with priorities. |
| `few_shot_examples` | `Array` | No | Examples of input/output pairs. |
| `output_schema` | `Object` | No | Expected JSON structure for the output. |
| `security` | `Object` | No | Security policies and sanitization levels. |
| `evals` | `Object` | No | Evaluation configuration and test cases. |
| `version` | `string` | No | Version of the specification. Default: `1.0`. |
| `tags` | `Array` | No | List of metadata tags. |

---

## Nested Objects

### `constraints`

Controls the generation parameters and formatting rules.

- `max_tokens` (int): Maximum output tokens.
- `tone` (enum): The desired tone. Options: `formal`, `informal`, `technical`, `creative`, `neutral` (default).
- `temperature` (float): Sampling temperature (0.0 to 2.0).
- `top_p` (float): Nucleus sampling (0.0 to 1.0).
- `cot_policy` (enum): Chain-of-thought policy. Options: `always`, `auto` (default), `never`.
- `include_risks` (bool): Ask the model to identify potential risks.
- `include_citations` (bool): Request source citations.
- `include_confidence` (bool): Request a confidence score.

### `instructions`

A list of specific goals or rules for the prompt.

- `text` (string): The instruction content.
- `priority` (int): Priority from 0 to 100. Higher numbers are prioritized by the compiler during context window constraints.

### `few_shot_examples`

Provides in-context learning examples.

- `input` (string): Example user query.
- `output` (string): Expected model response.
- `explanation` (string): Optional reasoning for the example.

### `context`

Defines dynamic background information to be injected into the prompt.

- `sources` (Array): List of context sources.
    - `type` (enum): `static`, `local_file`, `vector_store`, `web_search`.
    - `value` (string): Text value for `static` or file path for `local_file`.
    - `query` (string): Search query for `vector_store` or `web_search`.
    - `priority` (int): 0-100 (default: 50). Used for ranking when pruning.
    - `config` (dict): Provider-specific configuration.
- `combine_strategy` (enum): `ranked` (default) or `ordered`.
- `max_total_tokens` (int): Optional limit for the entire context block.

### `evals`

Defines automated test cases to run against the prompt.

- `threshold` (float): Global pass/fail threshold (0.0 to 1.0, default: 0.8).
- `judge_model` (string): Model used for `llm_judge` metrics.
- `cases` (Array): List of test cases.
    - `name` (string): Description of the test.
    - `input` (dict): Key-value pairs of input variables.
    - `expected` (string): The 'golden' or expected output.
    - `metrics` (Array): Metrics to run. Options: `exact_match` (default), `includes`, `regex`, `llm_judge`, `semantic`.

See the [Auto-Evals Guide](evals.md) for more details on how to run and interpret evaluations.

### `output_schema`

Uses JSON Schema to define the required output structure.

- `type` (string): Root type (usually `object`).
- `properties` (dict): Field definitions.
- `required` (list): Required field names.

### `security`

Defines security and sanitization rules.

- `level` (enum): `strict`, `moderate` (default), `permissive`.
- `block_code_execution` (bool): Sanitize potential code-injection patterns.
- `block_system_prompt_leak` (bool): Guard against "ignore previous instructions" attacks.
- `block_instruction_override` (bool): Prevent users from redefining the task.

---

## Complete Example

```yaml
task: sentiment_analysis
input_type: product_review
model_target: claude-3-5-sonnet-20240620
version: "2.1"

constraints:
  tone: neutral
  temperature: 0.3
  include_confidence: true

instructions:
  - text: "Analyze the sentiment as strictly Positive, Negative, or Neutral."
    priority: 100
  - text: "Ignore emojis and focus on textual content."
    priority: 50

output_schema:
  type: object
  properties:
    sentiment:
      type: string
      enum: [Positive, Negative, Neutral]
    score:
      type: number
    justification:
      type: string
  required: [sentiment, score]

security:
  level: strict
```
