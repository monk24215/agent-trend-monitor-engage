"""CONTENT LOG — a human-reviewed ledger of every headline/message produced
and which vendor (from vendors_2.csv / inputs/product_catalog.json) it was
created for, plus a promote / don't-promote decision.

A delivery edge, like publisher.py and dashboard.py — never touches engine
logic, only reads daily/*.json. Safe to run any number of times: existing
rows, and any decision/notes a human has typed into the CSV, are preserved.
Only genuinely new content_ids get appended.

Rebuild/sync any time:
    python -m tmea.contentlog

tmea.run calls this automatically after every run, so the log never falls
behind. The DECISION column is yours, not the agent's — see
00_constitution/purpose.md, autonomy level 0: "human confirms before they
count as shipped." Nothing in here ever sets promoted/rejected on its own;
new rows always start "pending" and wait for you to edit the CSV (open it
in Excel/Sheets, change the decision column, save).

Content this doesn't auto-populate — full emails/messages you write by
hand outside TMEA (TMEA's constitution refuses to write long-form content)
— you add as a row yourself: same columns, type="email" or "message",
any content_id you like as long as it's unique.
"""
from __future__ import annotations
import csv, glob, os
from .core import ROOT, DAILY, read_json
from .publisher import _load_catalog_map

LOG_PATH = os.path.join(ROOT, "content_log.csv")

FIELDS = [
    "date", "run_id", "content_id", "type", "headline",
    "vendor_id", "vendor_link", "decision", "decided_at", "notes",
]


def _load_existing() -> dict:
    if not os.path.exists(LOG_PATH):
        return {}
    with open(LOG_PATH, newline="", encoding="utf-8") as f:
        return {row["content_id"]: row for row in csv.DictReader(f) if row.get("content_id")}


def _rows_from_daily(catalog: dict) -> list:
    rows = []
    for path in sorted(glob.glob(os.path.join(DAILY, "*.json"))):
        doc = read_json(path)
        run_id = doc.get("run_id") or os.path.splitext(os.path.basename(path))[0]
        for kind, items in (("discovery", doc.get("discovery", [])),
                             ("derived", doc.get("derived", []))):
            for item in items:
                product_id = item.get("product_id", "")
                prod = catalog.get(product_id, {})
                vendor_id = prod.get("clickbank", {}).get("vendor_id", "")
                vendor_link = prod.get("clickbank", {}).get("hoplink", "")
                rows.append({
                    "date": run_id,
                    "run_id": run_id,
                    "content_id": item.get("id", ""),
                    "type": f"headline-{kind}",
                    "headline": item.get("headline", ""),
                    "vendor_id": vendor_id,
                    "vendor_link": vendor_link,
                    "decision": "pending",
                    "decided_at": "",
                    "notes": "",
                })
    return rows


def sync() -> str:
    """Add any new headlines from daily/*.json to content_log.csv without
    touching rows that already exist (so human decisions never get
    clobbered). Returns the path written."""
    catalog = _load_catalog_map()
    existing = _load_existing()
    for row in _rows_from_daily(catalog):
        if row["content_id"] and row["content_id"] not in existing:
            existing[row["content_id"]] = row

    ordered = sorted(existing.values(), key=lambda r: (r.get("date", ""), r.get("content_id", "")))
    with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in ordered:
            w.writerow({k: row.get(k, "") for k in FIELDS})
    return LOG_PATH


if __name__ == "__main__":
    print("content log synced:", sync())
