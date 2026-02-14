#!/bin/bash
# Index or update the project codebase

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

source .venv/bin/activate 2>/dev/null || true

FORCE=""
if [[ "$1" == "--force" || "$1" == "-f" ]]; then
    FORCE="--force"
    echo "Forced re-indexing (ignoring cache)..."
else
    echo "Indexing project (skipping unchanged files)..."
fi

python3 - <<EOF
import asyncio, sys, json
sys.path.insert(0, "src")

async def main():
    from rag_pipeline import RAGPipeline
    rag = RAGPipeline()
    result = await rag.index(force=${FORCE:+True}${FORCE:-False})
    print(result)

asyncio.run(main())
EOF
