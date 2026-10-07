"""
Unit tests for scraper.py — HTML parsing with fixtures, no live network.
"""

from unittest.mock import patch, MagicMock
import pytest
import responses
from bs4 import BeautifulSoup

from scraper import (
    _to_float,
    parse_top_ratios,
    parse_warehouse_id,
    fetch_peers,
    fetch_company,
    enrich_with_ev_multiples,
    BASE_URL,
)


# ---------- _to_float ----------

@pytest.mark.parametrize("raw,expected", [
    ("1,23,456.78", 123456.78),
    ("₹ 1,234", 1234.0),
    ("12.3%", 12.3),
    ("500 Cr.", 500.0),
    ("", None),
    ("-", None),
    ("N/A", None),
    (None, None),
    ("abc 42.5 xyz", 42.5),
    ("-15.25", -15.25),
])
def test_to_float(raw, expected):
    assert _to_float(raw) == expected


# ---------- parse_top_ratios ----------

SAMPLE_RATIOS_HTML = """
<html><body>
<ul id="top-ratios">
  <li><span class="name">Market Cap</span>
      <span class="value">₹ <span class="number">6,74,543</span> Cr.</span></li>
  <li><span class="name">Current Price</span>
      <span class="value">₹ <span class="number">1,623</span></span></li>
  <li><span class="name">Stock P/E</span>
      <span class="value"><span class="number">26.4</span></span></li>
  <li><span class="name">ROCE</span>
      <span class="value"><span class="number">39.5</span> %</span></li>
  <li><span class="name">Debt</span>
      <span class="value">₹ <span class="number">8,500</span> Cr.</span></li>
</ul>
<div data-warehouse-id="12345">x</div>
</body></html>
"""


def test_parse_top_ratios():
    soup = BeautifulSoup(SAMPLE_RATIOS_HTML, "html.parser")
    ratios = parse_top_ratios(soup)
    assert ratios["Market Cap"] == 674543.0
    assert ratios["Current Price"] == 1623.0
    assert ratios["Stock P/E"] == 26.4
    assert ratios["ROCE"] == 39.5


def test_parse_warehouse_id():
    soup = BeautifulSoup(SAMPLE_RATIOS_HTML, "html.parser")
    assert parse_warehouse_id(soup) == "12345"


# ---------- fetch_peers (mocked HTTP) ----------

SAMPLE_PEERS_HTML = """
<table>
<thead><tr>
  <th>S.No.</th><th>Name</th><th>CMP</th><th>P/E</th>
  <th>Mar Cap</th><th>Sales</th><th>ROCE</th>
</tr></thead>
<tbody>
<tr>
  <td>1</td>
  <td><a href="/company/TCS/consolidated/">TCS</a></td>
  <td>3,500</td><td>28.5</td><td>12,80,000</td><td>2,40,000</td><td>52.3</td>
</tr>
<tr>
  <td>2</td>
  <td><a href="/company/WIPRO/consolidated/">Wipro</a></td>
  <td>420</td><td>22.1</td><td>2,20,000</td><td>90,000</td><td>18.5</td>
</tr>
<tr>
  <td></td>
  <td>Median: 73 Co.</td>
  <td>218.65</td><td>19.12</td><td>891.56</td><td>85.66</td><td>22.12</td>
</tr>
</tbody>
</table>
"""


@responses.activate
def test_fetch_peers_parses_table():
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/company/12345/peers/",
        body=SAMPLE_PEERS_HTML, status=200,
    )
    peers = fetch_peers("12345", consolidated=True)
    assert len(peers) == 2
    assert peers[0]["Ticker"] == "TCS"
    assert peers[0]["Mar Cap"] == 1280000.0
    assert peers[0]["P/E"] == 28.5
    assert peers[1]["Ticker"] == "WIPRO"
    assert peers[1]["Sales"] == 90000.0


@responses.activate
def test_fetch_peers_handles_bad_status():
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/company/999/peers/",
        status=404,
    )
    assert fetch_peers("999") == []


# ---------- fetch_company (mocked HTTP) ----------

FULL_COMPANY_HTML = f"""
<html><body>
<h1>Infosys Ltd</h1>
{SAMPLE_RATIOS_HTML}
</body></html>
"""


@responses.activate
def test_fetch_company_integration():
    responses.add(
        responses.GET,
        f"{BASE_URL}/company/INFY/consolidated/",
        body=FULL_COMPANY_HTML, status=200,
    )
    company = fetch_company("infy")
    assert company["ticker"] == "INFY"
    assert "Infosys" in company["name"]
    assert company["ratios"]["Market Cap"] == 674543.0
    assert company["warehouse_id"] == "12345"
    # Shares derived = Mcap / CMP
    assert round(company["shares_outstanding_cr"], 2) == round(674543 / 1623, 2)


# ---------- enrich_with_ev_multiples ----------

def test_enrich_ev_sales():
    row = {"Mar Cap": 100000, "Sales": 20000, "P/E": 25}
    out = enrich_with_ev_multiples(row)
    assert out["EV"] == 100000
    assert out["EV/Sales"] == 5.0
    assert out["EV/EBITDA"] is None
    assert out["P/E"] == 25


def test_enrich_missing_sales():
    row = {"Mar Cap": 100000, "P/E": 25}
    out = enrich_with_ev_multiples(row)
    assert out["EV/Sales"] is None


def test_enrich_zero_sales():
    row = {"Mar Cap": 100000, "Sales": 0, "P/E": 25}
    out = enrich_with_ev_multiples(row)
    assert out["EV/Sales"] is None
