"""Tests for RAG pipeline chunking and similarity."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag_pipeline import RAGPipeline


class TestRAGPipelineChunking:
    """Test chunking logic without needing Ollama."""

    def test_cosine_similarity_identical(self):
        """Identical vectors should have similarity 1.0."""
        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline._chunk_size = 60
        pipeline._chunk_overlap = 10
        pipeline.project_path = Path("/tmp")
        vec = [1.0, 2.0, 3.0]
        assert pipeline._cosine_similarity(vec, vec) == 1.0

    def test_cosine_similarity_orthogonal(self):
        """Orthogonal vectors should have similarity 0."""
        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline._chunk_size = 60
        pipeline._chunk_overlap = 10
        pipeline.project_path = Path("/tmp")
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert abs(pipeline._cosine_similarity(a, b)) < 0.001

    def test_cosine_similarity_opposite(self):
        """Opposite vectors should have similarity -1."""
        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline._chunk_size = 60
        pipeline._chunk_overlap = 10
        pipeline.project_path = Path("/tmp")
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(pipeline._cosine_similarity(a, b) + 1.0) < 0.001

    def test_cosine_similarity_zero_vector(self):
        """Zero vector should return 0."""
        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline._chunk_size = 60
        pipeline._chunk_overlap = 10
        pipeline.project_path = Path("/tmp")
        assert pipeline._cosine_similarity([0, 0], [1, 1]) == 0.0


class TestChunkFile:
    """Test _chunk_file with a temp file."""

    def test_chunk_file_basic(self, tmp_path):
        """Chunking produces overlapping chunks."""
        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline._chunk_size = 10
        pipeline._chunk_overlap = 2
        pipeline.project_path = tmp_path

        file_path = tmp_path / "test.py"
        file_path.write_text("line1\nline2\nline3\nline4\nline5\n" * 5)

        chunks = pipeline._chunk_file(file_path)
        assert len(chunks) >= 1
        for c in chunks:
            assert "text" in c
            assert "file" in c
            assert "start_line" in c
            assert "end_line" in c
            assert c["file"] == "test.py"

    def test_chunk_file_empty(self, tmp_path):
        """Empty file returns empty chunks."""
        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline._chunk_size = 10
        pipeline._chunk_overlap = 2
        pipeline.project_path = tmp_path

        file_path = tmp_path / "empty.py"
        file_path.write_text("")

        chunks = pipeline._chunk_file(file_path)
        assert chunks == []
