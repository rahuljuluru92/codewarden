# CodeWarden

CodeWarden is a multi-agent architectural compliance checker. Point it at a codebase and a set of rules, and it tells you where the code violates your architecture, using Tree-sitter AST parsing (not text or line matching), ChromaDB retrieval over AST-derived code chunks, and a three-role LangGraph agent pipeline to reason about violations that need judgment, not just pattern matching.

It ships as three ways to use it: a Python CLI, a GitHub Action, and an MCP server.

## How it works

1. **Parsing.** Source files are parsed into structured ASTs with Tree-sitter (Python and TypeScript are supported). Imports, function boundaries, and class boundaries are extracted into a structured representation.
2. **Indexing and retrieval.** Each function and class becomes a chunk (not a raw text window) and is indexed into ChromaDB. Rules that need judgment retrieve the relevant chunks for review.
3. **Multi-agent pipeline.** A LangGraph pipeline with three roles processes the rules:
   - **Planner**: decides what to check. Structural rules (import restrictions, layering) are resolved directly from parsed AST metadata, no LLM call needed. Rules that require judgment are resolved by retrieving relevant code chunks from the index.
   - **Executor**: decides whether a specific piece of code violates a specific rule. Structural rules are checked with plain code, no LLM involved. Judgment based rules are evaluated by an LLM.
   - **Verifier**: reviews the batch of findings. Low confidence verdicts are sent back to the Planner for another pass with more context rather than being reported or silently dropped. The final structured report is produced once every finding is either confident or has already been retried once.

## The rule schema

Rules are written in YAML. Each rule has an id, name, description, rationale, severity, target languages, a scope (which files it applies to, via glob patterns), and a `params` block whose shape depends on the rule type.

There are three rule types:

**`import_restriction`**: flags files that import something they should not.

```yaml
- id: no-controller-db-access
  name: Controllers must not access the database directly
  description: >
    Files under any controllers/ or api/ directory must not import
    the ORM or database layer directly.
  rationale: >
    Direct DB access from controllers couples HTTP handling to storage
    details and makes controllers hard to test.
  severity: error
  languages: [python]
  scope:
    include: ["**/controllers/**/*.py", "**/api/**/*.py"]
  params:
    rule_type: import_restriction
    from_module_glob: "**/controllers/**/*.py"
    forbidden_import_globs: ["**/db/**", "**/models/orm/**"]
```

**`layering`**: flags any import from one layer into a forbidden layer.

```yaml
- id: no-service-to-api-import
  name: Services must not import from the API layer
  severity: error
  languages: [python, typescript]
  scope:
    include: ["**/services/**/*"]
  params:
    rule_type: layering
    source_layer_glob: "**/services/**/*"
    target_layer_glob: "**/{api,controllers}/**/*"
    direction: forbidden
```

**`semantic_check`**: for rules that need judgment rather than a structural match. A natural language prompt is evaluated by an LLM against the retrieved code.

```yaml
- id: no-business-logic-in-controllers
  name: Controllers must stay thin
  severity: warning
  languages: [python, typescript]
  scope:
    include: ["**/controllers/**/*", "**/api/**/*"]
  params:
    rule_type: semantic_check
    check_prompt: >
      Does this controller or handler function contain non-trivial
      business logic rather than delegating to a service function?
    applies_to_glob: "**/{controllers,api}/**/*"
```

A full example rules file with all three types is in `rules/examples/example_rules.yaml`.

## Setup

Requires Python 3.11 or newer (developed and tested on 3.12).

```bash
git clone https://github.com/rahuljuluru92/codewarden.git
cd codewarden
python3 -m venv venv
source venv/bin/activate
pip install -e .
cp .env.example .env
```

Edit `.env` and fill in a Groq API key (free tier works, get one at console.groq.com/keys). The pipeline uses Groq's OpenAI compatible endpoint for the LLM calls the Executor role makes for `semantic_check` rules. Structural rules never call the LLM.

## Testing

There are two test suites.

**Fast suite**: unit and integration tests with mocked LLM responses, safe to run on every commit, no API calls made.

```bash
pytest
```

**Live suite**: tests that call the real Groq API, marked with `@pytest.mark.live` and excluded from the default run.

```bash
pytest -m live
```

**Eval harness**: runs the full pipeline against a hand labeled Golden Dataset and computes real precision, recall, and F1. This makes real LLM calls.

```bash
python -m codewarden.eval.harness
```

## Measured accuracy

