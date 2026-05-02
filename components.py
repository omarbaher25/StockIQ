"""
ui/components.py — Reusable Streamlit chart and card rendering components
"""
from __future__ import annotations
import streamlit as st
import textwrap
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from config import COLORS, RISK_COLORS
from web_scraper import get_market_hub_links

_PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color=COLORS["text_primary"], size=12),
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(gridcolor=COLORS["border"], showgrid=True, zeroline=False),
    yaxis=dict(gridcolor=COLORS["border"], showgrid=True, zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=COLORS["border"], borderwidth=1),
)


# ─── Hero Header ──────────────────────────────────────────────────────────────

def render_header(info: dict):
    price    = info.get("current_price")
    prev     = info.get("previous_close")
    mktcap   = info.get("market_cap")
    currency = info.get("currency", "USD")

    pct_change = ((price - prev) / prev * 100) if price and prev else None
    change_color = COLORS["accent_green"] if (pct_change or 0) >= 0 else COLORS["accent_red"]
    change_arrow = "▲" if (pct_change or 0) >= 0 else "▼"

    mktcap_str = "N/A"
    if mktcap:
        mktcap_str = f"${mktcap/1e12:.2f}T" if mktcap >= 1e12 else f"${mktcap/1e9:.2f}B" if mktcap >= 1e9 else f"${mktcap/1e6:.2f}M"

    rec = info.get("recommendation", "").upper().replace("-", " ")
    rec_badge = {"STRONG BUY": "badge-green", "BUY": "badge-blue", "HOLD": "badge-yellow",
                 "SELL": "badge-red", "STRONG SELL": "badge-red"}.get(rec, "badge-blue")

    st.markdown(textwrap.dedent(f"""
    <div class="glass-card" style="background: linear-gradient(135deg, {COLORS['gradient_start']}cc 0%, {COLORS['bg_card']} 100%); padding: 2rem;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:1rem;">
        <div>
          <div class="hero-ticker">{info.get('ticker','')}</div>
          <div class="hero-name">{info.get('name','')}</div>
          <div style="margin-top:0.6rem; display:flex; gap:0.5rem; flex-wrap:wrap;">
            <span class="score-badge badge-blue">{info.get('sector','N/A')}</span>
            <span class="score-badge" style="background:rgba(255,255,255,0.07);color:{COLORS['text_secondary']};border:1px solid {COLORS['border']}">{info.get('country','N/A')} · {info.get('exchange','')}</span>
            {f'<span class="score-badge {rec_badge}">{rec}</span>' if rec and rec != "N/A" else ""}
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:2.2rem; font-weight:800; color:{COLORS['text_primary']};">{currency} {f"{price:,.2f}" if price else "N/A"}</div>
          <div style="font-size:1rem; color:{change_color}; font-weight:600;">{change_arrow} {abs(pct_change):.2f}% today</div>
          <div style="font-size:0.8rem; color:{COLORS['text_secondary']}; margin-top:0.4rem;">Mkt Cap: {mktcap_str}</div>
        </div>
      </div>
    </div>
    """), unsafe_allow_html=True)


# ─── Key Stats Grid ───────────────────────────────────────────────────────────

def render_key_stats(info: dict):
    def fmt(v, prefix="", suffix="", pct=False, billions=False):
        if v is None: return "N/A"
        if pct:  return f"{v*100:.2f}%"
        if billions and abs(v) >= 1e9: return f"${v/1e9:.2f}B"
        if billions and abs(v) >= 1e6: return f"${v/1e6:.2f}M"
        return f"{prefix}{v:.2f}{suffix}"

    stats = [
        ("52W High",    fmt(info.get("52w_high"),   prefix="$")),
        ("52W Low",     fmt(info.get("52w_low"),    prefix="$")),
        ("Beta",        fmt(info.get("beta"),        suffix="x")),
        ("P/Book",      fmt(info.get("price_to_book"), suffix="x")),
        ("EPS (TTM)",   fmt(info.get("eps"),         prefix="$")),
        ("Div Yield",   fmt(info.get("dividend_yield"), pct=True)),
        ("Short Ratio", fmt(info.get("short_ratio"),  suffix="x")),
        ("Free CF",     fmt(info.get("free_cashflow"), billions=True)),
        ("EV",          fmt(info.get("enterprise_value"), billions=True)),
        ("Analyst Tgt", fmt(info.get("analyst_target"), prefix="$")),
    ]
    cols = st.columns(5)
    for i, (label, value) in enumerate(stats):
        with cols[i % 5]:
            st.markdown(textwrap.dedent(f"""
            <div class="metric-card">
              <div class="metric-label">{label}</div>
              <div class="metric-value" style="font-size:1.1rem;">{value}</div>
            </div>
            """), unsafe_allow_html=True)


