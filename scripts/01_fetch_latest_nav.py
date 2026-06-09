"""
01_fetch_latest_nav.py
======================
Fetches ALL ~15,000 mutual fund latest NAVs from AMFI in ONE request.
Source: https://www.amfiindia.com/spages/NAVAll.txt (official AMFI data)
Updated daily after ~7 PM IST (after market close).

Output:
    data/latest_nav.csv           → all schemes, latest NAV only
    data/latest_nav_enriched.csv  → with mfapi category/type metadata

Usage:
    python 01_fetch_latest_nav.py              # basic
    python 01_fetch_latest_nav.py --enrich     # add category metadata (slower)
    python 01_fetch_latest_nav.py --output custom_name.csv
"""

import requests
import pandas as pd
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
AMFI_URL     = "https://www.amfiindia.com/spages/NAVAll.txt"
MFAPI_BASE   = "https://api.mfapi.in/mf"
DATA_DIR     = Path(__file__).parent.parent / "data"
TIMEOUT      = 30
# ─────────────────────────────────────────────────────────────────────────────


def fetch_amfi_bulk() -> pd.DataFrame:
    """
    Single HTTP request → all ~15k scheme NAVs instantly.
    AMFI NAVAll.txt format (semicolon-delimited):
        SchemeCode;ISIN-Div-Payout-ISIN;ISIN-Div-Reinvestment;SchemeName;NAV;Date
        (Header lines and blank lines are interleaved with section labels)
    """
    print("⬇️  Fetching AMFI bulk NAV data (single request)...")
    resp = requests.get(AMFI_URL, timeout=TIMEOUT)
    resp.raise_for_status()

    rows        = []
    current_amc = ""

    for line in resp.text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Section header lines look like "Open Ended Schemes(Debt Scheme - Banking and PSU Fund)"
        # AMC name lines don't contain semicolons and aren't the column header
        if ";" not in line:
            if line not in ("Scheme Code;ISIN Div Payout/ ISIN Growth;"
                            "ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date",
                            "Scheme Code;ISIN Div Payout/ISIN Growth;"
                            "ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date"):
                current_amc = line  # treat as AMC / section label
            continue

        parts = line.split(";")
        if len(parts) < 5:
            continue
        if parts[0].strip().lower() == "scheme code":
            continue  # skip header row

        rows.append({
            "scheme_code":  parts[0].strip(),
            "isin_growth":  parts[1].strip(),
            "isin_div":     parts[2].strip(),
            "scheme_name":  parts[3].strip(),
            "nav":          parts[4].strip(),
            "nav_date":     parts[5].strip() if len(parts) > 5 else "",
            "amc_section":  current_amc,
        })

    df = pd.DataFrame(rows)

    # ── Type conversions ──────────────────────────────────────────────────────
    df["scheme_code"] = pd.to_numeric(df["scheme_code"], errors="coerce")
    df["nav"]         = pd.to_numeric(df["nav"], errors="coerce")
    df["nav_date"]    = pd.to_datetime(df["nav_date"], dayfirst=True, errors="coerce")

    # Drop rows where scheme_code or nav couldn't be parsed
    df.dropna(subset=["scheme_code", "nav"], inplace=True)
    df["scheme_code"] = df["scheme_code"].astype(int)
    df.reset_index(drop=True, inplace=True)

    print(f"   ✅ {len(df):,} schemes fetched  |  "
          f"NAV date range: {df['nav_date'].min().date()} → {df['nav_date'].max().date()}")
    return df


def enrich_with_mfapi_meta(df: pd.DataFrame, sample_size: int = None) -> pd.DataFrame:
    """
    Optional: pull category + type metadata from mfapi for each scheme.
    Uses the /mf list endpoint which returns schemeCode + schemeName,
    then merges — no per-scheme API calls needed for basic enrichment.
    """
    print("\n🔗 Enriching with mfapi category metadata...")
    resp = requests.get(MFAPI_BASE, timeout=TIMEOUT)
    resp.raise_for_status()
    meta_list = resp.json()

    meta_df = pd.DataFrame(meta_list).rename(columns={
        "schemeCode": "scheme_code",
        "schemeName": "mfapi_scheme_name"
    })
    meta_df["scheme_code"] = meta_df["scheme_code"].astype(int)

    merged = df.merge(meta_df, on="scheme_code", how="left")
    print(f"   ✅ Matched {merged['mfapi_scheme_name'].notna().sum():,} schemes")
    return merged


def save(df: pd.DataFrame, path: Path, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    size_kb = path.stat().st_size // 1024
    print(f"\n💾 {label}")
    print(f"   Path : {path}")
    print(f"   Rows : {len(df):,}  |  Columns : {len(df.columns)}  |  Size : {size_kb} KB")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--enrich", action="store_true",
                        help="Add category metadata from mfapi")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    df = fetch_amfi_bulk()

    out_path = Path(args.output) if args.output else DATA_DIR / "latest_nav.csv"
    save(df, out_path, "Latest NAV (AMFI bulk)")

    if args.enrich:
        df_rich = enrich_with_mfapi_meta(df)
        rich_path = DATA_DIR / "latest_nav_enriched.csv"
        save(df_rich, rich_path, "Enriched NAV")

    print(f"\n🎉 Done at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
