"""Tests for config loading."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_load_config_missing(tmp_path, monkeypatch):
    """Missing config raises FileNotFoundError."""
    import config as config_module
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "nonexistent.json")
    with pytest.raises(FileNotFoundError, match="Config not found"):
        config_module.load_config()


def test_load_config_env_override(tmp_path, monkeypatch):
    """Environment variables override config."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "project_path": "/original/path",
        "database_path": "/original/db",
        "ollama_url": "http://localhost:11434",
        "llm_model": "test",
        "embed_model": "test",
    }))
    import config as config_module
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_file)
    monkeypatch.setenv("PROJECT_BRAIN_PROJECT_PATH", "/env/override")

    cfg = config_module.load_config()
    assert cfg["project_path"] == "/env/override"