# ─── Candlestick Chart ────────────────────────────────────────────────────────

def render_candlestick(df: pd.DataFrame, ticker: str = ""):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.75, 0.25], vertical_spacing=0.04)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"],  close=df["Close"],
        name="Price",
        increasing_line_color=COLORS["accent_green"],
        decreasing_line_color=COLORS["accent_red"],
        increasing_fillcolor=COLORS["accent_green"],
        decreasing_fillcolor=COLORS["accent_red"],
    ), row=1, col=1)

    # SMAs
    for col, color, name in [("SMA_20","#60A5FA","SMA 20"), ("SMA_50","#F59E0B","SMA 50"), ("SMA_200","#8B5CF6","SMA 200")]:
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[col], name=name, line=dict(color=color, width=1.5), opacity=0.8), row=1, col=1)

    # Bollinger Bands
    if "BB_Upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Upper"], name="BB Upper",
                                 line=dict(color=COLORS["accent_gold"], width=1, dash="dot"), opacity=0.5), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Lower"], name="BB Lower",
                                 line=dict(color=COLORS["accent_gold"], width=1, dash="dot"), opacity=0.5,
                                 fill="tonexty", fillcolor="rgba(245,158,11,0.05)"), row=1, col=1)

    # Volume bars
    colors = [COLORS["accent_green"] if c >= o else COLORS["accent_red"]
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
                         marker_color=colors, opacity=0.7), row=2, col=1)

    fig.update_layout(**_PLOT_LAYOUT, title=f"{ticker} Price History",
                      title_font_size=14, showlegend=True, height=520,
                      xaxis_rangeslider_visible=False)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)


# ─── RSI + MACD Chart ────────────────────────────────────────────────────────

def render_technical_chart(df: pd.DataFrame):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.5, 0.5], vertical_spacing=0.06,
                        subplot_titles=("RSI (14)", "MACD (12/26/9)"))
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
                                 line=dict(color=COLORS["accent_blue"], width=2)), row=1, col=1)
        fig.add_hrect(y0=70, y1=100, fillcolor="rgba(239,68,68,0.1)", line_width=0, row=1, col=1)
        fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(16,185,129,0.1)", line_width=0, row=1, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color=COLORS["accent_red"],   opacity=0.6, row=1, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color=COLORS["accent_green"], opacity=0.6, row=1, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color=COLORS["text_secondary"], opacity=0.4, row=1, col=1)

    if "MACD" in df.columns:
        hist = df["MACD_Hist"]
        hist_colors = [COLORS["accent_green"] if v >= 0 else COLORS["accent_red"] for v in hist.fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=hist, name="Histogram",
                             marker_color=hist_colors, opacity=0.7), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD",
                                 line=dict(color=COLORS["accent_blue"], width=2)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD_Signal"], name="Signal",
                                 line=dict(color=COLORS["accent_gold"], width=1.5, dash="dot")), row=2, col=1)

    fig.update_layout(**_PLOT_LAYOUT, height=420, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)


# ─── Manipulation Gauge ───────────────────────────────────────────────────────

def render_manipulation_gauge(score: float, risk_level: str):
    color = RISK_COLORS.get(risk_level, COLORS["accent_blue"])
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        delta={"reference": 25, "valueformat": ".1f"},
        number={"suffix": "/100", "font": {"size": 38, "color": COLORS["text_primary"]}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": COLORS["text_secondary"],
                     "tickfont": {"color": COLORS["text_secondary"]}},
            "bar":  {"color": color, "thickness": 0.25},
            "bgcolor": COLORS["bg_card2"],
            "borderwidth": 0,
            "steps": [
                {"range": [0,  25], "color": "rgba(16,185,129,0.15)"},
                {"range": [25, 50], "color": "rgba(245,158,11,0.15)"},
                {"range": [50, 75], "color": "rgba(239,68,68,0.15)"},
                {"range": [75,100], "color": "rgba(139,92,246,0.15)"},
            ],
            "threshold": {"line": {"color": color, "width": 3}, "value": score},
        },
        title={"text": f"Manipulation Risk — <b>{risk_level}</b>",
               "font": {"size": 14, "color": COLORS["text_secondary"]}},
    ))
    fig.update_layout(**_PLOT_LAYOUT, height=300)
    st.plotly_chart(fig, use_container_width=True)


