"""
scraper.py — final working version
Confirmed against Screener's actual peers endpoint (2026-10-07).
Columns returned: S.No., Company, CMP Rs., P/E, Mar Cap Rs.Cr., Div Yld %,
NP Qtr Rs.Cr., Qtr Profit Var %, Sales Qtr Rs.Cr., Qtr Sales Var %, ROCE %.
"""

import re
import os
import io
import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import Dict, List, Optional

BASE_URL = "https://www.screener.in"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.screener.in/",
}
SUMMARY_ROWS = {"LTM", "MEDIAN", "INDUSTRY", "AVERAGE", "AGGREGATE", "", "NAN"}
DEBUG = os.getenv("SCRAPER_DEBUG") == "1"


# ---------- Helpers ----------

def _to_float(x) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x) if pd.notna(x) else None
    t = str(x).strip().replace(",", "").replace("₹", "").replace("%", "").replace("Cr.", "").strip()
    if t in ("", "-", "N/A", "nan", "NaN"):
        return None
    try:
        return float(t)
    except ValueError:
        m = re.search(r"-?\d+(\.\d+)?", t)
        return float(m.group()) if m else None


def _get_soup(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def _find_val(row: Dict, candidates) -> Optional[float]:
    """Substring-based lookup across row keys (case-insensitive)."""
    for cand in candidates:
        c = cand.lower()
        for k, v in row.items():
            if k in ("Name", "Ticker"):
                continue
            if c in str(k).lower():
                return _to_float(v)
    return None


# ---------- Core Scrape ----------

def parse_top_ratios(soup: BeautifulSoup) -> Dict[str, Optional[float]]:
    ratios: Dict[str, Optional[float]] = {}
    for li in soup.select("ul#top-ratios li"):
        name_tag = li.find("span", class_="name")
        value_tag = li.find("span", class_="value")
        if not name_tag or not value_tag:
            continue
        name = name_tag.get_text(strip=True)
        number_tag = value_tag.find("span", class_="number")
        value_text = number_tag.get_text(strip=True) if number_tag else value_tag.get_text(" ", strip=True)
        ratios[name] = _to_float(value_text)
    return ratios


def parse_warehouse_id(soup: BeautifulSoup) -> Optional[str]:
    el = soup.find(attrs={"data-warehouse-id": True})
    if el:
        return el["data-warehouse-id"]
    m = re.search(r'warehouse-id[\"\s:=]+(\d+)', soup.decode())
    return m.group(1) if m else None


def fetch_peers(warehouse_id: str, consolidated: bool = True) -> List[Dict]:
    """Peers AJAX returns headerless-<thead> HTML; pandas.read_html handles it correctly."""
    url = f"{BASE_URL}/api/company/{warehouse_id}/peers/"
    params = {"consolidated": "true" if consolidated else "false"}
    r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    if r.status_code != 200:
        return []
    html = r.text

    if DEBUG:
        with open("peers_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[peers] saved {len(html)} bytes")

    # Hyperlinks → tickers
    soup = BeautifulSoup(html, "html.parser")
    ticker_by_name: Dict[str, str] = {}
    for a in soup.select("table a[href*='/company/']"):
        nm = a.get_text(strip=True)
        tk = a["href"].strip("/").split("/")[1]
        ticker_by_name[nm] = tk

    try:
        dfs = pd.read_html(io.StringIO(html))
    except ValueError:
        return []
    if not dfs:
        return []
    df = dfs[0]
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [" ".join(str(c) for c in tup if str(c) != "nan").strip() for tup in df.columns]
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]

    if DEBUG:
        print(f"[peers] columns: {list(df.columns)}")
        print(df.head(3).to_string())

    # Screener uses "Company" (not "Name") for the name column
    name_col = next((c for c in df.columns if c.lower() in ("company", "name")),
                    df.columns[1] if len(df.columns) > 1 else None)
    if name_col is None:
        return []

    peers: List[Dict] = []
    for _, r in df.iterrows():
        name = str(r[name_col]).strip()
        # Summary rows can carry a suffix, e.g. "Median: 73 Co."
        if name.split(":")[0].strip().upper() in SUMMARY_ROWS:
            continue
        row = {"Name": name, "Ticker": ticker_by_name.get(name, name)}
        for col in df.columns:
            if col == name_col:
                continue
            row[col] = _to_float(r[col])
        peers.append(row)
    return peers


