# Project Brain



## What it does

- **Indexes your codebase** and saves the vector database persistently to disk
- **Answers questions** about the project with full code context ("Where is error handling done in the API?")
- **Semantic search** across the code ("Show everything related to the Stripe integration")
- **Creates Linear issues** via AI based on a free-text description
- **Auto-updates** via a git hook after every commit

---

## Requirements

- macOS or Linux (Windows via WSL works)
- Python 3.10+
- ~15 GB disk space (for the AI models)
- Ollama (installed automatically by the setup script)

---

## Installation

```bash
# 1. Clone the project
git clone <repo-url> ~/project-brain
cd ~/project-brain

# 2. Run the install script
chmod +x scripts/install.sh
./scripts/install.sh
```

The script automatically installs:
- Ollama (runtime for local models)
- `nomic-embed-text` — embeddings model (~300 MB)
- `deepseek-coder-v2` — LLM optimized for code (~9 GB)

On first run, the install script creates `config/config.json` from `config/config.example.json` if it does not exist.

---

## Configuration

Edit `config/config.json` (created from `config.example.json` on first install):

```json
{
  "project_path": "/this/is/my/project",
  "database_path": "~/.project-brain/db", 
  "ollama_url": "http://localhost:11434",
  "llm_model": "deepseek-coder-v2",
  "embed_model": "nomic-embed-text",
  "linear_api_key": "lin_api_xxxxx",
  "linear_team_id": "TEAM-ID"
}
```

> **Linear API key:** https://linear.app/settings/api  
> **Linear Team ID:** found in the URL when you are on your team page

---

## Index your project

```bash
# First time (indexes everything)
./scripts/index.sh

# Update (skips unchanged files)
./scripts/index.sh

# Force full re-indexing
./scripts/index.sh --force
```

---

## Warp integration

Add to your `~/.zshrc`:

```bash
source ~/project-brain/config/warp_aliases.sh
```

Restart Warp and use directly:

```bash
brain ask "How does authentication work?"
brain search "stripe webhook"
brain index
brain summary
brain linear "App crashes when logging out on iOS"
```

---

## Cursor integration

1. Copy the MCP configuration:

```bash
# Create the directory if it doesn't exist
mkdir -p ~/.cursor

# Copy and edit
cp config/cursor_mcp.json ~/.cursor/mcp.json
```

2. Open `~/.cursor/mcp.json` and replace `REPLACE_WITH_PROJECT_BRAIN_PATH` with your actual project-brain path (e.g. `/Users/you/project-brain`).

3. Restart Cursor.

You can now ask in Cursor Chat:
- *"Use project-brain to explain how the login flow works"*
- *"Search the project for all API endpoints"*
- *"Create a Linear issue: Fix memory leak in WebSocket handling"*

---

## Linear integration

The Linear integration works via:

1. **Cursor Chat** — ask Cursor to call the `create_linear_issue` tool
2. **Warp** — `brain linear "issue description"`
3. **Directly via CLI** — `python3 scripts/brain.py linear "description"`

The AI automatically drafts the title, description and priority based on your text and the project context.

---

## Auto-indexing via git hook

To keep the index up to date after every commit:

```bash
# Install the hook in your code project
cp scripts/git_hook_post_commit.sh /path/to/your-project/.git/hooks/post-commit
chmod +x /path/to/your-project/.git/hooks/post-commit
```

Edit the hook and set `PROJECT_BRAIN_DIR` to your project-brain install path if it differs from `$HOME/project-brain`.

Indexing runs in the background and does not block your workflow.

---

## Architecture

```
Cursor / Warp / CLI
        │
        ▼
   MCP Server (src/mcp_server.py)
        │
   ┌────┴────────┐
   │             │
   ▼             ▼
RAG Pipeline   Linear API
(rag_pipeline.py)   (linear_integration.py)
   │
   ├── Ollama (LLM: deepseek-coder-v2)
   ├── Ollama (Embeddings: nomic-embed-text)
   └── Vector database (~/.project-brain/db/)
           ├── index.json      ← file hash cache
           ├── chunks.json     ← code + embeddings
           └── summary.json    ← project overview
```

---

## Switching models

If you have a less powerful machine, switch to a smaller model in `config.json`:

| Model | Size | Best for |
|-------|------|----------|
| `deepseek-coder-v2` | ~9 GB | Best for code (recommended) |
| `codellama` | ~4 GB | Good balance of performance/size |
| `llama3.2` | ~2 GB | Fast, weaker code understanding |
| `qwen2.5-coder:7b` | ~4 GB | Good code alternative |

```bash
ollama pull qwen2.5-coder:7b
# Update llm_model in config/config.json
```

---

## Troubleshooting

**Config not found**
- Ensure `config/config.json` exists. Run the install script or copy `config/config.example.json` to `config/config.json`.

**Ollama connection refused**
- Start Ollama: `ollama serve` (or launch the Ollama app). The default URL is `http://localhost:11434`.

**Path does not exist**
- Check that `project_path` in `config/config.json` points to a valid directory. Use absolute paths or `~` for home (e.g. `~/.project-brain/db`).

**No index found**
- Run `./scripts/index.sh` or `brain index` to index your project before using ask/search.

---

## Development

- Python dependencies: `pip install -r requirements.txt`
- Source layout: `src/` (RAG pipeline, MCP server, Linear integration), `scripts/` (CLI, install, index)