# ─── Anomaly Timeline ─────────────────────────────────────────────────────────

def render_anomaly_timeline(df: pd.DataFrame, anomaly_report):
    if anomaly_report is None or df is None:
        st.info("No anomaly data available.")
        return

    df_plot = df.copy()
    df_plot["is_anomaly"] = df_plot.get("is_anomaly", False)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_plot.index, y=df_plot["Close"],
        name="Close Price", line=dict(color=COLORS["accent_blue"], width=2), opacity=0.8,
    ))
    anomaly_df = df_plot[df_plot.get("is_anomaly", pd.Series(False, index=df_plot.index))]
    if not anomaly_df.empty:
        fig.add_trace(go.Scatter(
            x=anomaly_df.index, y=anomaly_df["Close"],
            mode="markers", name="Anomaly",
            marker=dict(color=COLORS["accent_red"], size=10, symbol="x",
                        line=dict(color=COLORS["accent_red"], width=2)),
        ))
    fig.update_layout(**_PLOT_LAYOUT, title="Price with Anomaly Flags",
                      title_font_size=14, height=380)
    st.plotly_chart(fig, use_container_width=True)


# ─── Sentiment Bar ────────────────────────────────────────────────────────────

def render_sentiment_bar(sentiment_report):
    if sentiment_report is None:
        return

    label_color = {
        "BULLISH": COLORS["accent_green"],
        "BEARISH": COLORS["accent_red"],
        "NEUTRAL": COLORS["accent_gold"],
    }.get(sentiment_report.overall_sentiment, COLORS["accent_blue"])
    badge_class = {"BULLISH": "badge-green", "BEARISH": "badge-red", "NEUTRAL": "badge-yellow"}.get(
        sentiment_report.overall_sentiment, "badge-blue")

    score = sentiment_report.compound_score
    pct   = (score + 1) / 2 * 100  # map -1..1 to 0..100%

    st.markdown(textwrap.dedent(f"""
    <div class="glass-card">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
        <span style="font-weight:600; font-size:0.95rem;">News Sentiment</span>
        <span class="score-badge {badge_class}">{sentiment_report.overall_sentiment}</span>
      </div>
      <div style="background:var(--bg-card2); border-radius:99px; height:10px; overflow:hidden; margin-bottom:0.5rem;">
        <div style="width:{pct:.1f}%; height:100%; background:linear-gradient(90deg,{COLORS['accent_red']},{COLORS['accent_gold']},{COLORS['accent_green']}); border-radius:99px; transition:width 0.6s ease;"></div>
      </div>
      <div style="display:flex; justify-content:space-between; font-size:0.72rem; color:var(--text-muted);">
        <span>Bearish</span>
        <span>Score: <b style="color:{label_color};">{score:+.3f}</b> &nbsp;·&nbsp; {sentiment_report.article_count} articles</span>
        <span>Bullish</span>
      </div>
    </div>
    """), unsafe_allow_html=True)


# ─── Fundamental Table ────────────────────────────────────────────────────────

