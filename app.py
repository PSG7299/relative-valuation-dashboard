"""
app.py
------
Streamlit UI for the Relative Valuation Dashboard.
Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict
from zoneinfo import ZoneInfo

from scraper import fetch_company, fetch_peers_for, enrich_with_ev_multiples, enrich_with_deep_pnl, fetch_pnl_ttm
from valuation import peer_statistics, implied_share_price, overall_signal
from tickers import NIFTY_50, NIFTY_NEXT_50, ALL_TICKERS


# ---------- Page config ----------

st.set_page_config(
    page_title="Relative Valuation Dashboard",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
        .badge {
            display: inline-block; padding: 6px 14px; border-radius: 20px;
            font-weight: 700; font-size: 14px; letter-spacing: 0.4px;
        }
        .under   { background: #0f9d58; color: white; }
        .over    { background: #d93025; color: white; }
        .fair    { background: #f4b400; color: #1a1a1a; }
        .na      { background: #9aa0a6; color: white; }
        .small-muted { color:#5f6368; font-size:12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Relative Valuation Dashboard")
st.caption("Live peer multiples from Screener.in · EV/Sales · EV/EBITDA · P/E")


# ---------- Sidebar inputs ----------

with st.sidebar:
    st.header("Inputs")

    source = st.radio(
        "Pick ticker from",
        ["Nifty 50", "Nifty Next 50", "All (Nifty 100)", "Manual entry"],
        index=0,
        horizontal=False,
    )

    if source == "Nifty 50":
        choice = st.selectbox("Company", sorted(NIFTY_50.keys()), index=sorted(NIFTY_50.keys()).index("Infosys"))
        ticker = NIFTY_50[choice]
    elif source == "Nifty Next 50":
        choice = st.selectbox("Company", sorted(NIFTY_NEXT_50.keys()))
        ticker = NIFTY_NEXT_50[choice]
    elif source == "All (Nifty 100)":
        choice = st.selectbox("Company", sorted(ALL_TICKERS.keys()))
        ticker = ALL_TICKERS[choice]
    else:
        ticker = st.text_input("Enter NSE ticker (as on Screener)", value="INFY").strip().upper().replace(" ", "")

    st.caption(f"Using ticker: **`{ticker}`**")

    stat_choice = st.selectbox("Peer stat to apply", ["Median", "Mean", "P25", "P75"], index=0)
    peer_limit = st.slider("Number of peers", 3, 15, 10)
    deep_ebitda = st.checkbox(
        "Compute real EV/EBITDA (slower, ~10-15s extra)",
        value=False,
        help="Deep-scrapes each peer's P&L to pull TTM Operating Profit and Debt.",
    )

    st.markdown("---")
    st.subheader("Target financials (override)")
    st.caption("Leave 0 to auto-fetch from Screener where available.")
    sales_cr = st.number_input("Sales / Revenue (₹ Cr, TTM)", min_value=0.0, value=0.0, step=100.0)
    ebitda_cr = st.number_input("EBITDA (₹ Cr, TTM)", min_value=0.0, value=0.0, step=50.0)
    eps = st.number_input("EPS (₹, TTM)", min_value=0.0, value=0.0, step=1.0)
    net_debt_cr = st.number_input("Net Debt (₹ Cr)", value=0.0, step=100.0)

    run = st.button("Run Valuation", type="primary", use_container_width=True)


# ---------- Main ----------

def _badge(signal: str) -> str:
    cls = {"UNDERVALUED": "under", "OVERVALUED": "over", "FAIRLY VALUED": "fair"}.get(signal, "na")
    return f'<span class="badge {cls}">{signal}</span>'


if run:
    fetch_start = datetime.now(ZoneInfo("Asia/Kolkata"))
    try:
        with st.spinner(f"Fetching {ticker} from Screener.in..."):
            company = fetch_company(ticker)
            peers_raw = fetch_peers_for(ticker, limit=peer_limit)
            peers = [enrich_with_ev_multiples(p) for p in peers_raw]
        if deep_ebitda:
            with st.spinner(f"Deep-scraping EBITDA & Debt for {len(peers)} peers..."):
                peers = [enrich_with_deep_pnl(p) for p in peers]
    except Exception as e:
        st.error(f"Failed to fetch data for {ticker}: {e}")
        st.stop()
    fetch_end = datetime.now(ZoneInfo("Asia/Kolkata"))
    fetch_secs = (fetch_end - fetch_start).total_seconds()

    if not peers:
        st.warning("No peer data returned. Verify the ticker on Screener.in.")
        st.stop()

    ratios = company["ratios"]
    cmp_price = ratios.get("Current Price")
    shares_cr = company.get("shares_outstanding_cr")

    # Header strip
    view_tag = company.get("view", "consolidated")
    st.subheader(f"{company['name']}  ·  {ticker}  ·  _{view_tag}_")
    st.caption(
        f"🕒 Data fetched: **{fetch_end.strftime('%d %b %Y, %I:%M:%S %p IST')}**  ·  "
        f"took {fetch_secs:.1f}s  ·  source: [Screener.in]({company['url']})"
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Price (₹)", f"{cmp_price:,.2f}" if cmp_price else "—")
    c2.metric("Market Cap (₹ Cr)", f"{ratios.get('Market Cap'):,.0f}" if ratios.get("Market Cap") else "—")
    c3.metric("Stock P/E", f"{ratios.get('Stock P/E'):.2f}" if ratios.get("Stock P/E") else "—")
    c4.metric("ROCE (%)", f"{ratios.get('ROCE'):.2f}" if ratios.get("ROCE") else "—")

    st.markdown("---")

    # Peer table
    st.subheader(f"Peer Set ({len(peers)})")
    peers_df = pd.DataFrame(peers)
    display_cols = [c for c in [
        "Name", "Ticker", "CMP", "P/E", "Mar Cap", "Sales", "EBITDA (TTM)", "Debt",
        "EV", "EV/Sales", "EV/EBITDA", "ROCE"
    ] if c in peers_df.columns]
    st.dataframe(peers_df[display_cols], use_container_width=True, hide_index=True)

    # Peer stats
    st.subheader("Peer Multiple Statistics")
    stats_df = peer_statistics(peers_df)
    st.dataframe(stats_df, use_container_width=True, hide_index=True)

    # Target financials: auto-fetch from target's own P&L + derive EPS from P/E
    tgt_pnl = fetch_pnl_ttm(ticker)
    stock_pe = ratios.get("Stock P/E")
    derived_eps = (cmp_price / stock_pe) if (cmp_price and stock_pe) else None

    sources: Dict = {}  # track where each number came from
    def _pick(user_val, auto_val, user_label="user override", auto_label="auto-fetched"):
        if user_val:
            return user_val, user_label
        if auto_val:
            return auto_val, auto_label
        return None, "missing"

    sales_val,  sales_src  = _pick(sales_cr,    tgt_pnl.get("sales_ttm"),  auto_label="Screener P&L (TTM)")
    ebitda_val, ebitda_src = _pick(ebitda_cr,   tgt_pnl.get("ebitda_ttm"), auto_label="Screener P&L (TTM, Operating Profit)")
    eps_val,    eps_src    = _pick(eps,         derived_eps,                auto_label=f"derived (CMP ÷ Stock P/E = {cmp_price:.0f}/{stock_pe:.2f})" if stock_pe else "missing")
    debt_val,   debt_src   = _pick(net_debt_cr, tgt_pnl.get("debt"),       auto_label="Screener Balance Sheet")

    target_payload = {
        "sales_cr":      sales_val,
        "ebitda_cr":     ebitda_val,
        "eps":           eps_val,
        "net_debt_cr":   debt_val,
        "shares_cr":     shares_cr,
        "current_price": cmp_price,
    }

    with st.expander("Target financials used (click to inspect source)"):
        src_df = pd.DataFrame([
            {"Field": "Sales (₹ Cr, TTM)",  "Value": sales_val,  "Source": sales_src},
            {"Field": "EBITDA (₹ Cr, TTM)", "Value": ebitda_val, "Source": ebitda_src},
            {"Field": "EPS (₹, TTM)",       "Value": eps_val,    "Source": eps_src},
            {"Field": "Net Debt (₹ Cr)",    "Value": debt_val,   "Source": debt_src},
            {"Field": "Shares (Cr)",        "Value": shares_cr,  "Source": "Market Cap ÷ CMP"},
            {"Field": "Current Price (₹)", "Value": cmp_price,  "Source": "Screener top-ratios"},
        ])
        st.dataframe(src_df, use_container_width=True, hide_index=True)

    # Implied price
    st.subheader(f"Implied Share Price (using Peer {stat_choice})")
    implied_df = implied_share_price(target_payload, stats_df, stat=stat_choice)

    if implied_df.empty:
        st.warning("Not enough target financials to compute an implied price. "
                   "Enter Sales / EBITDA / EPS in the sidebar.")
    else:
        st.dataframe(implied_df, use_container_width=True, hide_index=True)

        verdict = overall_signal(implied_df)
        st.markdown("### Overall Valuation Signal")
        colA, colB = st.columns([1, 3])
        with colA:
            st.markdown(_badge(verdict["signal"]), unsafe_allow_html=True)
        with colB:
            if verdict["avg_upside"] is not None:
                st.markdown(
                    f"**Average Upside / Downside:** {verdict['avg_upside']:+.2f}%  "
                    f"<span class='small-muted'>vs. current price ₹{cmp_price:,.2f}</span>",
                    unsafe_allow_html=True,
                )

        csv = implied_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download implied-price table (CSV)",
            data=csv,
            file_name=f"{ticker}_relative_valuation_{fetch_end.strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

    st.caption(
        f"Source: Screener.in · Pulled at {fetch_end.strftime('%d %b %Y %I:%M %p IST')} · "
        "Figures are indicative and should be validated before any investment decision."
    )

else:
    st.info("Pick a company in the sidebar and click **Run Valuation** to begin.")
