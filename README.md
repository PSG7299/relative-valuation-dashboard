# 📊 Relative Valuation Dashboard

A one-click Streamlit app that pulls live Indian equity data from **Screener.in**, builds a peer-comparison set for any Nifty 100 company, and tells you whether the stock is **UNDERVALUED**, **FAIRLY VALUED**, or **OVERVALUED** relative to its peers.

Built for quick, defensible relative valuation — the kind of multiples-based analysis an investment banker or buy-side analyst does in Excel, but automated end-to-end.

---

## 📋 Table of contents

1. [What it does](#what-it-does)
2. [Quick start (Windows)](#quick-start-windows)
3. [How to use the dashboard](#how-to-use-the-dashboard)
4. [How the valuation math works](#how-the-valuation-math-works)
5. [How the scraper works](#how-the-scraper-works)
6. [File-by-file breakdown](#file-by-file-breakdown)
7. [Running the tests](#running-the-tests)
8. [Known limitations](#known-limitations)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)

---

## What it does

Given a target company (e.g. TCS, Infosys, Reliance), the app:

1. Scrapes the target's own financials from Screener.in
2. Scrapes the top 10 peers Screener assigns to the same sector
3. Calculates three valuation multiples for each peer: **P/E**, **EV/Sales**, **EV/EBITDA**
4. Computes **peer statistics** — Median, Mean, Min, Max, 25th & 75th percentile
5. Applies the chosen peer stat (default: Median) to the target's financials to derive an **implied share price** for each multiple
6. Compares implied price to current market price → emits a **valuation signal**

**Example output for TCS @ ₹2,080:**

| Multiple | Peer Median | Implied Price (₹) | vs CMP | Signal |
|---|---|---|---|---|
| EV/Sales | 8.5× | 1,840 | −11.5% | FAIRLY VALUED |
| EV/EBITDA | 18× | 2,350 | +13.0% | FAIRLY VALUED |
| P/E | 25× | 2,780 | +33.7% | UNDERVALUED |
| **Overall** | — | — | **+11.7%** | **FAIRLY VALUED** |

---

## Quick start (Windows)

### Prerequisites
- Windows 10/11
- Python 3.10 or newer ([python.org](https://www.python.org/downloads/)) — tick **"Add Python to PATH"** during install
- Internet connection (for live Screener.in data)

### Setup (first time only)

| # | Step |
|---|---|
| 1 | Download/clone this repo into a folder, e.g. `F:\relative_valuation_app\` |
| 2 | Double-click **`run.bat`** |
| 3 | Wait ~2 min — it creates a virtual environment and installs dependencies |
| 4 | A browser window opens at `http://localhost:8501` |

### Subsequent launches

Just double-click **`run.bat`** again — opens in 2 seconds.

### To stop

Close the browser tab, go to the terminal window, press `Ctrl + C` → `Y`.

---

## How to use the dashboard

### Sidebar inputs

| Control | What it does |
|---|---|
| **Pick ticker from** | Choose source: Nifty 50 / Nifty Next 50 / Nifty 100 / Manual |
| **Company dropdown** | Pick a company by name (resolves to Screener ticker automatically) |
| **Peer stat to apply** | Which statistic drives the implied price — Median (default), Mean, P25, P75 |
| **Number of peers** | 3-15 peers (default 10) |
| **Compute real EV/EBITDA** | If ticked, deep-scrapes each peer's P&L for Operating Profit — slower but gives real EV/EBITDA |
| **Target financials (override)** | Manually enter Sales / EBITDA / EPS / Net Debt — overrides auto-fetched values |
| **Run Valuation** | Executes the pipeline |

### Output sections (top to bottom)

1. **Header strip** — Company name, ticker, view (consolidated/standalone), timestamp of fetch
2. **KPI metrics** — Current Price, Market Cap, Stock P/E, ROCE
3. **Peer Set table** — Each peer's CMP, P/E, Mar Cap, Sales, EV, EV/Sales, (EV/EBITDA if deep-scrape on), ROCE
4. **Peer Multiple Statistics** — Median / Mean / Min / Max / P25 / P75 per multiple
5. **Target financials used** (expandable) — Shows each number plugged into the math and where it came from
6. **Implied Share Price** — One row per multiple with Implied EV, Equity, Price, Upside %, Signal badge
7. **Overall Valuation Signal** — Weighted-average verdict badge
8. **Download CSV** — Export the implied-price table

### Signal thresholds

| Upside vs CMP | Verdict |
|---|---|
| > +15% | 🟢 **UNDERVALUED** |
| −15% to +15% | 🟡 **FAIRLY VALUED** |
| < −15% | 🔴 **OVERVALUED** |

---

## How the valuation math works

Relative valuation = "what multiple do similar companies trade at, and what does that imply for this one?"

### Step 1 — Pull peer multiples

For each peer:

```
EV           = Market Cap (+ Debt − Cash, if deep-scrape on)
EV/Sales     = EV ÷ TTM Sales
EV/EBITDA    = EV ÷ TTM Operating Profit    (if deep-scrape on)
P/E          = Price ÷ TTM EPS                (direct from Screener)
```

### Step 2 — Compute peer statistics

For each multiple across all peers:

| Stat | Why it matters |
|---|---|
| **Median** | Default. Robust to outliers (e.g. one peer at 500× P/E won't skew it) |
| **Mean** | Simple average — easy to explain, but outlier-sensitive |
| **P25 / P75** | Interquartile range — use P25 for a bearish case, P75 for bullish |

### Step 3 — Apply chosen stat to target

```
Implied EV              = Peer Median EV/Sales   × Target Sales
Implied Equity Value    = Implied EV − Target Net Debt
Implied Share Price     = Implied Equity Value ÷ Shares Outstanding

(For P/E: Implied Share Price = Peer Median P/E × Target EPS, directly)
```

### Step 4 — Signal

```
Upside % = (Implied Price ÷ Current Price − 1) × 100

If Upside > +15%  → UNDERVALUED  (price should rise to match peers)
If Upside < -15%  → OVERVALUED   (price should fall)
Else              → FAIRLY VALUED
```

Overall signal = average upside across all available multiples → same thresholds.

### Where target financials come from

| Field | Source |
|---|---|
| Current Price | Screener top-ratios ribbon |
| Market Cap | Screener top-ratios ribbon |
| Stock P/E | Screener top-ratios ribbon |
| Sales (TTM) | Deep-scrape target's Quarterly P&L → sum of last 4 Q Sales |
| EBITDA (TTM) | Deep-scrape target's Quarterly P&L → sum of last 4 Q Operating Profit |
| EPS (TTM) | **Derived**: Current Price ÷ Stock P/E |
| Net Debt | Deep-scrape target's Balance Sheet → latest Borrowings |
| Shares Outstanding | **Derived**: Market Cap ÷ Current Price |

---

## How the scraper works

### Target company page

**URL**: `https://www.screener.in/company/{TICKER}/consolidated/`

Falls back to `/company/{TICKER}/` (standalone) if consolidated 404s. The code tries consolidated first because it's the right view for conglomerates like Reliance or Tata Motors.

**What's parsed:**
- `<h1>` → company name
- `<ul id="top-ratios">` → Market Cap, Current Price, Stock P/E, ROCE, etc.
- `data-warehouse-id` attribute → numeric ID needed for the peers API
- `<section id="quarters">` → Quarterly P&L (for Sales/EBITDA TTM)
- `<section id="balance-sheet">` → Borrowings (for Net Debt)

### Peers endpoint

**URL**: `https://www.screener.in/api/company/{warehouse_id}/peers/?consolidated=true`

Returns an HTML table with 11 columns:
`S.No., Company, CMP Rs., P/E, Mar Cap Rs.Cr., Div Yld %, NP Qtr Rs.Cr., Qtr Profit Var %, Sales Qtr Rs.Cr., Qtr Sales Var %, ROCE %`

Parsed with `pandas.read_html` (robust against Screener's `<thead>`-less table structure). Hyperlinks are extracted separately via BeautifulSoup to get the ticker for each peer.

### Rate limiting & caching

- No explicit rate limit — Screener tolerates ~1 request/second comfortably
- Peer P&L results are cached in a Python dict (`_PNL_CACHE`) for the session's lifetime
- A full run = 1 (target page) + 1 (peers API) + up to 10 (peer P&L pages if deep-scrape on) = max 12 HTTP calls

---

## File-by-file breakdown

```
relative_valuation_app/
├── app.py                   # Streamlit UI + orchestration
├── scraper.py               # Screener.in scraping + parsing
├── valuation.py             # Peer stats, implied prices, signal math
├── tickers.py               # Nifty 50 + Next 50 ticker lists for dropdowns
├── requirements.txt         # Python dependencies
├── run.bat                  # One-click launcher (creates venv, installs, launches)
├── run_tests.bat            # Automated test runner
├── pytest.ini               # pytest configuration
├── diagnose.py              # Standalone diagnostic (dumps raw Screener response)
├── README.md                # This file
└── tests/
    ├── conftest.py          # Makes imports work from tests folder
    ├── test_valuation.py    # 23 tests for valuation math — 100% coverage
    ├── test_scraper.py      # 18 tests for scraping logic (mocked HTTP)
    └── test_live_screener.py # Live Screener integration tests (opt-in)
```

### `app.py` (Streamlit UI)
- Sidebar with ticker picker (dropdown or manual), peer settings, target financial overrides
- Main pane renders KPI cards, peer table, stats table, implied-price table, verdict badge
- Shows timestamp, data source URL, and the source of each target financial

### `scraper.py` (Screener.in scraper)
- `fetch_company(ticker)` — target company page
- `fetch_peers_for(ticker, limit)` — peer list via Screener's internal AJAX endpoint
- `fetch_pnl_ttm(ticker)` — deep-scrape P&L and Balance Sheet (used for target + optionally peers)
- `enrich_with_ev_multiples(peer)` — adds EV, EV/Sales from peer-table data
- `enrich_with_deep_pnl(peer)` — adds EBITDA, real EV/EBITDA, Debt (requires `fetch_pnl_ttm` per peer)
- Session-level cache so repeated queries on same ticker are instant

### `valuation.py` (math)
- `peer_statistics(df, multiples)` — Median/Mean/Min/Max/P25/P75/N per multiple, filters out junk values
- `implied_share_price(target, peer_stats, stat)` — EV/Sales, EV/EBITDA, P/E → implied price
- `overall_signal(implied_df)` — averages upside across multiples → single verdict
- Signal thresholds in `_signal()`: ±15%

### `tickers.py` (dropdown data)
- `NIFTY_50`: 50 companies
- `NIFTY_NEXT_50`: 47 companies
- `ALL_TICKERS`: combined dict

---

## Running the tests

Double-click **`run_tests.bat`** — runs 41 offline unit tests + 4 live Screener tests.

### What's tested

| Suite | Count | Covers |
|---|---|---|
| `test_valuation.py` | 23 | Peer stats accuracy, implied-price math per multiple, signal thresholds, edge cases (zero shares, missing metrics, empty data) |
| `test_scraper.py` | 18 | Number parsing (`"₹ 1,23,456"` → float), top-ratios HTML, warehouse ID extraction, mocked peers API, EV enrichment |
| `test_live_screener.py` | 4 | Live integration — fetches INFY, TCS, RELIANCE and runs the full pipeline. Requires internet. |

### Expected result

```
============================== 41 passed in 0.85s ==============================
Coverage: valuation.py 100% · scraper.py 81% · overall 88%
```

### Running specific suites

```cmd
pytest tests/test_valuation.py           # math only
pytest tests/test_scraper.py             # scraping only
set RUN_LIVE=1 && pytest tests/test_live_screener.py   # live Screener hits
```

---

## Known limitations

| Limitation | Workaround |
|---|---|
| **EBITDA not in Screener's peer-table API** — must deep-scrape each peer | Enable "Compute real EV/EBITDA" checkbox (adds ~10-15s) |
| **Cash not reliably exposed on balance sheet** — EV uses gross Debt not Net Debt | For cash-rich firms (TCS, Infosys), true EV/EBITDA is ~5-10% lower than shown |
| **Banks/NBFCs don't have "Operating Profit"** — EV/EBITDA shows None | Use P/E and P/B for financial-sector peers (P/B not yet in dashboard) |
| **Screener's auto-peer list isn't always ideal** — e.g. Tata Motors gets paired with all auto OEMs including CV players | Future enhancement: custom-peer-ticker override |
| **One year of P&L / balance sheet data** — scraper only grabs latest Qs, not historical trends | Beyond scope — use Screener directly for trend analysis |
| **No DCF, no comparable transactions** — pure trading multiples only | By design — this is a *relative* valuation tool |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Python not on PATH — reinstall and tick "Add to PATH" during install |
| `run.bat` closes instantly | Open `cmd`, `cd` to the folder, type `run.bat` to see the error |
| Browser doesn't open | Manually visit `http://localhost:8501` |
| `Failed to fetch data for XXX: 404` | Ticker doesn't exist on Screener. Check `screener.in` manually, or try without `/consolidated/` |
| All peer cells show `None` | You're on an older version of `scraper.py` — ensure it uses `pandas.read_html` |
| EBITDA always `None` | "Compute real EV/EBITDA" checkbox isn't ticked (it's off by default) |
| Port 8501 already in use | Edit `run.bat`, change last line to `streamlit run app.py --server.port 8502` |
| `ModuleNotFoundError` | Delete `.venv` folder and re-run `run.bat` to force fresh install |

### Diagnostic mode

If something seems off, run the standalone diagnostic:

```cmd
cd /d F:\relative_valuation_app
.venv\Scripts\activate
set SCRAPER_DEBUG=1
python diagnose.py
```

Dumps the raw Screener response to `peers_debug.html` and prints column structure.

---

## FAQ

**Q: Can I use this for US stocks or crypto?**
A: No — hardcoded to Screener.in which only covers Indian listed equities (NSE/BSE).

**Q: Why Median and not Mean by default?**
A: Peer multiples have long right tails (one peer at 100× P/E is common). Median gives a more defensible central tendency.

**Q: Why ±15% as the UNDERVALUED/OVERVALUED threshold?**
A: Standard sell-side convention — anything within ±15% is "noise" given multiple-choice uncertainty. Below −15% / above +15% is a conviction call.

**Q: Can I change the signal thresholds?**
A: Yes — edit `_signal()` in `valuation.py`. Two integer constants to change.

**Q: Does it store or share my searches?**
A: No. Zero telemetry. Everything runs locally. Only outbound HTTP is to `screener.in`.

**Q: Can I add more companies to the dropdown?**
A: Yes — append to the dicts in `tickers.py`. Format: `"Display Name": "SCREENER_TICKER"`.

**Q: Is the data real-time?**
A: Depends on Screener. Price data refreshes with ~15-min delay (end-of-day for free Screener accounts). Financials update quarterly.

**Q: What's EBITDA proxied by here, exactly?**
A: Screener's "Operating Profit" line in the Quarterly P&L — this = Sales − Operating Expenses, before Other Income, Interest, Depreciation, and Tax. Close to EBITDA for non-financial firms.

**Q: Why doesn't it work for banks like HDFC Bank?**
A: Bank valuation uses P/B and P/E (not EV multiples) since EV isn't meaningful for financial firms. The P/E row will populate; EV rows will show None — this is expected and correct.

**Q: Where do the peer lists come from?**
A: Screener's own internal classification (sector + sub-industry match). You can see the same peers if you visit the company's page on screener.in directly.

**Q: Can I run this on Mac / Linux?**
A: Yes — ignore `run.bat`. Install deps with `pip install -r requirements.txt` and launch with `streamlit run app.py`.

---

## Credits

- **Data source**: [Screener.in](https://www.screener.in/) — all equity data scraped from their public pages
- **Stack**: Python 3.10+, Streamlit, pandas, requests, BeautifulSoup4, pytest

## License

For personal / educational use. Respect Screener.in's terms of service — don't hammer their servers.

## Disclaimer

**Not investment advice.** This tool produces indicative relative-valuation estimates based on peer multiples. Multiples-based valuation is one input among many; always validate with full fundamental analysis, management quality assessment, and macro context before any investment decision.