def render_fundamental_table(fundamental_report):
    if fundamental_report is None:
        return

    label_styles = {
        "EXCELLENT": "badge-green", "STRONG": "badge-green", "STRONG BUY": "badge-green",
        "ATTRACTIVE": "badge-green", "UNDERVALUED": "badge-green", "CONSERVATIVE": "badge-green",
        "HEALTHY": "badge-green", "GOOD": "badge-green", "HYPERGROWTH": "badge-green",
        "FAIR": "badge-blue", "MODERATE": "badge-blue", "MANAGEABLE": "badge-blue",
        "ADEQUATE": "badge-blue", "STRONG GROWTH": "badge-blue",
        "ELEVATED": "badge-yellow", "THIN": "badge-yellow", "FLAT": "badge-yellow",
        "WEAK": "badge-yellow", "STRETCHED": "badge-yellow",
        "EXPENSIVE": "badge-red", "HIGH LEVERAGE": "badge-red", "DECLINING": "badge-red",
        "STRESSED": "badge-red", "LOSS-MAKING": "badge-red", "NET LOSS": "badge-red",
        "NEGATIVE": "badge-red", "CRITICAL": "badge-purple", "OVERVALUED": "badge-red",
        "N/A": "badge-blue",
    }
    rows_html = ""
    for m in fundamental_report.metrics:
        badge = label_styles.get(m.label, "badge-blue")
        rows_html += f"""
        <tr style="border-bottom:1px solid var(--border);">
          <td style="padding:0.65rem 1rem; color:var(--text-muted); font-size:0.85rem;">{m.name}</td>
          <td style="padding:0.65rem 1rem; font-weight:600; font-family:'JetBrains Mono',monospace; font-size:0.88rem;">{m.formatted_value()}</td>
          <td style="padding:0.65rem 1rem;"><span class="score-badge {badge}" style="font-size:0.7rem;">{m.label}</span></td>
          <td style="padding:0.65rem 1rem; color:var(--text-muted); font-size:0.8rem;">{m.interpretation}</td>
        </tr>"""

    overall_badge = label_styles.get(fundamental_report.overall_label, "badge-blue")
    st.markdown(textwrap.dedent(f"""
    <div class="glass-card" style="padding:0; overflow:hidden;">
      <div style="padding:1rem 1.5rem; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center;">
        <span style="font-weight:600;">Fundamental Metrics</span>
        <div style="display:flex; align-items:center; gap:0.75rem;">
          <span style="font-size:0.82rem; color:var(--text-muted);">Score: <b>{fundamental_report.overall_score:.1f}/10</b></span>
          <span class="score-badge {overall_badge}">{fundamental_report.overall_label}</span>
        </div>
      </div>
      <div style="overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse;">
          <thead>
            <tr style="background:var(--bg-card2);">
              <th style="padding:0.6rem 1rem; text-align:left; font-size:0.72rem; text-transform:uppercase; letter-spacing:1px; color:var(--text-muted);">Metric</th>
              <th style="padding:0.6rem 1rem; text-align:left; font-size:0.72rem; text-transform:uppercase; letter-spacing:1px; color:var(--text-muted);">Value</th>
              <th style="padding:0.6rem 1rem; text-align:left; font-size:0.72rem; text-transform:uppercase; letter-spacing:1px; color:var(--text-muted);">Rating</th>
              <th style="padding:0.6rem 1rem; text-align:left; font-size:0.72rem; text-transform:uppercase; letter-spacing:1px; color:var(--text-muted);">Interpretation</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
      <div style="padding:0.75rem 1.5rem; background:var(--bg-card2); border-top:1px solid var(--border); font-size:0.82rem; color:var(--text-muted); font-style:italic;">
        {fundamental_report.summary}
      </div>
    </div>
    """), unsafe_allow_html=True)


# ─── Technical Signals Grid ───────────────────────────────────────────────────

def render_technical_signals(technical_report):
    if technical_report is None:
        return
    overall_color = {"BUY": "badge-green", "SELL": "badge-red", "NEUTRAL": "badge-yellow"}.get(
        technical_report.overall_signal, "badge-blue")

    st.markdown(textwrap.dedent(f"""
    <div style="display:flex; align-items:center; gap:1rem; margin-bottom:1rem;">
      <span style="font-size:0.7rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:1.5px;">Aggregate Signal</span>
      <span class="score-badge {overall_color}" style="font-size:0.85rem; padding:0.35rem 1rem;">{technical_report.overall_signal}</span>
      <span style="font-size:0.8rem; color:var(--text-muted);">Confidence: <b>{technical_report.overall_confidence:.1%}</b></span>
    </div>
    """), unsafe_allow_html=True)

    cols = st.columns(3)
    for i, sig in enumerate(technical_report.signals):
        badge = {"BUY": "badge-green", "SELL": "badge-red", "NEUTRAL": "badge-yellow"}.get(sig.signal, "badge-blue")
        with cols[i % 3]:
            val_str = f"{sig.value:.4f}" if sig.value is not None else "N/A"
            st.markdown(textwrap.dedent(f"""
            <div class="metric-card" style="margin-bottom:0.75rem; text-align:left;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
                <span style="font-size:0.78rem; font-weight:600; color:var(--text);">{sig.indicator}</span>
                <span class="score-badge {badge}" style="font-size:0.65rem;">{sig.signal}</span>
              </div>
              <div style="font-size:0.75rem; color:var(--text-muted); line-height:1.4;">{sig.note}</div>
              <div style="font-size:0.7rem; color:var(--text-muted); margin-top:0.4rem; font-family:'JetBrains Mono',monospace;">
                val={val_str} · conf={sig.confidence:.0%}
              </div>
            </div>
            """), unsafe_allow_html=True)


