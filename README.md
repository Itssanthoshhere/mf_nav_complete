# 📈 MF NAV Complete — Indian Mutual Fund Data Fetcher

Automated daily fetcher for all Indian mutual fund NAV data.
Sources: **AMFI** (bulk latest) + **mfapi.in** (history per scheme).

---

## 🗂 Project Structure

```
mf_nav_complete/
├── scripts/
│   ├── 01_fetch_latest_nav.py      # AMFI bulk latest NAV — all schemes, 1 request
│   ├── 02_fetch_nav_history.py     # Full history per scheme from mfapi.in
│   └── 03_incremental_update.py   # Smart daily updater (runs via scheduler)
├── powerquery/
│   └── mf_nav_queries.pq          # All Power Query M scripts for Excel / Power BI
├── scheduler/
│   ├── setup_scheduler_mac.sh     # Mac launchd auto-scheduler
│   ├── setup_cron.sh              # Linux/Mac cron alternative
│   └── github_actions_workflow.yml # Cloud scheduler (no PC needed)
├── data/                           # Created automatically on first run
│   ├── latest_nav.csv              # All schemes — latest NAV
│   ├── nav_history_incremental.csv # Daily appended history
│   ├── update_log.csv              # Run history log
│   └── .progress.json             # Resume tracker for history fetch
└── requirements.txt
```

---

## ⚡ Quick Start (5 minutes)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Fetch all latest NAVs RIGHT NOW (single request, instant)
```bash
python scripts/01_fetch_latest_nav.py
# → data/latest_nav.csv  (~15,000 rows)
```

### 3. Set up daily auto-update (Mac)
```bash
chmod +x scheduler/setup_scheduler_mac.sh
./scheduler/setup_scheduler_mac.sh
# Runs every day at 9:30 PM automatically
```

---

## 📋 Script Reference

### `01_fetch_latest_nav.py` — Fast bulk fetch (AMFI)
```bash
python scripts/01_fetch_latest_nav.py                  # basic
python scripts/01_fetch_latest_nav.py --enrich         # add mfapi metadata
python scripts/01_fetch_latest_nav.py --output my.csv  # custom output path
```
- **Source**: `https://www.amfiindia.com/spages/NAVAll.txt`
- **Speed**: ~2 seconds for all 15,000 schemes
- **Output columns**: scheme_code, isin_growth, isin_div, scheme_name, nav, nav_date, amc_section

---

### `02_fetch_nav_history.py` — Full history (mfapi.in)
```bash
python scripts/02_fetch_nav_history.py                        # all schemes
python scripts/02_fetch_nav_history.py --scheme 125497        # single scheme
python scripts/02_fetch_nav_history.py --fund "HDFC"          # filter by name
python scripts/02_fetch_nav_history.py --since 2020-01-01     # from date only
python scripts/02_fetch_nav_history.py --resume               # skip already fetched
python scripts/02_fetch_nav_history.py --limit 100            # test with 100 schemes
```
- **Speed**: ~30–90 min for all schemes (parallel, 8 threads)
- **Resume**: if interrupted, add `--resume` to skip already-fetched schemes
- **Output columns**: scheme_code, scheme_name, fund_house, scheme_type, scheme_category, isin_growth, nav_date, nav

---

### `03_incremental_update.py` — Daily smart updater
```bash
python scripts/03_incremental_update.py          # silent run
python scripts/03_incremental_update.py --notify # print summary
```
- Compares existing CSV with fresh AMFI data
- Only fetches what changed since last run
- Appends to incremental history file
- Logs every run to `data/update_log.csv`

---

## 🔄 Scheduling Options

### Option A — Mac launchd (recommended for Mac)
```bash
./scheduler/setup_scheduler_mac.sh

# Useful commands after setup:
tail -f /tmp/mfnav_updater.log                           # view live logs
launchctl unload ~/Library/LaunchAgents/com.mfnav.updater.plist  # stop
launchctl load  ~/Library/LaunchAgents/com.mfnav.updater.plist   # restart
```

### Option B — Cron (Mac/Linux)
```bash
./scheduler/setup_cron.sh

crontab -l                  # verify it was added
tail -f /tmp/mfnav_cron.log # view logs
crontab -e                  # edit or remove
```

### Option C — GitHub Actions (cloud, no PC needed)
1. Push this project to GitHub
2. Copy `scheduler/github_actions_workflow.yml` to `.github/workflows/fetch_mf_nav.yml`
3. Push — GitHub runs it every weekday at 9:30 PM IST automatically
4. Data is committed back to the repo daily
5. Access CSV at: `https://raw.githubusercontent.com/YOU/REPO/main/data/latest_nav.csv`

---

## 📊 Power Query (Excel / Power BI)

Open `powerquery/mf_nav_queries.pq` — it contains 4 queries:

| Query | Description | How to use |
|-------|-------------|-----------|
| **Q1 MF_Latest_NAV** | AMFI bulk — all schemes live | New Blank Query → paste → Done |
| **Q2 MF_SchemeHistory** | Full history for one scheme | Paste, change `schemeCode` |
| **Q3 MF_HDFCSchemes** | Filter Q1 by fund house | References Q1, change filter |
| **Q4 MF_FromCSV** | Load from Python CSV output | Paste, change file path |

### How to add in Excel:
1. **Data** → **Get Data** → **From Other Sources** → **Blank Query**
2. **Home** → **Advanced Editor**
3. Paste the query block → **Done**
4. **Close & Load**
5. Click **Refresh All** anytime for fresh data

### How to add in Power BI:
1. **Home** → **Transform Data** → **New Source** → **Blank Query**
2. **Advanced Editor** → paste → **Done** → **Close & Apply**

> **Tip**: Q1 (AMFI bulk) is the fastest — one HTTP request for all schemes.
> For Power BI reports, use Q1 as the base and filter in Power BI.

---

## 📅 Data Source & Update Times

| Source | URL | Update time (IST) | Speed |
|--------|-----|-------------------|-------|
| AMFI bulk | `amfiindia.com/spages/NAVAll.txt` | ~7 PM daily | ~2 sec |
| mfapi history | `api.mfapi.in/mf/{code}` | ~8 PM daily | ~30–90 min for all |

AMFI publishes NAVs after NSE/BSE market close (~3:30 PM) + processing delay.
Scheduler runs at **9:30 PM IST** to ensure data is ready.

---

## 📁 Output CSV Columns

### `latest_nav.csv`
| Column | Type | Description |
|--------|------|-------------|
| scheme_code | int | Unique AMFI scheme code |
| isin_growth | str | ISIN for growth option |
| isin_div | str | ISIN for dividend option |
| scheme_name | str | Full scheme name |
| nav | float | Latest NAV (₹) |
| nav_date | date | NAV date |
| amc_section | str | AMC / category section |

### `all_nav_history.csv` / `nav_history_incremental.csv`
Same as above plus: fund_house, scheme_type, scheme_category

---

## 🔗 Find Scheme Codes

- Browse: `https://api.mfapi.in/mf` (JSON list of all codes)
- Search: `https://api.mfapi.in/mf/search?q=HDFC`
- AMFI website: `https://www.amfiindia.com/nav-history`
