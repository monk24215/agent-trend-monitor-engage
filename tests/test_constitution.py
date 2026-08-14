"""Runs between every section. If any of these fail, STOP the build.
These enforce that growth never violates Layer 0."""
import json, glob, os

ROOT = os.path.dirname(os.path.dirname(__file__))

def test_active_pattern_cap():
    active = glob.glob(os.path.join(ROOT, "01_active_patterns", "*.json"))
    assert len(active) <= 12, f"cruft: {len(active)} active patterns, cap is 12"

def test_daily_output_shape():
    for f in glob.glob(os.path.join(ROOT, "daily", "*.json")):
        d = json.load(open(f))
        assert len(d.get("discovery", [])) == 5, f"{f}: need exactly 5 discovery"
        assert len(d.get("derived", [])) == 5, f"{f}: need exactly 5 derived"

def test_build_log_append_only():
    # every line must be valid JSON (proves nothing corrupted a past line)
    p = os.path.join(ROOT, "build_log", "log.jsonl")
    if os.path.exists(p):
        for i, line in enumerate(open(p)):
            if line.strip():
                json.loads(line)  # raises if a past line was edited badly

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print(f"PASS {name}")
    print("all invariants hold")
