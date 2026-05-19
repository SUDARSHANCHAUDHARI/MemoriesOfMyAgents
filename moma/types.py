from dataclasses import dataclass, field
from typing import Literal, Optional
from datetime import datetime


MemoryType = Literal["pattern", "preference", "architecture", "bug", "workflow", "fact", "conflict", "procedural"]
MemoryScope = Literal["project", "global"]


@dataclass
class SessionIntent:
    raw: str
    task_type: str = "unknown"
    domain: str = ""
    files_mentioned: list[str] = field(default_factory=list)
    goal: str = ""


@dataclass
class Session:
    id: str
    project: str
    project_slug: str
    cwd: str
    agent: str
    started_at: str
    git_branch: str = ""
    model: str = ""
    ended_at: Optional[str] = None
    intent: Optional[SessionIntent] = None


@dataclass
class RawObservation:
    id: str
    session_id: str
    timestamp: str
    tool: str
    tool_input_hash: str
    output_tail: str       # last 4000 chars of output — errors live here
    importance_hint: int   # 1-10 rough signal from hook context


@dataclass
class Memory:
    id: str
    type: MemoryType
    scope: MemoryScope
    project: str           # project_slug, or "global"
    title: str
    content: str
    concepts: list[str]
    files: list[str]
    importance: int        # 1-10
    confidence: float      # 0.0-1.0
    created_at: str
    updated_at: str
    session_ids: list[str]
    supersedes: list[str] = field(default_factory=list)
    superseded_by: Optional[str] = None
    source_observation_ids: list[str] = field(default_factory=list)  # citation provenance
    access_count: int = 0   # strengthens with use (Ebbinghaus reinforcement)
