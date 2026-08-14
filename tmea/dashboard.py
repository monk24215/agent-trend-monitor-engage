"""DASHBOARD — a single, reopenable HTML view over every daily brief.

A delivery edge, like publisher.py — reads whatever's in daily/*.json and
never touches engine logic. Rebuild any time with:

    python -m tmea.dashboard

(run_tmea.bat calls this automatically after every run, then opens the
result.) Always writes to the same path — daily/index.html — so there's
exactly one file to keep open/bookmarked/pinned, not a new one per day.
"""
from __future__ import annotations
import os, glob
from .core import DAILY, read_json
from .publisher import CSS, _items, _esc, _load_catalog_map

HISTORY_CSS = """
.history{list-style:none}
.history li{padding:6px 0;border-bottom:1px solid var(--line);
  font-family:ui-monospace,Menlo,monospace;font-size:12px;
  display:flex;justify-content:space-between;gap:12px}
.history a{color:var(--ink);text-decoration:none}
.history a:hover{color:var(--go)}
.history .latest{color:var(--go)}
.empty{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--dim)}
"""


def _history_list(files: list[str], latest_id: str) -> str:
    rows = []
    for f in reversed(files):
        rid = os.path.splitext(os.path.basename(f))[0]
        tag = '<span class="latest">latest</span>' if rid == latest_id else ""
        rows.append(f'<li><a href="{_esc(rid)}.html">{_esc(rid)}</a>{tag}</li>')
    return "".join(rows)


def build() -> str:
    catalog = _load_catalog_map()
    files = sorted(glob.glob(os.path.join(DAILY, "*.json")))

    if not files:
        latest_id = "—"
        body = '<p class="empty">No runs yet. Double-click run_tmea.bat to produce the first one.</p>'
        history_html = ""
    else:
        latest_path = files[-1]
        doc = read_json(latest_path)
        latest_id = doc.get("run_id") or os.path.splitext(os.path.basename(latest_path))[0]
        disc = _items(doc.get("discovery", []), "discovery", catalog)
        deriv = _items(doc.get("derived", []), "derived", catalog)
        body = (
            '<section><div class="sec-head"><h2>The Field — What\'s Moving</h2>'
            f'<div class="rule"></div></div>{disc}</section>'
            '<section><div class="sec-head"><h2>The Angle — Topic × Offer</h2>'
            f'<div class="rule"></div></div>{deriv}</section>'
        )
        history_html = (
            '<section><div class="sec-head"><h2>History</h2><div class="rule"></div></div>'
            f'<ul class="history">{_history_list(files, latest_id)}</ul></section>'
        )

    out = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TMEA Dashboard — latest: {_esc(latest_id)}</title><style>{CSS}{HISTORY_CSS}</style></head><body>
<div class="mast"><h1>TMEA Dashboard</h1><span class="date">latest: {_esc(latest_id)}</span></div>
<span class="tag">Trend Monitor &middot; Engage</span>
{body}
{history_html}
<footer>Rebuilt by tmea.dashboard &middot; reopen daily/index.html any time</footer>
</body></html>"""

    out_path = os.path.join(DAILY, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    return out_path


if __name__ == "__main__":
    print("dashboard written:", build())
