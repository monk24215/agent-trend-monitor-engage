#!/usr/bin/env python3
"""
Kutt link creator for sl.defendsurviveprepare.com

Creates short links of the form:

    https://sl.defendsurviveprepare.com/<vendor>  ->  <target URL>

using the Kutt API (POST /links), per https://docs.kutt.to/.

SETUP
-----
1. pip install requests
2. Set your Kutt API key:
       export KUTT_API_KEY="94vIiZpoIuaFo9x3t-1DUk-FZBWkXiHFa2n-b07D"
   (Find it in your Kutt account settings -> API Key.)
3. If you're on a self-hosted Kutt instance (not kutt.it), also set:
       export KUTT_API_BASE="https://your-kutt-host/api/v2"
4. IMPORTANT: sl.defendsurviveprepare.com must already be added as a
   custom domain on your Kutt account (Settings -> Domains, or via
   --add-domain below) with its DNS CNAME'd to your Kutt server, and
   verified. Custom links against a domain that isn't registered/verified
   will be rejected by the API.

USAGE
-----
    # Single link
    python3 kutt_vendor_links.py --vendor acme --target "https://linktoshortn.com"

    # Bulk from CSV (columns: vendor,target)
    python3 kutt_vendor_links.py --csv vendors.csv

    # See what would be sent without calling the API
    python3 kutt_vendor_links.py --csv vendors.csv --dry-run

    # One-time: register the domain on your Kutt account first
    python3 kutt_vendor_links.py --add-domain
"""

import argparse
import csv
import os
import sys
import time

import requests

DOMAIN = "sl.defendsurviveprepare.com"
API_BASE = os.environ.get("KUTT_API_BASE", "https://kutt.it/api/v2")
API_KEY = os.environ.get("KUTT_API_KEY")


def _headers() -> dict:
    return {"X-API-KEY": API_KEY, "Content-Type": "application/json"}


def add_domain(homepage: str | None = None) -> dict:
    """One-time setup: register DOMAIN on the Kutt account (must already
    have working DNS pointed at the Kutt server)."""
    payload = {"address": DOMAIN}
    if homepage:
        payload["homepage"] = homepage
    resp = requests.post(f"{API_BASE}/domains", json=payload, headers=_headers(), timeout=15)
    print(resp.status_code, resp.text)
    resp.raise_for_status()
    return resp.json()


def create_link(vendor: str, target: str, reuse: bool = True, dry_run: bool = False) -> dict:
    """Create/point sl.defendsurviveprepare.com/<vendor> -> target."""
    payload = {
        "target": target,
        "customurl": vendor,
        "domain": DOMAIN,
        "reuse": reuse,
    }

    if dry_run:
        print(f"[DRY RUN] {DOMAIN}/{vendor}  ->  {target}")
        return payload

    resp = requests.post(f"{API_BASE}/links", json=payload, headers=_headers(), timeout=15)

    if resp.status_code == 200:
        data = resp.json()
        print(f"OK    {DOMAIN}/{vendor}  ->  {target}   ({data.get('link')})")
        return data

    print(f"FAIL  {DOMAIN}/{vendor}  ->  {target}   [{resp.status_code}] {resp.text}", file=sys.stderr)
    return {"error": resp.status_code, "body": resp.text}


def run_csv(path: str, dry_run: bool) -> list:
    results = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vendor = (row.get("vendor") or "").strip()
            target = (row.get("target") or "").strip()
            if not vendor or not target:
                continue
            results.append(create_link(vendor, target, dry_run=dry_run))
            time.sleep(0.3)  # gentle rate limiting
    return results


def main():
    parser = argparse.ArgumentParser(
        description=f"Create vendor short links on {DOMAIN} via the Kutt API"
    )
    parser.add_argument("--vendor", help="Vendor slug, e.g. 'acme' -> sl.defendsurviveprepare.com/acme")
    parser.add_argument("--target", help="Destination URL for --vendor")
    parser.add_argument("--csv", help="CSV file with columns: vendor,target")
    parser.add_argument("--add-domain", action="store_true", help="Register the domain on your Kutt account first, then exit")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without calling the API")
    args = parser.parse_args()

    if not args.dry_run and not API_KEY:
        sys.exit("Set KUTT_API_KEY in your environment first (your Kutt account API key).")

    if args.add_domain:
        add_domain()
        return

    if args.csv:
        run_csv(args.csv, args.dry_run)
    elif args.vendor and args.target:
        create_link(args.vendor, args.target, dry_run=args.dry_run)
    else:
        parser.error("Provide --add-domain, --csv FILE, or both --vendor and --target")


if __name__ == "__main__":
    main()