def fetch_company(ticker: str) -> Dict:
    """
    Try /consolidated/ first; fall back to the standalone page if that 404s
    (some companies don't publish consolidated financials).
    """
    ticker = ticker.strip().upper().replace(" ", "")
    urls_to_try = [
        f"{BASE_URL}/company/{ticker}/consolidated/",
        f"{BASE_URL}/company/{ticker}/",
    ]
    last_error = None
    soup = None
    used_url = None
    for u in urls_to_try:
        try:
            r = requests.get(u, headers=HEADERS, timeout=20)
            if r.status_code == 404:
                last_error = f"404 at {u}"
                continue
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            used_url = u
            break
        except requests.HTTPError as e:
            last_error = str(e)
            continue
    if soup is None:
        raise ValueError(
            f"Could not find ticker '{ticker}' on Screener.in. "
            f"Tried consolidated + standalone views. {last_error or ''}"
        )

    name_tag = soup.find("h1")
    name = name_tag.get_text(strip=True) if name_tag else ticker
    ratios = parse_top_ratios(soup)
    warehouse_id = parse_warehouse_id(soup)
    mcap = ratios.get("Market Cap")
    cmp_price = ratios.get("Current Price")
    shares_cr = (mcap / cmp_price) if (mcap and cmp_price) else None
    return {
        "ticker": ticker,
        "name": name,
        "url": used_url,
        "view": "consolidated" if "consolidated" in used_url else "standalone",
        "ratios": ratios,
        "shares_outstanding_cr": shares_cr,
        "warehouse_id": warehouse_id,
    }


def fetch_peers_for(ticker: str, limit: int = 10) -> List[Dict]:
    company = fetch_company(ticker)
    if not company["warehouse_id"]:
        return []
    peers = fetch_peers(company["warehouse_id"], consolidated=True)
    peers = [p for p in peers if p["Ticker"].upper() != ticker.upper()]
    return peers[:limit]


# ---------- Enrichment ----------

def enrich_with_ev_multiples(peer_row: Dict) -> Dict:
    """
    Screener peer columns (confirmed): CMP Rs., P/E, Mar Cap Rs.Cr., Div Yld %,
    NP Qtr Rs.Cr., Qtr Profit Var %, Sales Qtr Rs.Cr., Qtr Sales Var %, ROCE %.
    EV ≈ Market Cap (debt/cash not exposed). EV/EBITDA stays None.
    """
    cmp_  = _find_val(peer_row, ["CMP"])
    pe    = _find_val(peer_row, ["P/E"])
    mcap  = _find_val(peer_row, ["Mar Cap", "Market Cap"])
    sales = _find_val(peer_row, ["Sales Qtr", "Sales TTM", "Sales"])
    roce  = _find_val(peer_row, ["ROCE"])
    divy  = _find_val(peer_row, ["Div Yld", "Dividend Yield"])
    np_q  = _find_val(peer_row, ["NP Qtr"])

    ev = mcap
    ev_sales = (ev / sales) if (ev and sales and sales > 0) else None

    peer_row["CMP"]       = cmp_
    peer_row["P/E"]       = pe
    peer_row["Mar Cap"]   = mcap
    peer_row["Sales"]     = sales
    peer_row["ROCE"]      = roce
    peer_row["Div Yld"]   = divy
    peer_row["NP Qtr"]    = np_q
    peer_row["EV"]        = ev
    peer_row["EV/Sales"]  = ev_sales
    peer_row["EV/EBITDA"] = None
    return peer_row


