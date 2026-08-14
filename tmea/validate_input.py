"""Validate an input file against its JSON Schema before the engine touches it.

Design intent: bad input fails LOUDLY here, at the door, rather than silently
corrupting a daily run. Works hand-filled today and API-fed later — same shapes.

Uses `jsonschema` if installed (full validation); otherwise falls back to a
minimal built-in check of required keys so it still runs with zero deps.

CLI:  python -m tmea.validate_input signals inputs/signals.json
"""
import json, sys, os

ROOT = os.path.dirname(os.path.dirname(__file__))
SCHEMA_DIR = os.path.join(ROOT, "inputs", "schemas")

KINDS = {"signals", "feedback", "product_catalog"}


def _load(path):
    with open(path) as f:
        return json.load(f)


def _minimal_check(kind, data, schema):
    # Zero-dep fallback: enforce top-level required keys and array item required keys.
    missing = [k for k in schema.get("required", []) if k not in data]
    if missing:
        raise ValueError(f"{kind}: missing required top-level keys: {missing}")
    for prop, spec in schema.get("properties", {}).items():
        if spec.get("type") == "array" and prop in data:
            item_req = spec.get("items", {}).get("required", [])
            for i, item in enumerate(data[prop]):
                miss = [k for k in item_req if k not in item]
                if miss:
                    raise ValueError(f"{kind}: {prop}[{i}] missing {miss}")
    return "minimal"


def validate(kind, path):
    if kind not in KINDS:
        raise ValueError(f"unknown input kind '{kind}'; expected one of {sorted(KINDS)}")
    schema = _load(os.path.join(SCHEMA_DIR, f"{kind}.schema.json"))
    data = _load(path)
    try:
        import jsonschema  # optional
        jsonschema.validate(instance=data, schema=schema)
        return "full"
    except ImportError:
        return _minimal_check(kind, data, schema)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python -m tmea.validate_input <kind> <path>")
        sys.exit(2)
    mode = validate(sys.argv[1], sys.argv[2])
    print(f"OK ({mode} validation): {sys.argv[2]}")
