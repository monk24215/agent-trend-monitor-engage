"""Deterministic shared spine: path resolution, IO, and the append-only build
log. No model calls here — this is bone, not muscle."""
from __future__ import annotations
import os, json, datetime
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# canonical locations (the layer structure IS the architecture)
CONSTITUTION = os.path.join(ROOT, "00_constitution")
ACTIVE       = os.path.join(ROOT, "01_active_patterns")
COLD_STORE   = os.path.join(ROOT, "02_cold_store")
BUILD_LOG    = os.path.join(ROOT, "build_log")
DAILY        = os.path.join(ROOT, "daily")
INPUTS       = os.path.join(ROOT, "inputs")

LOG_PATH = os.path.join(BUILD_LOG, "log.jsonl")


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> str:
    return datetime.date.today().isoformat()


def read_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)


def read_yaml(path: str) -> Any:
    """Minimal YAML read via pyyaml if present; else a tiny fallback that
    handles the flat list-of-maps our config files use."""
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        return _tiny_yaml(path)


def _tiny_yaml(path: str) -> dict:
    # Zero-dep fallback good enough for our simple registries. Prefer pyyaml.
    import re
    text = open(path).read()
    data: dict = {}
    top_key = None
    cur = None
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if m and not line.startswith(" "):
            top_key = m.group(1)
            rest = m.group(2).strip()
            data[top_key] = [] if rest in ("", "[]") else rest
            if rest == "[]":
                data[top_key] = []
            continue
        if re.match(r"^\s*-\s", line):
            if not isinstance(data.get(top_key), list):
                data[top_key] = []
            cur = {}
            data[top_key].append(cur)
            line = re.sub(r"^\s*-\s", "", line)
        km = re.match(r"^\s*([\w-]+):\s*(.*)$", line)
        if km and cur is not None:
            v = km.group(2).strip().strip('"')
            cur[km.group(1)] = v
    return data


class RunContext:
    """Carries run_id and writes the append-only build log. Passed to every
    agent so the whole run shares one traceable history."""
    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or today()
        os.makedirs(BUILD_LOG, exist_ok=True)

    def log(self, type_: str, detail: dict) -> None:
        entry = {"ts": now_iso(), "type": type_, "run_id": self.run_id, "detail": detail}
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
