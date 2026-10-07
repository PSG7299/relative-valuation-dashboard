"""
diagnose.py — one-off probe to see what Screener's peer AJAX actually returns.
Run:  python diagnose.py
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.screener.in/",
}

TICKER = "TCS"

# 1. Get warehouse_id from the main page
print(f"=== Step 1: fetching main page for {TICKER}")
r = requests.get(f"https://www.screener.in/company/{TICKER}/consolidated/",
                 headers=HEADERS, timeout=20)
print(f"HTTP {r.status_code}, {len(r.text)} bytes")
soup = BeautifulSoup(r.text, "html.parser")
el = soup.find(attrs={"data-warehouse-id": True})
warehouse_id = el["data-warehouse-id"] if el else None
print(f"warehouse_id = {warehouse_id}")

if not warehouse_id:
    print("!! Could not find warehouse_id. Dumping first 2000 chars of main page:")
    print(r.text[:2000])
    exit(1)

# 2. Hit the peers endpoint
print(f"\n=== Step 2: hitting peers endpoint")
url = f"https://www.screener.in/api/company/{warehouse_id}/peers/"
r = requests.get(url, headers=HEADERS, params={"consolidated": "true"}, timeout=20)
print(f"HTTP {r.status_code}, {len(r.text)} bytes")
print(f"Content-Type: {r.headers.get('Content-Type')}")

# Save for inspection
with open("peers_raw.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print("Saved full response to peers_raw.html")

# 3. Show first 1500 chars of response
print("\n=== Step 3: first 1500 chars of response ===")
print(r.text[:1500])

# 4. Try parsing with pandas
print("\n=== Step 4: pandas.read_html output ===")
try:
    dfs = pd.read_html(r.text)
    print(f"Found {len(dfs)} tables")
    for i, df in enumerate(dfs):
        print(f"\n--- Table {i} ---")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(df.head(3).to_string())
except Exception as e:
    print(f"pandas failed: {e}")

# 5. Try BeautifulSoup
print("\n=== Step 5: raw table structure via BS4 ===")
soup2 = BeautifulSoup(r.text, "html.parser")
tables = soup2.find_all("table")
print(f"BS4 found {len(tables)} table(s)")
for i, t in enumerate(tables):
    rows = t.find_all("tr")
    print(f"Table {i}: {len(rows)} rows")
    if rows:
        print(f"  First row has {len(rows[0].find_all(['th','td']))} cells")
        print(f"  First row text: {rows[0].get_text(' | ', strip=True)[:200]}")
        if len(rows) > 1:
            print(f"  Second row text: {rows[1].get_text(' | ', strip=True)[:200]}")