# ─── Metadata Panel ───────────────────────────────────────────────────────────

def render_metadata_panel(metadata_report):
    if metadata_report is None:
        return
    with st.expander("📋 Data Context & Metadata", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-title">Data Sources</div>', unsafe_allow_html=True)
            for src in metadata_report.data_sources:
                st.markdown(f"- {src}")
            st.markdown('<div class="section-title" style="margin-top:1rem;">Timeframe</div>', unsafe_allow_html=True)
            st.markdown(f"**{metadata_report.timeframe_start}** → **{metadata_report.timeframe_end}** ({metadata_report.timeframe_days} days, {metadata_report.data_points} data points)")
            if metadata_report.custom_text_provided:
                st.markdown('<div class="section-title" style="margin-top:1rem;">Custom Text</div>', unsafe_allow_html=True)
                st.markdown(f"**{metadata_report.custom_text_word_count}** words provided")
                if metadata_report.ai_tools_detected:
                    st.warning(f"🤖 AI tool signatures detected: {', '.join(metadata_report.ai_tools_detected)}")
                else:
                    st.success("✅ No AI tool fingerprints detected in custom text.")
        with c2:
            st.markdown('<div class="section-title">Detected Topics</div>', unsafe_allow_html=True)
            for t in metadata_report.detected_topics[:6]:
                st.markdown(f"- **{t['topic']}** ({t['hits']} mentions)")
            st.markdown('<div class="section-title" style="margin-top:1rem;">Top Keywords</div>', unsafe_allow_html=True)
            keywords = [f"`{kw['word']}`" for kw in metadata_report.top_keywords[:12]]
            st.markdown("  ".join(keywords))

        st.caption(f"Analysis generated at {metadata_report.analysis_timestamp}")


# ─── Macro Panel ──────────────────────────────────────────────────────────────

def render_macro_panel(macro_report):
    if not macro_report:
        return
    
    color = RISK_COLORS.get(macro_report.risk_label, COLORS["accent_blue"])
    
    st.markdown(textwrap.dedent(f"""
    <div class="glass-card" style="border-left:4px solid {color};">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
        <span style="font-weight:700; font-size:1.1rem;">🌍 {macro_report.country} Macro Context</span>
        <span class="score-badge" style="background:{color}22; color:{color}; border:1px solid {color}44;">{macro_report.risk_label} RISK</span>
      </div>
      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap:1rem;">
        <div class="metric-card">
          <div class="metric-label">Inflation</div>
          <div class="metric-value">{macro_report.inflation_rate:.1%}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Interest Rate</div>
          <div class="metric-value">{macro_report.interest_rate:.2%}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">GDP Growth</div>
          <div class="metric-value" style="color:{COLORS['accent_green'] if macro_report.gdp_growth > 0 else COLORS['accent_red']};">{macro_report.gdp_growth:+.1%}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Currency</div>
          <div class="metric-value">{macro_report.currency}</div>
        </div>
      </div>
      <div style="margin-top:1rem; font-size:0.82rem; color:var(--text-muted); line-height:1.5; padding:0.75rem; background:rgba(255,255,255,0.03); border-radius:6px;">
        {macro_report.summary}
      </div>
    </div>
    """), unsafe_allow_html=True)


# ─── Feature Importance Chart ─────────────────────────────────────────────────

def render_feature_importance(explanation):
    if not explanation or not explanation.top_features:
        return
    features = explanation.top_features
    names = [f["description"] for f in features]
    values = [f["importance"] for f in features]
    colors_list = [COLORS["accent_blue"] if v > 0 else COLORS["accent_red"] for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=names, orientation="h",
        marker_color=colors_list, opacity=0.85,
    ))
    fig.update_layout(**_PLOT_LAYOUT)
    fig.update_layout(title="Top Anomaly Features (contribution vs baseline)",
                      title_font_size=13, height=max(220, len(names) * 55),
                      xaxis_title="Importance Score", yaxis=dict(autorange="reversed", **_PLOT_LAYOUT["yaxis"]))
    st.plotly_chart(fig, use_container_width=True)


# ─── News Feed ────────────────────────────────────────────────────────────────

