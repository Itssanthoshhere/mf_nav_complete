"""
02_fetch_nav_history.py
=======================
Fetches FULL NAV history for all schemes from mfapi.in.
Supports resume (skip already-fetched schemes), date filtering,
and appends new data without re-downloading everything.

This is the slow script (~30–90 min for all 15k schemes).
Use 01_fetch_latest_nav.py for daily latest NAVs.

Usage:
    python 02_fetch_nav_history.py                        # all schemes
    python 02_fetch_nav_history.py --scheme 125497        # single scheme
    python 02_fetch_nav_history.py --resume               # skip already done
    python 02_fetch_nav_history.py --limit 200            # test with 200 schemes
    python 02_fetch_nav_history.py --since 2020-01-01     # only history from date
    python 02_fetch_nav_history.py --fund "HDFC"          # filter by fund house name
"""

import requests
import pandas as pd
import time
import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("Tip: pip install tqdm  for progress bars\n")

# ── Config ────────────────────────────────────────────────────────────────────
MFAPI_BASE  = "https://api.mfapi.in/mf"
DATA_DIR    = Path(__file__).parent.parent / "data"
PROGRESS_F  = DATA_DIR / ".progress.json"   # tracks which schemes were fetched
MAX_WORKERS = 8      # parallel threads (keep ≤10 to be polite)
DELAY       = 0.05   # seconds between requests per thread
TIMEOUT     = 20
CHUNK_SIZE  = 500    # flush to disk every N schemes (avoid RAM blow-up)
# ─────────────────────────────────────────────────────────────────────────────


def load_progress() -> set:
    """Load set of already-fetched scheme codes."""
    if PROGRESS_F.exists():
        with open(PROGRESS_F) as f:
            return set(json.load(f))
    return set()


def save_progress(done: set) -> None:
    PROGRESS_F.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_F, "w") as f:
        json.dump(list(done), f)


def get_all_scheme_codes() -> list[dict]:
    print("📋 Fetching scheme master list...")
    resp = requests.get(MFAPI_BASE, timeout=TIMEOUT)
    resp.raise_for_status()
    schemes = resp.json()
    print(f"   ✅ {len(schemes):,} schemes")
    return schemes


def fetch_history_one(scheme: dict, since_date: pd.Timestamp = None) -> list[dict]:
    """Fetch full history for one scheme. Returns list of row dicts."""
    code = scheme["schemeCode"]
    try:
        time.sleep(DELAY)
        resp = requests.get(f"{MFAPI_BASE}/{code}", timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "SUCCESS":
            return []

        meta = data.get("meta", {})
        rows = []
        for entry in data.get("data", []):
            nav_date = pd.to_datetime(entry.get("date", ""), dayfirst=True, errors="coerce")
            if since_date and pd.notna(nav_date) and nav_date < since_date:
                continue
            rows.append({
                "scheme_code":     code,
                "scheme_name":     meta.get("scheme_name", scheme.get("schemeName", "")),
                "fund_house":      meta.get("fund_house", ""),
                "scheme_type":     meta.get("scheme_type", ""),
                "scheme_category": meta.get("scheme_category", ""),
                "isin_growth":     meta.get("isin_growth", ""),
                "nav_date":        nav_date,
                "nav":             pd.to_numeric(entry.get("nav"), errors="coerce"),
            })
        return rows
    except Exception as e:
        return []


def flush_chunk(all_rows: list, output_path: Path, first_chunk: bool) -> None:
    """Write current batch to CSV (append mode after first chunk)."""
    df = pd.DataFrame(all_rows)
    mode   = "w" if first_chunk else "a"
    header = first_chunk
    df.to_csv(output_path, index=False, mode=mode, header=header)


def run_bulk(schemes: list[dict], output_path: Path,
             since_date: pd.Timestamp, resume: bool) -> None:

    done_codes  = load_progress() if resume else set()
    pending     = [s for s in schemes if s["schemeCode"] not in done_codes]
    total       = len(schemes)
    skipped     = total - len(pending)

    print(f"\n🚀 History fetch: {len(pending):,} schemes to fetch"
          f"  ({skipped:,} skipped / already done)")
    if not pending:
        print("   Nothing to do — all schemes already fetched.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    first_chunk = not (resume and output_path.exists())

    all_rows   = []
    chunk_done = 0
    total_rows = 0

    iterator = pending
    if HAS_TQDM:
        iterator = tqdm(pending, unit="scheme", dynamic_ncols=True)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_history_one, s, since_date): s for s in pending}

        for future in (tqdm(as_completed(futures), total=len(futures), unit="scheme")
                       if HAS_TQDM else as_completed(futures)):
            scheme = futures[future]
            rows   = future.result()
            all_rows.extend(rows)
            total_rows += len(rows)
            done_codes.add(scheme["schemeCode"])
            chunk_done += 1

            # Flush to disk every CHUNK_SIZE schemes
            if chunk_done % CHUNK_SIZE == 0:
                flush_chunk(all_rows, output_path, first_chunk)
                first_chunk = False
                all_rows    = []
                save_progress(done_codes)

    # Final flush
    if all_rows:
        flush_chunk(all_rows, output_path, first_chunk)

    save_progress(done_codes)
    size_mb = output_path.stat().st_size // (1024 * 1024)
    print(f"\n✅ Done — {total_rows:,} rows written → {output_path}  ({size_mb} MB)")


def run_single(scheme_code: int, output_path: Path, since_date: pd.Timestamp) -> None:
    print(f"🔍 Fetching history for scheme {scheme_code}...")
    scheme = {"schemeCode": scheme_code, "schemeName": ""}
    rows   = fetch_history_one(scheme, since_date)

    if not rows:
        print("❌ No data returned.")
        return

    df = pd.DataFrame(rows).sort_values("nav_date")
    df.to_csv(output_path, index=False)
    print(f"✅ {len(df):,} rows → {output_path}")
    print(df.tail(5).to_string(index=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scheme",  type=int,   default=None, help="Single scheme code")
    parser.add_argument("--resume",  action="store_true",      help="Skip already fetched schemes")
    parser.add_argument("--limit",   type=int,   default=None, help="Max number of schemes")
    parser.add_argument("--since",   type=str,   default=None, help="Only history from date (YYYY-MM-DD)")
    parser.add_argument("--fund",    type=str,   default=None, help="Filter scheme names containing this string")
    parser.add_argument("--output",  type=str,   default=None)
    parser.add_argument("--workers", type=int,   default=MAX_WORKERS)
    args = parser.parse_args()

    since_date = pd.to_datetime(args.since) if args.since else None

    if args.scheme:
        out = Path(args.output) if args.output else DATA_DIR / f"scheme_{args.scheme}_history.csv"
        run_single(args.scheme, out, since_date)
        return

    schemes = get_all_scheme_codes()

    if args.fund:
        schemes = [s for s in schemes if args.fund.lower() in s["schemeName"].lower()]
        print(f"   🔎 Filtered to {len(schemes):,} schemes matching '{args.fund}'")

    if args.limit:
        schemes = schemes[:args.limit]
        print(f"   🔬 Limited to first {args.limit} schemes")

    out = Path(args.output) if args.output else DATA_DIR / "all_nav_history.csv"
    run_bulk(schemes, out, since_date, args.resume)


if __name__ == "__main__":
    main()