The Golden Dataset is a set of 13 synthetic Python and TypeScript files under `eval/golden_dataset/repo/`, written with deliberately planted violations and deliberately clean counterexamples, labeled at the file level against all four example rules (23 labeled rule and file pairs total, in `eval/golden_dataset/labels.yaml`). It is synthetic rather than sourced from real open source violations, which keeps the labels unambiguous but means these numbers describe performance on clear cut cases, not a claim about messier real world code.

An early version of the pipeline scored:

| | Precision | Recall | F1 |
|---|---|---|---|
| Overall | 1.0 | 0.8 | 0.8889 |

Investigating the two missed violations found a real bug: the Planner ran a single retrieval query across every file in a rule's scope, so a file whose functions happened to embed less closely to the rule's check prompt could get crowded out of the results entirely, meaning the violating function was never even sent to the LLM for review. This was fixed by querying each in-scope file separately so every file gets its functions considered. After the fix, on the same dataset:

| | Precision | Recall | F1 |
|---|---|---|---|
| Overall | 1.0 | 1.0 | 1.0 |

Both runs were reproduced twice with identical results at temperature 0. The structural rules (import restriction and layering) score perfectly in both cases, since they never involve the LLM. A perfect score on a 23 pair synthetic dataset is a strong signal that the pipeline and the retrieval fix work as intended, not a claim of production grade accuracy on arbitrary real world codebases.

## Using the CLI

```bash
codewarden check <path-to-repo> --rules <path-to-rules.yaml> [--format text|json] [--fail-on error|warning|info|never]
```

`--fail-on` controls the exit code: the command exits 1 if a finding at or above that severity is present (default `error`), or always exits 0 with `--fail-on never`. This is what the GitHub Action uses for pass and fail behavior in CI.

Example, checking the bundled Golden Dataset repo:

```bash
codewarden check eval/golden_dataset/repo --rules rules/examples/example_rules.yaml
```

## Using the GitHub Action

`action.yml` at the repository root wraps the CLI as a composite action. Reference it from a workflow:

```yaml
- uses: actions/checkout@v4
- uses: rahuljuluru92/codewarden@main
  with:
    repo-path: .
    rules-path: rules/my-rules.yaml
    fail-on: error
    groq-api-key: ${{ secrets.GROQ_API_KEY }}
```

This has been exercised in this repository's own CI (`.github/workflows/codewarden-self-check.yml`), which runs the action against the Golden Dataset repo on every push to `main` and can also be triggered manually.

## Using the MCP server

CodeWarden can be exposed as an MCP server, so it can be called as a tool from an MCP compatible client such as Claude Desktop, Cursor, or Windsurf. Start it directly:

```bash
python -m codewarden.mcp.server
```

It communicates over stdio and exposes a single tool, `check_repository(repo_path, rules_path)`, which returns the same structured JSON report as the CLI.

To use it from Claude Desktop, add an entry to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "codewarden": {
      "command": "/path/to/codewarden/venv/bin/python3",
      "args": ["-m", "codewarden.mcp.server"],
      "cwd": "/path/to/codewarden",
      "env": {
        "GROQ_API_KEY": "your-key-here",
        "GROQ_BASE_URL": "https://api.groq.com/openai/v1",
        "GROQ_MODEL": "openai/gpt-oss-120b"
      }
    }
  }
}
```

Note that MCP clients spawn the server with their own environment, not your shell's, so the API key needs to be set explicitly in the client config rather than just exported in a terminal.

The server has been verified at the protocol level: a real MCP client (the official `mcp` Python SDK's own stdio client) was used to list its tools and call `check_repository` against the Golden Dataset repo, and it returned a correct structured report.

## Project layout

```
codewarden/
  parsing/    Tree-sitter AST parsing and extraction
  indexing/   ChromaDB chunking and retrieval
  agents/     Planner, Executor, Verifier, and the LangGraph pipeline
  rules/      Rule schema, loader, and glob matching
  cli/        The codewarden CLI
  mcp/        The MCP server
  eval/       Golden Dataset loading, metrics, and eval harness
rules/examples/    Example rules file
eval/golden_dataset/    The Golden Dataset repo and labels
tests/    Fast test suite plus live-marked integration tests
action.yml    GitHub Action definition
.github/workflows/    Self-check CI workflow
```

## Scope

CodeWarden performs detection and reporting only. It does not auto-fix violations. It supports Python and TypeScript. These are deliberate scope boundaries, not limitations to be worked around casually.
