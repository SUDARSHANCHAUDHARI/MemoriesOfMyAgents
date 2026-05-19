"""
Multi-agent leases — file-based mutual exclusion.
Prevents two agents from writing the same memory or session simultaneously.

Usage:
  with acquire_lease("memory:mem_123") as ok:
      if ok:
          # do the write
      else:
          # lease held by another agent
"""
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from .config import MOMA_ROOT

LEASES_DIR = MOMA_ROOT / "locks"
DEFAULT_TTL = 30  # seconds — lease auto-expires


def _lease_path(resource_id: str) -> Path:
    safe = resource_id.replace("/", "_").replace(":", "__")
    return LEASES_DIR / f"{safe}.lock"


def acquire(resource_id: str, holder: str = "", ttl: int = DEFAULT_TTL) -> bool:
    """Try to acquire a lease. Returns True if successful."""
    LEASES_DIR.mkdir(parents=True, exist_ok=True)
    path = _lease_path(resource_id)

    # Check if existing lease is expired
    if path.exists():
        try:
            data = json.loads(path.read_text())
            if time.time() - data.get("acquired_at", 0) < data.get("ttl", ttl):
                return False  # held by someone else
        except Exception:
            pass  # corrupted lock — take it

    data = {"resource_id": resource_id, "holder": holder or str(os.getpid()), "acquired_at": time.time(), "ttl": ttl}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(path)
    return True


def release(resource_id: str) -> None:
    path = _lease_path(resource_id)
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


def is_held(resource_id: str) -> Optional[dict]:
    """Return lease info if held and not expired, else None."""
    path = _lease_path(resource_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data.get("acquired_at", 0) < data.get("ttl", DEFAULT_TTL):
            return data
    except Exception:
        pass
    return None


def list_active() -> list[dict]:
    LEASES_DIR.mkdir(parents=True, exist_ok=True)
    active = []
    now = time.time()
    for p in LEASES_DIR.glob("*.lock"):
        try:
            data = json.loads(p.read_text())
            age = now - data.get("acquired_at", 0)
            if age < data.get("ttl", DEFAULT_TTL):
                data["age_seconds"] = round(age, 1)
                active.append(data)
            else:
                p.unlink(missing_ok=True)  # clean up expired
        except Exception:
            pass
    return active


def release_all_expired() -> int:
    LEASES_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    now = time.time()
    for p in LEASES_DIR.glob("*.lock"):
        try:
            data = json.loads(p.read_text())
            if now - data.get("acquired_at", 0) >= data.get("ttl", DEFAULT_TTL):
                p.unlink(missing_ok=True)
                count += 1
        except Exception:
            p.unlink(missing_ok=True)
            count += 1
    return count


@contextmanager
def acquire_lease(resource_id: str, holder: str = "", ttl: int = DEFAULT_TTL) -> Generator[bool, None, None]:
    ok = acquire(resource_id, holder=holder, ttl=ttl)
    try:
        yield ok
    finally:
        if ok:
            release(resource_id)