# ---------- Deep-scrape: EBITDA, Debt from each peer's own page ----------

_PNL_CACHE: Dict[str, Dict] = {}  # ticker → {"ebitda_ttm": float, "debt": float, "sales_ttm": float}


def fetch_pnl_ttm(ticker: str) -> Dict[str, Optional[float]]:
    """
    Scrape peer's own page for:
      - Operating Profit TTM (= sum of last 4 quarters) → EBITDA proxy
      - Latest Debt (from Balance Sheet)
      - Sales TTM (sanity check)
    Cached per-ticker for the Python process.
    """
    ticker = ticker.strip().upper()
    if ticker in _PNL_CACHE:
        return _PNL_CACHE[ticker]

    result = {"ebitda_ttm": None, "debt": None, "sales_ttm": None}
    try:
        for suffix in ("/consolidated/", "/"):
            url = f"{BASE_URL}/company/{ticker}{suffix}"
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                break
        else:
            _PNL_CACHE[ticker] = result
            return result

        soup = BeautifulSoup(r.text, "html.parser")

        # --- Quarters P&L: Operating Profit + Sales TTM
        q_section = soup.find("section", {"id": "quarters"})
        if q_section:
            for row in q_section.select("table tbody tr"):
                cells = row.find_all("td")
                if not cells:
                    continue
                label = cells[0].get_text(" ", strip=True).lower()
                values = [_to_float(c.get_text(" ", strip=True)) for c in cells[1:]]
                values = [v for v in values if v is not None]
                if not values:
                    continue
                last4 = values[-4:] if len(values) >= 4 else values
                if "operating profit" in label and result["ebitda_ttm"] is None:
                    result["ebitda_ttm"] = sum(last4)
                elif label in ("sales", "revenue") and result["sales_ttm"] is None:
                    result["sales_ttm"] = sum(last4)

        # --- Balance Sheet: Borrowings (debt)
        bs_section = soup.find("section", {"id": "balance-sheet"})
        if bs_section:
            for row in bs_section.select("table tbody tr"):
                cells = row.find_all("td")
                if not cells:
                    continue
                label = cells[0].get_text(" ", strip=True).lower()
                if "borrowing" in label:
                    nums = [_to_float(c.get_text(" ", strip=True)) for c in cells[1:]]
                    nums = [n for n in nums if n is not None]
                    if nums:
                        result["debt"] = nums[-1]  # latest column
                    break

    except Exception as e:
        if DEBUG:
            print(f"[pnl] {ticker}: {e}")

    _PNL_CACHE[ticker] = result
    return result


def enrich_with_deep_pnl(peer_row: Dict) -> Dict:
    """Call after enrich_with_ev_multiples to add real EV/EBITDA using per-peer page scrape."""
    tk = peer_row.get("Ticker")
    if not tk:
        return peer_row
    pnl = fetch_pnl_ttm(tk)
    ebitda = pnl.get("ebitda_ttm")
    debt = pnl.get("debt") or 0

    mcap = peer_row.get("Mar Cap")
    if mcap is not None and ebitda:
        ev = mcap + debt            # cash not reliably exposed → gross-debt EV
        peer_row["EV"] = ev
        peer_row["EV/EBITDA"] = ev / ebitda if ebitda > 0 else None
        peer_row["EBITDA (TTM)"] = ebitda
        peer_row["Debt"] = debt
        # Refresh EV/Sales with real EV too
        sales = peer_row.get("Sales")
        if sales and sales > 0:
            peer_row["EV/Sales"] = ev / sales
    return peer_row


if __name__ == "__main__":
    tgt = fetch_company("TCS")
    print(tgt["name"], tgt["ratios"])
    for p in fetch_peers_for("TCS", limit=5):
        p = enrich_with_ev_multiples(p)
        p = enrich_with_deep_pnl(p)
        print(p)
