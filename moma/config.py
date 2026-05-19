import json
import os
from pathlib import Path


MOMA_ROOT = Path(os.environ.get("MOMA_ROOT", Path.home() / ".moma"))

DEFAULTS = {
    "version": "0.1.0",
    "compression": {
        "model": "claude-haiku-4-5-20251001",
        "max_memories_per_session": 5,
        "min_importance": 3,
    },
    "injection": {
        "enabled": True,
        "max_tokens": 2000,
        "weights": {
            "importance": 0.40,
            "recency": 0.35,
            "file_overlap": 0.25,
        },
    },
    "guardlocks": [],
    "ignore_paths": [
        ".env", ".env.*", "*.pem", "*.key", "id_rsa", "id_ed25519",
        "*.jks", "*.keystore", "local.properties", "keystore.properties",
        "node_modules", ".git",
    ],
    "secret_patterns": [
        r"api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9\-_]{20,}",
        r"secret\s*[:=]\s*['\"]?[A-Za-z0-9\-_]{20,}",
        r"password\s*[:=]\s*['\"]?.{8,}",
        r"sk-[A-Za-z0-9]{20,}",
        r"ghp_[A-Za-z0-9]{36}",
        r"AKIA[A-Z0-9]{16}",
    ],
}


def load() -> dict:
    config_path = MOMA_ROOT / "config.json"
    if not config_path.exists():
        return DEFAULTS.copy()
    with open(config_path) as f:
        saved = json.load(f)
    merged = DEFAULTS.copy()
    merged.update(saved)
    return merged


def save(config: dict) -> None:
    config_path = MOMA_ROOT / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
