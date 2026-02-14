"""
RAG Pipeline for project-brain
Indexes the codebase, saves the vector database persistently and answers questions via Ollama.
"""

import json
import hashlib
from pathlib import Path
from typing import Optional
import httpx

from config import load_config

# File types to index
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
    ".cpp", ".c", ".h", ".cs", ".rb", ".php", ".swift", ".kt",
    ".vue", ".svelte", ".html", ".css", ".scss", ".sql",
    ".md", ".mdx", ".yaml", ".yml", ".json", ".toml", ".env.example"
}

DEFAULT_IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
    "project-brain-db", "cdk.out"
}


class RAGPipeline:
    def __init__(self):
        self.config = load_config()
        self.db_path = Path(self.config["database_path"])
        self.project_path = Path(self.config["project_path"])
        self.ollama_url = self.config["ollama_url"]
        self.llm_model = self.config["llm_model"]
        self.embed_model = self.config["embed_model"]
        indexing = self.config.get("indexing", {})
        self._chunk_size = indexing.get("chunk_size", 60)
        self._chunk_overlap = indexing.get("chunk_overlap", 10)
        # Use config ignore_dirs if set, otherwise defaults
        config_ignore = self.config.get("ignore_dirs")
        self._ignore_dirs = set(config_ignore) if config_ignore else DEFAULT_IGNORE_DIRS

        self.db_path.mkdir(parents=True, exist_ok=True)
        self._index_file = self.db_path / "index.json"
        self._chunks_file = self.db_path / "chunks.json"
        self._summary_file = self.db_path / "summary.json"

        # Load existing index if available
        self._index = self._load_json(self._index_file, {})
        self._chunks = self._load_json(self._chunks_file, [])

    def _load_json(self, path: Path, default):
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return default

    def _save_json(self, path: Path, data):
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _file_hash(self, path: Path) -> str:
        return hashlib.md5(path.read_bytes()).hexdigest()

    def _collect_files(self, root: Path) -> list[Path]:
        files = []
        for p in root.rglob("*"):
            if any(part in self._ignore_dirs for part in p.parts):
                continue
            if p.is_file() and p.suffix in CODE_EXTENSIONS:
                files.append(p)
        return files

    def _chunk_file(self, path: Path, chunk_size: int = None, overlap: int = None) -> list[dict]:
        """Split a file into overlapping text chunks with metadata."""
        chunk_size = chunk_size if chunk_size is not None else self._chunk_size
        overlap = overlap if overlap is not None else self._chunk_overlap
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        lines = content.splitlines()
        chunks = []
        step = chunk_size - overlap

        for i in range(0, max(1, len(lines) - overlap), step):
            chunk_lines = lines[i:i + chunk_size]
            text = "\n".join(chunk_lines).strip()
            if not text:
                continue
            chunks.append({
                "text": text,
                "file": str(path.relative_to(self.project_path)),
                "start_line": i + 1,
                "end_line": i + len(chunk_lines)
            })

        return chunks

    async def _get_embedding(self, text: str) -> list[float]:
        """Fetch embedding from Ollama."""
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.embed_model, "prompt": text}
            )
            resp.raise_for_status()
            return resp.json()["embedding"]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def index(self, project_path: Optional[str] = None, force: bool = False) -> str:
        """Index the project codebase. Skips files that have not changed."""
        root = Path(project_path).expanduser() if project_path else self.project_path

        if not root.exists():
            return f"❌ Path does not exist: {root}"

        files = self._collect_files(root)
        current_files = {str(f.resolve()) for f in files}

        # Prune deleted files from index and chunks
        for old_key in list(self._index.keys()):
            if old_key not in current_files:
                del self._index[old_key]
        self._chunks = [
            c for c in self._chunks
            if str((root / c["file"]).resolve()) in current_files
        ]

        new_chunks = []
        indexed = 0
        skipped = 0

        print(f"Found {len(files)} files to index...", file=__import__('sys').stderr)

        for file in files:
            file_hash = self._file_hash(file)

            # Skip if file has not changed
            if not force and self._index.get(str(file)) == file_hash:
                skipped += 1
                # Keep existing chunks for this file
                existing = [c for c in self._chunks if c["file"] == str(file.relative_to(root))]
                new_chunks.extend(existing)
                continue

            # Chunk and embed the file
            chunks = self._chunk_file(file)
            for chunk in chunks:
                try:
                    embedding = await self._get_embedding(chunk["text"])
                    chunk["embedding"] = embedding
                    new_chunks.append(chunk)
                except Exception as e:
                    print(f"Warning: could not embed {file}: {e}", file=__import__('sys').stderr)

            self._index[str(file)] = file_hash
            indexed += 1
            print(f"  ✓ {file.relative_to(root)} ({len(chunks)} chunks)", file=__import__('sys').stderr)

        self._chunks = new_chunks
        self._save_json(self._index_file, self._index)
        self._save_json(self._chunks_file, self._chunks)

        # Generate a new summary if new files were indexed
        if indexed > 0:
            await self._generate_summary(root)

        return (
            f"✅ Indexing complete!\n"
            f"   New/updated files: {indexed}\n"
            f"   Unchanged (skipped): {skipped}\n"
            f"   Total chunks in database: {len(new_chunks)}\n"
            f"   Database saved to: {self.db_path}"
        )

    async def search(self, query: str, n: int = 5) -> str:
        """Semantic search in the codebase."""
        if not self._chunks:
            return "❌ No index found. Run index_project first."

        query_embedding = await self._get_embedding(query)

        scored = []
        for chunk in self._chunks:
            if "embedding" not in chunk:
                continue
            score = self._cosine_similarity(query_embedding, chunk["embedding"])
            scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:n]

        if not top:
            return "No relevant code snippets found."

        result = f"🔍 Top {len(top)} results for: '{query}'\n\n"
        for score, chunk in top:
            result += f"📄 {chunk['file']} (line {chunk['start_line']}-{chunk['end_line']}) [relevance: {score:.2f}]\n"
            result += "```\n" + chunk["text"][:500] + "\n```\n\n"

        return result

    async def ask(self, question: str) -> str:
        """Answer a question about the project using RAG context."""
        if not self._chunks:
            return "❌ No index found. Run index_project first."

        # Retrieve relevant context
        query_embedding = await self._get_embedding(question)
        scored = [
            (self._cosine_similarity(query_embedding, c["embedding"]), c)
            for c in self._chunks if "embedding" in c
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        top_chunks = [c for _, c in scored[:8]]

        # Build context
        context = "\n\n".join([
            f"// {c['file']} line {c['start_line']}-{c['end_line']}\n{c['text']}"
            for c in top_chunks
        ])

        # Load project summary if available
        summary = ""
        if self._summary_file.exists():
            summary_data = self._load_json(self._summary_file, {})
            summary = summary_data.get("summary", "")

        prompt = f"""You are an expert assistant for this codebase. Answer concisely and reference specific files and line numbers where relevant.

PROJECT OVERVIEW:
{summary}

RELEVANT CODE:
{context}

QUESTION: {question}

Answer concretely and reference specific files and line numbers where relevant."""

        # Call Ollama
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            resp.raise_for_status()
            return resp.json()["response"]

    async def get_summary(self) -> str:
        """Return the project overview."""
        if self._summary_file.exists():
            data = self._load_json(self._summary_file, {})
            return data.get("summary", "No summary generated yet.")
        return "No summary found. Run index_project to generate one."

    async def _generate_summary(self, root: Path):
        """Generate an AI summary of the project."""
        # Collect file structure
        files = self._collect_files(root)
        file_tree = "\n".join([
            str(f.relative_to(root)) for f in sorted(files)[:100]
        ])

        # Read README if available
        readme = ""
        for name in ["README.md", "readme.md", "README.txt"]:
            readme_path = root / name
            if readme_path.exists():
                readme = readme_path.read_text(errors="ignore")[:2000]
                break

        prompt = f"""Analyze this codebase and provide a structured summary in English.

README:
{readme or "(no README found)"}

FILE STRUCTURE:
{file_tree}

Include:
1. What the project does (purpose)
2. Tech stack and frameworks
3. Folder structure and architecture
4. Key files and their roles
5. How to run the project (if apparent)"""

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": self.llm_model, "prompt": prompt, "stream": False}
                )
                summary = resp.json()["response"]
        except Exception as e:
            summary = f"Could not generate summary: {e}"

        self._save_json(self._summary_file, {"summary": summary})
        print("  📋 Project summary generated", file=__import__('sys').stderr)