def render_news_feed(headlines: list[dict], sentiment_report=None):
    if not headlines:
        st.info("No recent news articles found.")
        return

    sentiment_map = {}
    if sentiment_report:
        for r in sentiment_report.headline_results:
            sentiment_map[r["title"]] = r

    for item in headlines[:10]:
        title     = item.get("title", "")
        publisher = item.get("publisher", "")
        link      = item.get("link", "#")
        published = item.get("published", "")
        sent_info = sentiment_map.get(title, {})
        label     = sent_info.get("label", "")
        compound  = sent_info.get("compound", 0.0)
        badge     = {"POSITIVE": "badge-green", "NEGATIVE": "badge-red", "NEUTRAL": "badge-yellow"}.get(label, "")

        st.markdown(textwrap.dedent(f"""
        <div style="padding:0.75rem 1rem; margin-bottom:0.5rem; background:var(--bg-card2);
                    border:1px solid var(--border); border-radius:10px;
                    border-left:3px solid {'#10B981' if label=='POSITIVE' else '#EF4444' if label=='NEGATIVE' else '#F59E0B'};">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:0.5rem;">
            <div style="flex:1;">
               <div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:0.2rem;">
                  {item.get('source', 'Unknown')} · {publisher}
               </div>
               <a href="{link}" target="_blank" style="color:var(--text); text-decoration:none; font-size:0.88rem; font-weight:500; line-height:1.4;">{title}</a>
            </div>
            {f'<span class="score-badge {badge}" style="font-size:0.65rem; white-space:nowrap;">{label} {compound:+.2f}</span>' if label else ""}
          </div>
          <div style="margin-top:0.4rem; font-size:0.72rem; color:var(--text-muted);">{published}</div>
        </div>
        """), unsafe_allow_html=True)


# ─── Valuation Dashboard ──────────────────────────────────────────────────────

