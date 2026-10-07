"""
Unit tests for valuation.py — pure math, no network.
"""

import math
import pandas as pd
import pytest

from valuation import (
    peer_statistics,
    implied_share_price,
    overall_signal,
    _signal,
    _round,
)


# ---------- Fixtures ----------

@pytest.fixture
def peers_df():
    return pd.DataFrame([
        {"Name": "A", "EV/Sales": 2.0, "EV/EBITDA": 10.0, "P/E": 20.0},
        {"Name": "B", "EV/Sales": 3.0, "EV/EBITDA": 12.0, "P/E": 25.0},
        {"Name": "C", "EV/Sales": 4.0, "EV/EBITDA": 14.0, "P/E": 30.0},
        {"Name": "D", "EV/Sales": 5.0, "EV/EBITDA": 16.0, "P/E": 35.0},
        {"Name": "E", "EV/Sales": 6.0, "EV/EBITDA": 18.0, "P/E": 40.0},
    ])


@pytest.fixture
def target():
    return {
        "sales_cr":      10000,
        "ebitda_cr":     2500,
        "eps":           50.0,
        "net_debt_cr":   1000,
        "shares_cr":     100,
        "current_price": 1200,
    }


# ---------- peer_statistics ----------

class TestPeerStatistics:
    def test_median_matches_manual(self, peers_df):
        stats = peer_statistics(peers_df)
        row = stats[stats["Multiple"] == "EV/Sales"].iloc[0]
        assert row["Median"] == 4.0
        assert row["Mean"] == 4.0
        assert row["Min"] == 2.0
        assert row["Max"] == 6.0
        assert row["N"] == 5

    def test_p25_p75(self, peers_df):
        stats = peer_statistics(peers_df)
        row = stats[stats["Multiple"] == "P/E"].iloc[0]
        assert row["P25"] == 25.0
        assert row["P75"] == 35.0

    def test_missing_multiple(self):
        df = pd.DataFrame([{"Name": "X", "P/E": 15}])
        stats = peer_statistics(df)
        # EV/Sales + EV/EBITDA absent → not emitted
        assert set(stats["Multiple"]) == {"P/E"}

    def test_junk_filtered(self):
        df = pd.DataFrame([
            {"P/E": 20}, {"P/E": -5}, {"P/E": 1e5}, {"P/E": None}, {"P/E": 30},
        ])
        stats = peer_statistics(df)
        row = stats[stats["Multiple"] == "P/E"].iloc[0]
        assert row["N"] == 2
        assert row["Median"] == 25.0

    def test_empty_series_safe(self):
        df = pd.DataFrame([{"P/E": None}])
        stats = peer_statistics(df)
        assert stats.iloc[0]["N"] == 0


# ---------- implied_share_price ----------

class TestImpliedSharePrice:
    def test_ev_sales_math(self, peers_df, target):
        stats = peer_statistics(peers_df)
        out = implied_share_price(target, stats, stat="Median")
        row = out[out["Multiple"] == "EV/Sales"].iloc[0]
        # EV = 4 * 10000 = 40000; Equity = 39000; Price = 390
        assert row["Implied EV (₹ Cr)"] == 40000.0
        assert row["Implied Equity (₹ Cr)"] == 39000.0
        assert row["Implied Price (₹)"] == 390.0

    def test_ev_ebitda_math(self, peers_df, target):
        stats = peer_statistics(peers_df)
        row = implied_share_price(target, stats).query("Multiple == 'EV/EBITDA'").iloc[0]
        # EV = 14 * 2500 = 35000; Equity = 34000; Price = 340
        assert row["Implied Price (₹)"] == 340.0

    def test_pe_math(self, peers_df, target):
        stats = peer_statistics(peers_df)
        row = implied_share_price(target, stats).query("Multiple == 'P/E'").iloc[0]
        # Price = 30 * 50 = 1500
        assert row["Implied Price (₹)"] == 1500.0

    def test_signal_undervalued(self, peers_df, target):
        stats = peer_statistics(peers_df)
        row = implied_share_price(target, stats).query("Multiple == 'P/E'").iloc[0]
        # 1500 vs 1200 = +25% → UNDERVALUED
        assert row["Signal"] == "UNDERVALUED"

    def test_signal_overvalued(self, peers_df, target):
        stats = peer_statistics(peers_df)
        row = implied_share_price(target, stats).query("Multiple == 'EV/Sales'").iloc[0]
        # 390 vs 1200 = -67% → OVERVALUED
        assert row["Signal"] == "OVERVALUED"

    def test_missing_metric_skipped(self, peers_df):
        tgt = {"sales_cr": None, "ebitda_cr": None, "eps": 50,
               "shares_cr": 100, "current_price": 1000, "net_debt_cr": 0}
        stats = peer_statistics(peers_df)
        out = implied_share_price(tgt, stats)
        assert set(out["Multiple"]) == {"P/E"}

    def test_zero_shares_safe(self, peers_df, target):
        target["shares_cr"] = 0
        stats = peer_statistics(peers_df)
        out = implied_share_price(target, stats)
        assert out.empty


# ---------- overall_signal ----------

class TestOverallSignal:
    def test_average_upside(self, peers_df, target):
        stats = peer_statistics(peers_df)
        implied = implied_share_price(target, stats)
        verdict = overall_signal(implied)
        assert verdict["avg_upside"] is not None
        assert verdict["signal"] in {"UNDERVALUED", "OVERVALUED", "FAIRLY VALUED"}

    def test_empty_df(self):
        verdict = overall_signal(pd.DataFrame())
        assert verdict == {"avg_upside": None, "signal": "N/A"}


# ---------- _signal thresholds ----------

@pytest.mark.parametrize("upside,expected", [
    (50, "UNDERVALUED"),
    (16, "UNDERVALUED"),
    (15, "FAIRLY VALUED"),
    (0, "FAIRLY VALUED"),
    (-15, "FAIRLY VALUED"),
    (-16, "OVERVALUED"),
    (-80, "OVERVALUED"),
    (None, "N/A"),
])
def test_signal_thresholds(upside, expected):
    assert _signal(upside) == expected


def test_round_helper():
    assert _round(1.2345, 2) == 1.23
    assert _round(None) is None
    assert _round("abc") is None
