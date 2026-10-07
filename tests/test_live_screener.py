"""
Live integration test — hits Screener.in. Skipped unless RUN_LIVE=1.
Run with:  RUN_LIVE=1 pytest tests/test_live_screener.py -v
"""

import os
import pytest
from scraper import fetch_company, fetch_peers_for, enrich_with_ev_multiples
from valuation import peer_statistics, implied_share_price

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE") != "1",
    reason="Live network test. Set RUN_LIVE=1 to enable.",
)


@pytest.mark.parametrize("ticker", ["INFY", "TCS", "RELIANCE"])
def test_live_fetch_company(ticker):
    c = fetch_company(ticker)
    assert c["name"]
    assert c["ratios"].get("Current Price") is not None
    assert c["ratios"].get("Market Cap") is not None
    assert c["warehouse_id"] is not None


def test_live_end_to_end():
    c = fetch_company("INFY")
    peers = [enrich_with_ev_multiples(p) for p in fetch_peers_for("INFY", limit=10)]
    assert len(peers) > 0
    import pandas as pd
    stats = peer_statistics(pd.DataFrame(peers))
    assert not stats.empty
    tgt = {
        "sales_cr": c["ratios"].get("Sales"),
        "ebitda_cr": None,
        "eps": c["ratios"].get("EPS"),
        "net_debt_cr": c["ratios"].get("Debt") or 0,
        "shares_cr": c["shares_outstanding_cr"],
        "current_price": c["ratios"].get("Current Price"),
    }
    out = implied_share_price(tgt, stats)
    print("\nLive implied prices for INFY:")
    print(out.to_string(index=False))
