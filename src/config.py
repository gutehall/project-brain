"""
Shared configuration for project-brain.
Loads config.json, expands ~ in paths, and validates required keys.
"""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.json"


def load_config() -> dict:
    """Load and validate config. Expands ~ in path values."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config not found: {CONFIG_PATH}\n"
            "Run the install script or copy config/config.example.json to config/config.json"
        )

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    # Expand ~ in paths
    for key in ("project_path", "database_path"):
        if key in config and config[key]:
            config[key] = str(Path(config[key]).expanduser())

    # Validate required keys
    required = ["project_path", "database_path", "ollama_url", "llm_model", "embed_model"]
    missing = [k for k in required if not config.get(k)]
    if missing:
        raise ValueError(f"Config missing required keys: {missing}")

    return config
