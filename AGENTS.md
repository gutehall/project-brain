# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Build & Test Commands

```bash
# Install dependencies (use virtual environment)
pip install -r requirements.txt

# Run all tests
pytest tests -v

# Run a single test file
pytest tests/test_rag_pipeline.py -v

# Run a specific test
pytest tests/test_rag_pipeline.py::TestRAGPipelineChunking::test_cosine_similarity_identical -v
```

Tests run without Ollama — they test chunking and similarity logic in isolation.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Interfaces                              │
├───────────────┬──────────────────┬──────────────────────────────┤
│ CLI           │ Warp Aliases     │ Cursor MCP                   │
│ scripts/      │ config/          │ src/mcp_server.py            │
│ brain.py      │ warp_aliases.sh  │ (stdio JSON-RPC)             │
└───────┬───────┴────────┬─────────┴──────────────┬───────────────┘
        │                │                        │
        └────────────────┴────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │         Core Modules            │
        ├─────────────────────────────────┤
        │  rag_pipeline.py                │
        │  - Index codebase → chunks      │
        │  - Embed via Ollama             │
        │  - Search (cosine similarity)   │
        │  - Ask (RAG with LLM)           │
        ├─────────────────────────────────┤
        │  linear_integration.py          │
        │  - AI-draft issues/projects     │
        │  - Create via Linear GraphQL    │
        ├─────────────────────────────────┤
        │  config.py                      │
        │  - Load config/config.json      │
        │  - Env var overrides            │
        └─────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │       External Services         │
        ├─────────────────────────────────┤
        │  Ollama (localhost:11434)       │
        │  - nomic-embed-text (embeddings)│
        │  - deepseek-coder-v2 (LLM)      │
        ├─────────────────────────────────┤
        │  Linear GraphQL API             │
        └─────────────────────────────────┘
```

## Key Entry Points

- **`scripts/brain.py`** — CLI entry point. Parses commands (`ask`, `search`, `index`, `summary`, `linear`, `linear-project`) and delegates to RAGPipeline or linear_integration.
- **`src/mcp_server.py`** — MCP server for Cursor. Implements JSON-RPC over stdio, exposes tools like `ask_project`, `search_code`, `create_linear_issue`.
- **`src/rag_pipeline.py`** — Core RAG logic. Handles file collection, chunking, embedding, vector search, and LLM calls.
- **`src/linear_integration.py`** — Creates Linear issues/projects using AI-drafted content.
- **`src/config.py`** — Configuration loader with env var override support.

## Configuration

Config is loaded from `config/config.json`. Key env var overrides:
- `PROJECT_BRAIN_PROJECT_PATH` → `project_path`
- `PROJECT_BRAIN_DATABASE_PATH` → `database_path`
- `LINEAR_API_KEY` → `linear_api_key`
- `LINEAR_TEAM_ID` → `linear_team_id`

The database is stored at `database_path` (default `~/.project-brain/db/`) with:
- `index.json` — file hash cache for incremental indexing
- `chunks.json` — code chunks with embeddings
- `summary.json` — AI-generated project overview

## Code Patterns

- All async operations use `httpx.AsyncClient` for HTTP calls to Ollama and Linear.
- RAGPipeline lazy-loads in MCP server to avoid slow startup.
- Chunking uses overlapping windows (default 60 lines, 10 overlap) configurable via `indexing.chunk_size` and `indexing.chunk_overlap`.
- Linear integration uses the LLM to draft issue content from free-text descriptions, then extracts JSON from the response.

## Testing Notes

Tests use `RAGPipeline.__new__()` to instantiate without calling `__init__`, avoiding config/Ollama dependencies. Set required attributes manually when testing specific methods.
