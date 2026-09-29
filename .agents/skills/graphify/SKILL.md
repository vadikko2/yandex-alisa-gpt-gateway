---
name: graphify
description: Builds or refreshes the graphify knowledge graph in graphify-out/. Use when the user runs /graphify, asks to index or update the codebase graph, or graphify-out/graph.json is missing before exploration.
disable-model-invocation: true
---

# Graphify

## Overview

Maintain the project knowledge graph at `graphify-out/` using the `graphify` CLI. The graph powers scoped exploration via `query`, `path`, and `explain` — see `.cursor/rules/graphify.mdc`.

This skill is **graph maintenance only**: run extraction/update commands and report status. It does not replace graphify for codebase exploration.

## When to Use

- User runs `/graphify` or `/graphify .`
- User asks to build, refresh, index, or update the knowledge graph
- `graphify-out/graph.json` is missing and exploration is blocked until a graph exists

**When NOT to use:** routine code exploration after the graph exists — use `graphify query`, `graphify path`, or `graphify explain` instead.

## Project Rules Compliance

Read `.cursor/rules/graphify.mdc` before acting. Key points:

- Graph output lives in `graphify-out/`
- After code changes elsewhere, agents run `graphify update .` (AST-only, no API cost)
- Exploration agents must graphify before Read/Grep/Glob unless `graph.json` is absent

## Workflow

### Step 1: Detect current state

From repo root, check whether `graphify-out/graph.json` exists.

### Step 2: Choose mode

| Situation | Command | API key |
|-----------|---------|---------|
| Default — create or refresh code graph | `graphify update .` | Not required |
| User explicitly wants full semantic extraction (docs, INFERRED edges) | `graphify extract .` | Required |

**Default is always `graphify update .`** unless the user asks for full/semantic/deep extraction.

`graphify .` (bare path) invokes full `extract` and fails without an LLM API key when doc files are present. Do **not** run bare `graphify .` unless the user requested full extraction and a key is available.

### Step 3: Run the command

Run from the repository root:

```bash
graphify update .
```

For full extraction (only when explicitly requested):

```bash
graphify extract .
```

**Execution requirements:**

- Run with full permissions (`all`) — sandbox blocks graphify subprocesses
- Do not run inside a restricted sandbox
- Allow several minutes on first build (hundreds of source files)

Optional flags (only when user asks):

- `graphify update . --force` — after large refactors that removed code
- `graphify extract . --no-cluster` — skip clustering
- `graphify extract . --mode deep` — aggressive INFERRED-edge extraction

### Step 4: Verify and report

After a successful run, confirm:

1. `graphify-out/graph.json` exists
2. Report outcome to the user: created vs updated, command used, and any warnings

If verification fails, capture stderr and diagnose:

| Error | Action |
|-------|--------|
| `no LLM API key found` | User asked for full extract — report which keys are accepted (`GEMINI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.) or fall back to `graphify update .` for code-only graph |
| `Operation not permitted` | Re-run with full permissions |
| `Nothing to update or rebuild failed` | Re-run with `--force` or inspect stderr; if graph is stale, try `graphify update . --force` |

### Step 5: Post-build orientation (optional)

If the user wants to explore immediately after indexing:

```bash
graphify query "<question>"
graphify path "<symbol A>" "<symbol B>"
graphify explain "<concept>"
```

If `graphify-out/wiki/index.md` exists, prefer it for navigation. Use `graphify-out/GRAPH_REPORT.md` only for broad architecture review.

## Done When

- `graphify-out/graph.json` exists and is fresh for the requested mode
- User receives a short summary: command run, success/failure, and next step (explore via query/path/explain, or set API key for full extract)
