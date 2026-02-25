# CLI Reference

The `pcompile` command-line interface provides tools to compile, validate, and inspect prompt specifications.

## Global Options

- `--version`: Show the version and exit.
- `--help`: Show the help message and exit.

## Commands

### `compile`

Compiles a YAML DSL file into an optimized, model-specific prompt.

**Usage:**
```bash
pcompile compile [FILE] [OPTIONS]
```

**Arguments:**
- `FILE`: The path to the YAML DSL specification file. (Required)

**Options:**
- `-t, --target TEXT`: Override the `model_target` defined in the YAML spec. e.g., `gpt-4o`, `claude-3.5-sonnet`.
- `-o, --output PATH`: Write the resulting JSON output to a file instead of stdout.
- `--show-trace / --no-trace`: Include the compilation trace (steps taken by the optimizer/security modules) in the output. (Default: `no-trace`)

**Output Format:**
The command returns a JSON object containing:
- `model_target`: The model intended for this prompt.
- `plugin`: The plugin used for compilation.
- `parameters`: Recommended sampling parameters (temperature, etc.).
- `payload`: The model-specific payload ready for API submission.
- `prompt_text`: The raw text of the compiled prompt.
- `warnings`: (Optional) List of any warnings generated during compilation.
- `trace`: (Optional) Detailed compilation steps if `--show-trace` is used.

---

### `validate`

Performs static analysis on a DSL file without performing full compilation. This is useful for CI/CD pipelines.

**Usage:**
```bash
pcompile validate [FILE]
```

**Arguments:**
- `FILE`: The path to the YAML DSL specification file. (Required)

**Checks performed:**
- Schema validation (Pydantic).
- Ambiguity detection.
- Contradiction checking.
- Injection risk scoring.

**Output:**
- Shows a list of warnings or errors.
- Displays a **Clarity Score** and **Injection Risk** assessment.
- Returns exit code `1` if critical errors are found.

---

### `models`

Lists all available target models, their capabilities, and loaded plugins.

**Usage:**
```bash
pcompile models
```

**Displayed Information:**
- Model ID.
- Provider.
- Context Window Size.
- Max Output Tokens.
- JSON Mode Support.
- Function Calling Support.
- List of loaded Extension Plugins.

---

### `create`

Creates a DSL YAML specification from a natural language prompt using an LLM.

**Usage:**
```bash
pcompile create [PROMPT] [OPTIONS]
```

**Arguments:**
- `PROMPT`: A natural language description of the prompt you want to generate. (Optional if `--file` is used)

**Options:**
- `-f, --file PATH`: Path to a text file containing the natural language prompt.
- `-o, --output PATH`: Path to save the generated YAML.
- `--mock / --no-mock`: Use the mock generator (currently the default) or call a real provider. (Default: `mock`)

**Example:**
```bash
pcompile create "Create a prompt to summarize legal contracts." --output summarize.yaml
```