def render_valuation_dashboard(val_report):
    if not val_report:
        return

    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.markdown('<div class="section-title">Intrinsic Value vs. Price</div>', unsafe_allow_html=True)
        price = val_report.current_price
        fv = val_report.fair_value_avg or 0.0
        upside = val_report.upside_pct or 0.0
        color = COLORS["accent_green"] if upside > 0 else COLORS["accent_red"]
        
        st.markdown(textwrap.dedent(f"""
        <div class="glass-card" style="text-align:center; padding:1.5rem;">
          <div style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px;">Est. Fair Value</div>
          <div style="font-size:2.4rem; font-weight:800; color:{COLORS['text_primary']}; margin:0.5rem 0;">${fv:.2f}</div>
          <div style="font-size:1.1rem; font-weight:600; color:{color};">
            {"+" if upside > 0 else ""}{upside:.1%} {"Undervalued" if upside > 0 else "Overvalued"}
          </div>
          <div style="margin-top:1rem; height:8px; background:var(--bg-card2); border-radius:4px; overflow:hidden;">
            <div style="width:{min(100, max(0, (fv/price)*50)) if price else 0}%; height:100%; background:{color};"></div>
          </div>
          <div style="display:flex; justify-content:space-between; margin-top:0.4rem; font-size:0.7rem; color:var(--text-muted);">
            <span>Current: ${price:.2f}</span>
            <span>Target: ${fv:.2f}</span>
          </div>
        </div>
        """), unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="section-title">WACC Components</div>', unsafe_allow_html=True)
        st.markdown(textwrap.dedent(f"""
        <div class="glass-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
             <span style="font-size:0.9rem; font-weight:600;">WACC (Cost of Capital)</span>
             <span class="score-badge badge-purple" style="font-size:1rem;">{val_report.wacc:.2%}</span>
          </div>
          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:1rem;">
            <div class="metric-card">
              <div class="metric-label">Cost of Equity</div>
              <div class="metric-value" style="font-size:1rem;">{val_report.cost_of_equity:.2%}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">Cost of Debt</div>
              <div class="metric-value" style="font-size:1rem;">{val_report.cost_of_debt:.2%}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">Equity Weight</div>
              <div class="metric-value" style="font-size:1rem;">{val_report.equity_weight:.1%}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">Debt Weight</div>
              <div class="metric-value" style="font-size:1rem;">{val_report.debt_weight:.1%}</div>
            </div>
          </div>
        </div>
        """), unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # Detailed Model Breakdown
    st.markdown('<div class="section-title">Valuation Models</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    with m1:
        val = f"${val_report.dcf_value:.2f}" if val_report.dcf_value else "N/A"
        st.markdown(f'<div class="metric-card"><div class="metric-label">5Y DCF Model</div><div class="metric-value">{val}</div></div>', unsafe_allow_html=True)
    with m2:
        val = f"${val_report.graham_value:.2f}" if val_report.graham_value else "N/A"
        st.markdown(f'<div class="metric-card"><div class="metric-label">Graham Number</div><div class="metric-value">{val}</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Methodology</div><div style="font-size:0.7rem; color:var(--text-muted); line-height:1.3;">{val_report.methodology}</div></div>', unsafe_allow_html=True)

    if val_report.warnings:
        for w in val_report.warnings:
            st.warning(f"⚠️ {w}")


# ─── Market Hub ───────────────────────────────────────────────────────────────




# ─── Global Market Dashboard ──────────────────────────────────────────────────

def render_global_market_dashboard(bond_data: dict, global_news: list[dict]):
    """
    Renders a comprehensive global market overview.
    """
    st.markdown('<div class="section-title" style="font-size:1.4rem; margin-bottom:1.5rem;">🌍 Global Market Pulse</div>', unsafe_allow_html=True)
    
    # Bond Yields Section
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.markdown('<div class="section-title">Treasury Yields</div>', unsafe_allow_html=True)
        html = '<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap:0.75rem;">'
        for name, yield_val in bond_data.items():
            color = COLORS["accent_blue"]
            html += textwrap.dedent(f"""
                <div class="metric-card" style="padding:0.75rem;">
                  <div class="metric-label" style="font-size:0.65rem;">{name}</div>
                  <div class="metric-value" style="font-size:1.1rem; color:{color};">{yield_val:.3f}%</div>
                </div>
            """).strip()
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
        
        st.markdown(textwrap.dedent(f"""
        <div class="glass-card" style="margin-top:1rem; padding:1rem; font-size:0.75rem; color:var(--text-muted);">
          <b>Why Bonds Matter:</b><br>
          Rising yields often compress P/E multiples for growth stocks. The 10Y Treasury is the global benchmark for the 'Risk-Free Rate'.
        </div>
        """), unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="section-title">Global Market News</div>', unsafe_allow_html=True)
        news_html = ""
        if not global_news:
            st.info("Gathering global market signals...")
        else:
            for item in global_news[:8]:
                news_html += textwrap.dedent(f"""
                <div style="padding:0.75rem 1rem; margin-bottom:0.6rem; background:var(--bg-card2); 
                            border:1px solid var(--border); border-radius:12px; transition: all 0.2s ease;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.3rem;">
                    <span style="font-size:0.65rem; color:{COLORS['accent_purple']}; text-transform:uppercase; font-weight:700; letter-spacing:0.5px;">{item['source']}</span>
                    <span style="font-size:0.6rem; color:var(--text-muted);">{item['published'][:16]}</span>
                  </div>
                  <a href="{item['link']}" target="_blank" style="text-decoration:none; color:var(--text); font-size:0.9rem; font-weight:600; line-height:1.4;">{item['title']}</a>
                </div>
                """).strip()
            st.markdown(news_html, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # Market Links
    st.markdown('<div class="section-title">Institutional Portals</div>', unsafe_allow_html=True)
    portals = [
        {"name": "Companies Market Cap", "url": "https://companiesmarketcap.com/", "color": "#10B981"},
        {"name": "StockAnalysis Global", "url": "https://stockanalysis.com/", "color": "#2563EB"},
        {"name": "EGX Official Portal", "url": "https://www.egx.com.eg/en/HomePage.aspx", "color": "#1E2D42"},
        {"name": "NSE India Official", "url": "https://www.nseindia.com/", "color": "#003399"},
        {"name": "Bloomberg Markets", "url": "https://www.bloomberg.com/markets", "color": "#000000"},
    ]
    
    portal_html = '<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap:0.75rem;">'
    for p in portals:
        portal_html += textwrap.dedent(f"""
            <a href="{p['url']}" target="_blank" style="text-decoration:none;">
              <div style="background:{p['color']}22; color:{p['color']}; border:1px solid {p['color']}44; 
                          padding:0.7rem; border-radius:10px; text-align:center; font-size:0.78rem; font-weight:700; transition: all 0.2s ease;">
                {p['name']}
              </div>
            </a>
        """).strip()
    portal_html += '</div>'
    st.markdown(portal_html, unsafe_allow_html=True)
