"""
app.py — AI Stock Market Intelligence System
Main Streamlit application entrypoint
"""
import logging
import json
import sys
import os
import textwrap

import streamlit as st
import pandas as pd

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

# ── Configure logging ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# ── Page config (MUST be first Streamlit call) ─────────────────────────────────
st.set_page_config(
    page_title="StockIQ — AI Market Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Internal imports ──────────────────────────────────────────────────────────
from config import EXCHANGE_SUFFIXES, COLORS
from ui.theme import inject_theme
from data.fetcher import (
    fetch_company_info, fetch_stock_data, fetch_news_headlines, fetch_financials,
    fetch_risk_free_rate, fetch_macro_data, fetch_global_market_news, fetch_bond_data
)
from ui.components import (
    render_header, render_key_stats, render_candlestick, render_technical_chart,
    render_manipulation_gauge, render_anomaly_timeline, render_sentiment_bar,
    render_fundamental_table, render_technical_signals, render_metadata_panel,
    render_feature_importance, render_news_feed, render_valuation_dashboard,
    render_macro_panel, render_global_market_dashboard,
)
from data.validator import validate_ohlcv, validate_company_info
from data.cache import cache_key, get_cached, set_cached
from analysis.fundamental import run_fundamental_analysis
from analysis.technical import run_technical_analysis
from analysis.sentiment import run_sentiment_analysis
from analysis.metadata import run_metadata_analysis
from analysis.valuation import run_valuation_analysis
from analysis.macro import run_macro_analysis
from ml.anomaly_detector import run_anomaly_detection
from ml.manipulation_scorer import run_manipulation_scoring
from ml.explainer import generate_explanation

inject_theme()


# ─── Session State Init ───────────────────────────────────────────────────────
for key in ["results", "last_ticker", "error"]:
    if key not in st.session_state:
        st.session_state[key] = None


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(textwrap.dedent("""
    <div style="text-align:center; padding:1rem 0 1.5rem;">
      <div style="font-size:2rem;">📈</div>
      <div style="font-size:1.3rem; font-weight:800; background:linear-gradient(135deg,#3B82F6,#8B5CF6);
                  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;">StockIQ</div>
      <div style="font-size:0.7rem; color:#94A3B8; letter-spacing:2px; text-transform:uppercase;">AI Market Intelligence</div>
    </div>
    <hr style="border-color:#1E2D42; margin:0 0 1.25rem;">
    """), unsafe_allow_html=True)

    st.markdown("**🎯 Target Company**")
    ticker_raw = st.text_input("Ticker Symbol", value="AAPL", placeholder="e.g. AAPL, TSLA, MSFT",
                                help="Enter the stock ticker. Exchange suffix added automatically.", key="ticker_input")

    exchange = st.selectbox("Exchange", options=list(EXCHANGE_SUFFIXES.keys()),
                            index=0, key="exchange_select")

    st.markdown("**📅 Analysis Period**")
    period = st.select_slider("Period", options=["1mo","3mo","6mo","1y","2y","5y"],
                               value="1y", key="period_slider")

    st.markdown("**📰 Custom Text Input** *(optional)*")
    custom_text = st.text_area("Paste news, analyst reports, or any text for sentiment & metadata analysis.",
                                height=120, placeholder="Paste any financial text here...", key="custom_text")

    st.info("💡 **Pro Tip**: For EGX stocks, use the `.CA` suffix (e.g. `COMI`). For UK, use `.L` (e.g. `HSBA`).")

    st.markdown('<div style="margin:1rem 0 0.5rem;"></div>', unsafe_allow_html=True)
    run_btn = st.button("🚀 Run Analysis", key="run_button", use_container_width=True)

    st.markdown(textwrap.dedent("""
    <div style="margin-top:2rem; padding:1rem; background:rgba(255,255,255,0.03); border:1px solid #1E2D42; border-radius:10px;">
      <div style="font-size:0.68rem; color:#94A3B8; text-transform:uppercase; letter-spacing:1px; margin-bottom:0.5rem;">System Info</div>
      <div style="font-size:0.75rem; color:#64748B; line-height:1.6;">
        Data: Yahoo Finance<br>
        ML: Isolation Forest<br>
        NLP: VADER Sentiment<br>
        Risk: Hybrid Rule + ML
      </div>
    </div>
    <div style="margin-top:1rem; font-size:0.65rem; color:#334155; text-align:center;">
      ⚠️ For informational purposes only.<br>Not financial advice.
    </div>
    """), unsafe_allow_html=True)


# ─── Main Analysis Pipeline ───────────────────────────────────────────────────
def run_analysis(ticker: str, period: str, custom_text: str) -> dict:
    results = {}
    progress = st.progress(0, text="Fetching company data...")

    # Step 1: Company info
    info = fetch_company_info(ticker)
    val_info = validate_company_info(info)
    if not val_info.ok:
        st.error(f"❌ {val_info.errors[0]}")
        return {}
    for w in val_info.warnings:
        st.warning(f"⚠️ {w}")
    results["info"] = info
    progress.progress(15, text="Fetching historical price data...")

    # Step 2: OHLCV
    try:
        df = fetch_stock_data(ticker, period=period)
    except Exception as e:
        st.error(f"❌ Could not fetch price data: {e}")
        return {}
    val_ohlcv = validate_ohlcv(df)
    if not val_ohlcv.ok:
        st.error(f"❌ Data validation failed: {val_ohlcv.errors[0]}")
        return {}
    for w in val_ohlcv.warnings:
        st.warning(f"⚠️ {w}")
    results["df"] = df
    progress.progress(30, text="Running fundamental analysis...")

    # Step 3: Fundamental
    fund_report = run_fundamental_analysis(info)
    results["fundamental"] = fund_report
    progress.progress(45, text="Running technical analysis...")

    # Step 4: Technical
    tech_report = run_technical_analysis(df, ticker=ticker)
    results["technical"] = tech_report
    progress.progress(58, text="Fetching news & running sentiment analysis...")

    # Step 5: News + Sentiment
    headlines = fetch_news_headlines(ticker)
    results["headlines"] = headlines
    sentiment_report = run_sentiment_analysis(ticker, headlines, custom_text=custom_text)
    results["sentiment"] = sentiment_report
    progress.progress(70, text="Running ML anomaly detection...")

    # Step 6: Anomaly Detection (uses enriched df from technical)
    anomaly_report = run_anomaly_detection(tech_report.df, ticker=ticker)
    results["anomaly"] = anomaly_report
    progress.progress(82, text="Scoring manipulation risk...")

    # Step 7: Manipulation Scoring
    manip_report = run_manipulation_scoring(tech_report.df, ticker=ticker, anomaly_report=anomaly_report)
    results["manipulation"] = manip_report
    progress.progress(90, text="Generating explanations & metadata...")

    # Step 8: Explainer
    explanation = generate_explanation(manip_report, anomaly_report, fund_report, tech_report)
    results["explanation"] = explanation

    # Step 9: Metadata Analysis
    metadata_report = run_metadata_analysis(ticker, df=df, headlines=headlines, custom_text=custom_text, info=info)
    results["metadata"] = metadata_report

    # Step 10: Valuation Analysis
    progress.progress(95, text="Running macro & valuation models...")
    
    # 10a. Macro Analysis
    country = info.get("country", "United States")
    macro_data = fetch_macro_data(country)
    macro_report = run_macro_analysis(country, macro_data)
    results["macro"] = macro_report
    
    # 10b. Valuation
    financials = fetch_financials(ticker)
    rf_rate = fetch_risk_free_rate(country="EG" if ".CA" in ticker else "US")
    # Adjust ERP for emerging markets like Egypt
    erp_adj = 0.05 if ".CA" in ticker else 0.0 
    valuation_report = run_valuation_analysis(ticker, info, financials, rf_rate, country_risk_premium=erp_adj)
    results["valuation"] = valuation_report

    # Step 11: Global Market Data
    progress.progress(98, text="Fetching global market pulse...")
    results["global_news"] = fetch_global_market_news()
    results["bond_data"] = fetch_bond_data()

    progress.progress(100, text="✅ Analysis complete.")
    progress.empty()

    return results


# ─── Trigger Analysis ─────────────────────────────────────────────────────────
if run_btn:
    suffix = EXCHANGE_SUFFIXES.get(exchange, "")
    ticker = (ticker_raw.strip().upper() + suffix).strip()
    ck = cache_key(ticker, period, custom_text[:50])
    cached = get_cached(ck)
    if cached:
        st.session_state["results"] = cached
        st.toast("⚡ Loaded from cache", icon="💾")
    else:
        with st.spinner(""):
            results = run_analysis(ticker, period, custom_text)
        if results:
            set_cached(ck, results)
            st.session_state["results"] = results
            st.session_state["last_ticker"] = ticker


# ─── Results Rendering ────────────────────────────────────────────────────────
results = st.session_state.get("results")

if results is None:
    # ── Landing screen ──────────────────────────────────────────────────────
    st.markdown(textwrap.dedent("""
    <div style="text-align:center; padding:5rem 2rem;">
      <div style="font-size:4rem; margin-bottom:1rem;">📈</div>
      <div style="font-size:2.5rem; font-weight:800; background:linear-gradient(135deg,#3B82F6 0%,#8B5CF6 50%,#10B981 100%);
                  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; margin-bottom:0.75rem;">
        AI Stock Market Intelligence
      </div>
      <div style="font-size:1.05rem; color:#94A3B8; max-width:600px; margin:0 auto 2.5rem; line-height:1.7;">
        Institutional-grade stock analysis combining real-time financial data,
        technical indicators, AI anomaly detection, and market manipulation scoring.
      </div>
      <div style="display:flex; gap:1.5rem; justify-content:center; flex-wrap:wrap;">
        <div style="background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.3); border-radius:12px; padding:1.25rem 1.75rem; min-width:160px;">
          <div style="font-size:1.5rem; margin-bottom:0.4rem;">📊</div>
          <div style="font-weight:600; margin-bottom:0.2rem; font-size:0.9rem;">Fundamental</div>
          <div style="font-size:0.75rem; color:#64748B;">10 scored metrics</div>
        </div>
        <div style="background:rgba(139,92,246,0.1); border:1px solid rgba(139,92,246,0.3); border-radius:12px; padding:1.25rem 1.75rem; min-width:160px;">
          <div style="font-size:1.5rem; margin-bottom:0.4rem;">📉</div>
          <div style="font-weight:600; margin-bottom:0.2rem; font-size:0.9rem;">Technical</div>
          <div style="font-size:0.75rem; color:#64748B;">RSI · MACD · Bollinger</div>
        </div>
        <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); border-radius:12px; padding:1.25rem 1.75rem; min-width:160px;">
          <div style="font-size:1.5rem; margin-bottom:0.4rem;">🤖</div>
          <div style="font-weight:600; margin-bottom:0.2rem; font-size:0.9rem;">AI / ML</div>
          <div style="font-size:0.75rem; color:#64748B;">Isolation Forest</div>
        </div>
        <div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); border-radius:12px; padding:1.25rem 1.75rem; min-width:160px;">
          <div style="font-size:1.5rem; margin-bottom:0.4rem;">🚨</div>
          <div style="font-weight:600; margin-bottom:0.2rem; font-size:0.9rem;">Manipulation</div>
          <div style="font-size:0.75rem; color:#64748B;">5-rule hybrid scorer</div>
        </div>
      </div>
      <div style="margin-top:3rem; font-size:0.85rem; color:#475569;">
        ← Enter a ticker in the sidebar and click <b>Run Analysis</b>
      </div>
    </div>
    """), unsafe_allow_html=True)

else:
    info        = results["info"]
    df          = results["df"]
    fund        = results["fundamental"]
    tech        = results["technical"]
    sentiment   = results["sentiment"]
    anomaly     = results["anomaly"]
    manip       = results["manipulation"]
    explanation = results["explanation"]
    metadata    = results["metadata"]
    headlines   = results["headlines"]
    valuation   = results["valuation"]
    macro       = results.get("macro")
    global_news = results.get("global_news", [])
    bond_data   = results.get("bond_data", {})

    # ── Hero ─────────────────────────────────────────────────────────────────
    render_header(info)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🏢 Overview",
        "📉 Technicals",
        "💎 Valuation",
        "🌍 Macro & Context",
        "🤖 AI · Manipulation",
        "📋 Metadata & News",
        "🌐 Global Markets",
    ])

    # ══ TAB 1: Overview ═══════════════════════════════════════════════════════
    with tab1:
        render_key_stats(info)
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        c1, c2 = st.columns([1.6, 1])
        with c1:
            render_fundamental_table(fund)
        with c2:
            render_sentiment_bar(sentiment)

            st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)

            # Company summary
            if info.get("summary"):
                with st.expander("ℹ️ Company Description", expanded=False):
                    st.markdown(f'<div style="font-size:0.83rem; color:var(--text-muted); line-height:1.7;">{info["summary"][:800]}{"..." if len(info.get("summary","")) > 800 else ""}</div>',
                                unsafe_allow_html=True)

            # Analyst consensus
            st.markdown('<div class="glass-card" style="padding:1rem 1.25rem;">', unsafe_allow_html=True)
            rec = info.get("recommendation", "N/A").upper().replace("-", " ")
            tgt = info.get("analyst_target")
            price = info.get("current_price") or 0
            updown = ((tgt - price) / price * 100) if tgt and price else None
            st.markdown(textwrap.dedent(f"""
            <div class="section-title">Analyst Consensus</div>
            <div style="display:flex; gap:1.5rem; flex-wrap:wrap;">
              <div><div class="metric-label">Recommendation</div><div style="font-size:1.1rem; font-weight:700;">{rec}</div></div>
              <div><div class="metric-label">Price Target</div><div style="font-size:1.1rem; font-weight:700;">{f"${tgt:.2f}" if tgt else "N/A"}</div></div>
              {f'<div><div class="metric-label">Upside/Downside</div><div style="font-size:1.1rem; font-weight:700; color:{"#10B981" if (updown or 0)>0 else "#EF4444"};">{updown:+.1f}%</div></div>' if updown else ""}
            </div>
            </div>
            """), unsafe_allow_html=True)

    # ══ TAB 2: Technicals ═════════════════════════════════════════════════════
    with tab2:
        render_candlestick(tech.df if tech.df is not None else df, ticker=info.get("ticker",""))
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        render_technical_chart(tech.df if tech.df is not None else df)
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Signal Breakdown</div>', unsafe_allow_html=True)
        render_technical_signals(tech)

    # ══ TAB 3: Valuation ══════════════════════════════════════════════════════
    with tab3:
        render_valuation_dashboard(valuation)

    # ══ TAB 4: Macro & Context ════════════════════════════════════════════════
    with tab4:
        render_macro_panel(macro)
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Country Indicators</div>', unsafe_allow_html=True)
        st.info(f"Current risk profile for **{macro.country if macro else 'the region'}** is based on real-time central bank data and inflation indices.")

    # ══ TAB 5: AI · Manipulation ══════════════════════════════════════════════
    with tab5:
        c1, c2 = st.columns([1, 1.5])
        with c1:
            render_manipulation_gauge(manip.score, manip.risk_level)
            rules_html = "".join([f'<div style="font-size:0.78rem; padding:0.35rem 0.6rem; background:rgba(239,68,68,0.1); border-left:2px solid #EF4444; border-radius:4px; margin-bottom:0.35rem; color:#EF4444;">{r["rule"]} (+{r["contribution"]} pts)</div>' for r in (manip.triggered_rules or [])])
            st.markdown(textwrap.dedent(f"""
            <div class="glass-card" style="padding:1rem 1.25rem;">
              <div class="section-title">Risk Summary</div>
              <div style="font-size:0.85rem; color:var(--text-muted); line-height:1.65;">{manip.explanation.strip()}</div>
              <div style="margin-top:0.75rem;">{rules_html.strip()}</div>
            </div>
            """), unsafe_allow_html=True)
        with c2:
            render_anomaly_timeline(
                anomaly.df_with_flags if anomaly.df_with_flags is not None else df,
                anomaly
            )

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        c3, c4 = st.columns([1, 1])
        with c3:
            st.markdown('<div class="section-title">Evidence Log</div>', unsafe_allow_html=True)
            if manip.evidence:
                for ev in manip.evidence:
                    st.markdown(f'<div style="font-size:0.8rem; color:var(--text-muted); padding:0.4rem 0.75rem; border-left:2px solid {COLORS["accent_gold"]}; margin-bottom:0.4rem;">{ev}</div>', unsafe_allow_html=True)
            else:
                st.success("✅ No manipulation evidence found.")

            st.markdown('<div class="section-title" style="margin-top:1.25rem;">Recommendations</div>', unsafe_allow_html=True)
            for rec in explanation.recommendations:
                st.markdown(f'<div style="font-size:0.82rem; color:var(--text-muted); padding:0.4rem 0; border-bottom:1px solid var(--border);">→ {rec}</div>', unsafe_allow_html=True)

        with c4:
            render_feature_importance(explanation)
            if explanation.rule_explanations:
                with st.expander("📖 Rule Explanations", expanded=False):
                    for r in explanation.rule_explanations:
                        st.markdown(f"**{r['rule']}** (+{r['contribution']:.0f} pts)")
                        st.markdown(f'<div style="font-size:0.8rem; color:var(--text-muted);">{r["explanation"]}</div>', unsafe_allow_html=True)
                        st.markdown("---")

    # ══ TAB 6: Metadata & News ════════════════════════════════════════════════
    with tab6:
        render_metadata_panel(metadata)
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Recent News & Sentiment</div>', unsafe_allow_html=True)
        render_news_feed(headlines, sentiment_report=sentiment)

    # ══ TAB 7: Global Markets ════════════════════════════════════════════════
    with tab7:
        render_global_market_dashboard(bond_data, global_news)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        # ── JSON Export ──────────────────────────────────────────────────────
        export_data = {
            "ticker": info.get("ticker"),
            "company": info.get("name"),
            "analysis_timestamp": metadata.analysis_timestamp if metadata else "",
            "fundamental": fund.to_dict() if fund else {},
            "technical": tech.to_dict() if tech else {},
            "sentiment": sentiment.to_dict() if sentiment else {},
            "manipulation": manip.to_dict() if manip else {},
            "anomaly": anomaly.to_dict() if anomaly else {},
            "metadata": metadata.to_dict() if metadata else {},
        }
        st.download_button(
            label="⬇️ Export Full Report (JSON)",
            data=json.dumps(export_data, indent=2, default=str),
            file_name=f"{info.get('ticker','report')}_stockiq_report.json",
            mime="application/json",
            use_container_width=True,
        )
