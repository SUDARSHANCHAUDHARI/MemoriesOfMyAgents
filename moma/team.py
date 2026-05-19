"""
Team memory — shared namespaced memories across agents and users.
Each team has private + shared scopes.
Stored at: ~/.moma/teams/{team_name}/memories/
Config at: ~/.moma/teams/{team_name}/config.json
"""
import json
from pathlib import Path
from typing import Optional

from .config import MOMA_ROOT
from .storage import slugify, _memory_to_markdown, _parse_memory_markdown
from .types import Memory


def team_root(team_name: str) -> Path:
    return MOMA_ROOT / "teams" / slugify(team_name)


def list_teams() -> list[dict]:
    teams_dir = MOMA_ROOT / "teams"
    if not teams_dir.exists():
        return []
    result = []
    for d in teams_dir.iterdir():
        if d.is_dir():
            cfg = d / "config.json"
            if cfg.exists():
                try:
                    result.append(json.loads(cfg.read_text()))
                except Exception:
                    pass
    return result


def create_team(name: str, description: str = "", members: list[str] = None) -> dict:
    slug = slugify(name)
    root = team_root(name)
    root.mkdir(parents=True, exist_ok=True)
    (root / "memories" / "shared").mkdir(parents=True, exist_ok=True)

    cfg = {
        "name": name,
        "slug": slug,
        "description": description,
        "members": members or [],
        "created_at": _now(),
    }
    cfg_path = root / "config.json"
    tmp = cfg_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2))
    tmp.replace(cfg_path)
    return cfg


def save_team_memory(team_name: str, memory: Memory, visibility: str = "shared") -> None:
    """visibility: 'shared' (all members) or 'private' (local only)."""
    root = team_root(team_name)
    dir_path = root / "memories" / visibility / memory.type
    dir_path.mkdir(parents=True, exist_ok=True)
    content = _memory_to_markdown(memory)
    path = dir_path / f"{memory.id}.md"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def list_team_memories(team_name: str, visibility: str = "shared") -> list[dict]:
    root = team_root(team_name)
    mem_dir = root / "memories" / visibility
    if not mem_dir.exists():
        return []
    results = []
    for path in sorted(mem_dir.rglob("*.md")):
        parsed = _parse_memory_markdown(path.read_text())
        if parsed:
            parsed["team"] = team_name
            parsed["visibility"] = visibility
            results.append(parsed)
    return results


def get_team_config(team_name: str) -> Optional[dict]:
    cfg_path = team_root(team_name) / "config.json"
    if not cfg_path.exists():
        return None
    try:
        return json.loads(cfg_path.read_text())
    except Exception:
        return None


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
