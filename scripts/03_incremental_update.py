"""
03_incremental_update.py
========================
Smart daily updater — only fetches what's NEW since the last run.
Designed to run via cron/scheduler every evening after 7 PM IST.

Logic:
  1. Load existing latest_nav.csv  (from 01_fetch_latest_nav.py)
  2. Fetch fresh AMFI bulk data
  3. Compare — find schemes whose NAV date has changed
  4. For those schemes, fetch updated NAV from mfapi
  5. Append new rows to history file (if you maintain one)
  6. Overwrite latest_nav.csv with fresh data
  7. Write a daily log entry

Usage:
    python 03_incremental_update.py
    python 03_incremental_update.py --notify   # print summary to stdout (for cron emails)
"""

import requests
import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime, date

AMFI_URL    = "https://www.amfiindia.com/spages/NAVAll.txt"
DATA_DIR    = Path(__file__).parent.parent / "data"
LOG_FILE    = DATA_DIR / "update_log.csv"
TIMEOUT     = 30


def fetch_amfi_bulk() -> pd.DataFrame:
    resp = requests.get(AMFI_URL, timeout=TIMEOUT)
    resp.raise_for_status()

    rows = []
    for line in resp.text.strip().split("\n"):
        line = line.strip()
        if ";" not in line:
            continue
        parts = line.split(";")
        if len(parts) < 5 or parts[0].strip().lower() == "scheme code":
            continue
        rows.append({
            "scheme_code": parts[0].strip(),
            "isin_growth": parts[1].strip(),
            "isin_div":    parts[2].strip(),
            "scheme_name": parts[3].strip(),
            "nav":         parts[4].strip(),
            "nav_date":    parts[5].strip() if len(parts) > 5 else "",
        })

    df = pd.DataFrame(rows)
    df["scheme_code"] = pd.to_numeric(df["scheme_code"], errors="coerce")
    df["nav"]         = pd.to_numeric(df["nav"], errors="coerce")
    df["nav_date"]    = pd.to_datetime(df["nav_date"], dayfirst=True, errors="coerce")
    df.dropna(subset=["scheme_code", "nav"], inplace=True)
    df["scheme_code"] = df["scheme_code"].astype(int)
    return df


def run_update(notify: bool) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    run_time  = datetime.now()
    stats     = {"run_time": run_time.isoformat(), "status": "ok"}

    # ── Load existing data ────────────────────────────────────────────────────
    latest_path = DATA_DIR / "latest_nav.csv"
    if latest_path.exists():
        old_df = pd.read_csv(latest_path, parse_dates=["nav_date"])
        old_map = dict(zip(old_df["scheme_code"], old_df["nav_date"]))
        stats["schemes_before"] = len(old_df)
    else:
        old_map = {}
        stats["schemes_before"] = 0

    # ── Fetch fresh AMFI data ─────────────────────────────────────────────────
    print(f"[{run_time:%Y-%m-%d %H:%M:%S}] Fetching fresh AMFI data...")
    new_df = fetch_amfi_bulk()
    stats["schemes_total"]   = len(new_df)
    stats["amfi_fetch_ok"]   = True

    # ── Compare old vs new ────────────────────────────────────────────────────
    new_df["is_updated"] = new_df.apply(
        lambda r: (
            r["scheme_code"] not in old_map or
            pd.isna(old_map.get(r["scheme_code"])) or
            r["nav_date"] > old_map.get(r["scheme_code"], pd.NaT)
        ),
        axis=1
    )

    updated_schemes  = new_df[new_df["is_updated"]]
    unchanged        = new_df[~new_df["is_updated"]]
    stats["schemes_updated"]   = len(updated_schemes)
    stats["schemes_unchanged"] = len(unchanged)
    stats["new_schemes"]       = len(new_df) - len(old_map)

    print(f"   Total schemes : {len(new_df):,}")
    print(f"   Updated today : {len(updated_schemes):,}")
    print(f"   Unchanged     : {len(unchanged):,}")
    print(f"   New schemes   : {stats['new_schemes']}")

    # ── Overwrite latest_nav.csv ──────────────────────────────────────────────
    save_df = new_df.drop(columns=["is_updated"])
    save_df.to_csv(latest_path, index=False)
    print(f"\n💾 Saved → {latest_path}")

    # ── Append updated rows to history file ───────────────────────────────────
    history_path = DATA_DIR / "nav_history_incremental.csv"
    if len(updated_schemes) > 0:
        hist_rows = updated_schemes.drop(columns=["is_updated"]).copy()
        mode   = "a" if history_path.exists() else "w"
        header = not history_path.exists()
        hist_rows.to_csv(history_path, index=False, mode=mode, header=header)
        print(f"📜 Appended {len(hist_rows):,} rows → {history_path}")

    # ── Write log ─────────────────────────────────────────────────────────────
    log_row = pd.DataFrame([{
        "run_time":          run_time.strftime("%Y-%m-%d %H:%M:%S"),
        "schemes_total":     stats["schemes_total"],
        "schemes_updated":   stats["schemes_updated"],
        "schemes_unchanged": stats["schemes_unchanged"],
        "new_schemes":       stats["new_schemes"],
        "status":            "ok",
    }])
    log_mode   = "a" if LOG_FILE.exists() else "w"
    log_header = not LOG_FILE.exists()
    log_row.to_csv(LOG_FILE, index=False, mode=log_mode, header=log_header)

    if notify:
        print(f"\n{'='*50}")
        print(f"MF NAV Update Summary — {run_time:%d %b %Y %H:%M}")
        print(f"  Schemes fetched : {stats['schemes_total']:,}")
        print(f"  NAVs updated    : {stats['schemes_updated']:,}")
        print(f"  Unchanged       : {stats['schemes_unchanged']:,}")
        print(f"  Log             : {LOG_FILE}")
        print(f"{'='*50}")

    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--notify", action="store_true",
                        help="Print a formatted summary (for cron email notifications)")
    args = parser.parse_args()
    run_update(args.notify)


if __name__ == "__main__":
    main()
