"""
Shared configuration for project-brain.
Loads config.json, expands ~ in paths, validates required keys.
Supports environment variable overrides.
"""

import json
import os
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.json"

# Env vars that override config (when set)
ENV_OVERRIDES = {
    "PROJECT_BRAIN_PROJECT_PATH": "project_path",
    "PROJECT_BRAIN_DATABASE_PATH": "database_path",
    "PROJECT_BRAIN_OLLAMA_URL": "ollama_url",
    "LINEAR_API_KEY": "linear_api_key",
    "LINEAR_TEAM_ID": "linear_team_id",
}


def load_config() -> dict[str, Any]:
    """Load and validate config. Expands ~ in path values. Applies env overrides."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config not found: {CONFIG_PATH}\n"
            "Run the install script or copy config/config.example.json to config/config.json"
        )

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    # Apply env overrides
    for env_key, config_key in ENV_OVERRIDES.items():
        val = os.environ.get(env_key)
        if val:
            config[config_key] = val

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
