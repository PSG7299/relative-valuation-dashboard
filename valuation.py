"""
valuation.py
------------
Relative valuation math: peer stats, implied prices, valuation signal.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional


# ---------- Peer stats ----------

def peer_statistics(df: pd.DataFrame, multiples=("EV/Sales", "EV/EBITDA", "P/E")) -> pd.DataFrame:
    """Return Median / Mean / Min / Max / P25 / P75 for each multiple across peers."""
    rows = []
    for m in multiples:
        if m not in df.columns:
            continue
        s = pd.to_numeric(df[m], errors="coerce").dropna()
        s = s[(s > 0) & (s < 1e4)]  # drop junk
        if s.empty:
            rows.append({"Multiple": m, "Median": None, "Mean": None,
                         "Min": None, "Max": None, "P25": None, "P75": None, "N": 0})
            continue
        rows.append({
            "Multiple": m,
            "Median": round(float(s.median()), 2),
            "Mean":   round(float(s.mean()), 2),
            "Min":    round(float(s.min()), 2),
            "Max":    round(float(s.max()), 2),
            "P25":    round(float(s.quantile(0.25)), 2),
            "P75":    round(float(s.quantile(0.75)), 2),
            "N":      int(s.count()),
        })
    return pd.DataFrame(rows)


# ---------- Implied value ----------

def implied_share_price(
    target: Dict,
    peer_stats: pd.DataFrame,
    stat: str = "Median",
) -> pd.DataFrame:
    """
    Apply peer multiple (default: Median) to the target's underlying metric
    to arrive at an implied EV, equity value, and per-share price.

    target expects:
        - sales_cr        : latest sales (₹ Cr)
        - ebitda_cr       : latest EBITDA (₹ Cr)
        - eps             : trailing EPS (₹)
        - net_debt_cr     : net debt (₹ Cr)
        - shares_cr       : shares outstanding (Cr)
        - current_price   : current market price (₹)
    """
    sales = target.get("sales_cr")
    ebitda = target.get("ebitda_cr")
    eps = target.get("eps")
    net_debt = target.get("net_debt_cr") or 0
    shares = target.get("shares_cr")
    cmp_price = target.get("current_price")

    rows = []
    for _, r in peer_stats.iterrows():
        mult_name = r["Multiple"]
        mult_val = r.get(stat)
        if mult_val is None or shares in (None, 0):
            continue

        implied_price = None
        implied_ev = None
        implied_equity = None

        if mult_name == "EV/Sales" and sales:
            implied_ev = mult_val * sales
            implied_equity = implied_ev - net_debt
            implied_price = implied_equity / shares
        elif mult_name == "EV/EBITDA" and ebitda:
            implied_ev = mult_val * ebitda
            implied_equity = implied_ev - net_debt
            implied_price = implied_equity / shares
        elif mult_name == "P/E" and eps:
            implied_price = mult_val * eps
            implied_equity = implied_price * shares
            implied_ev = implied_equity + net_debt

        if implied_price is None:
            continue

        upside = ((implied_price / cmp_price) - 1) * 100 if cmp_price else None
        signal = _signal(upside)

        rows.append({
            "Multiple": mult_name,
            f"Peer {stat}": round(mult_val, 2),
            "Implied EV (₹ Cr)": _round(implied_ev),
            "Implied Equity (₹ Cr)": _round(implied_equity),
            "Implied Price (₹)": _round(implied_price),
            "Current Price (₹)": _round(cmp_price),
            "Upside / Downside (%)": _round(upside),
            "Signal": signal,
        })
    return pd.DataFrame(rows)


# ---------- Signal ----------

def _signal(upside: Optional[float]) -> str:
    if upside is None:
        return "N/A"
    if upside > 15:
        return "UNDERVALUED"
    if upside < -15:
        return "OVERVALUED"
    return "FAIRLY VALUED"


def overall_signal(implied_df: pd.DataFrame) -> Dict:
    """Average upside across available multiples → single verdict."""
    if implied_df.empty or "Upside / Downside (%)" not in implied_df.columns:
        return {"avg_upside": None, "signal": "N/A"}
    avg = float(np.nanmean(implied_df["Upside / Downside (%)"].astype(float)))
    return {"avg_upside": round(avg, 2), "signal": _signal(avg)}


# ---------- Formatting helper ----------

def _round(x, n=2):
    try:
        return round(float(x), n)
    except (TypeError, ValueError):
        return None
