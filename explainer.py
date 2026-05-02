"""
ml/explainer.py — Human-readable model explanations for anomaly & manipulation decisions
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


FEATURE_DESCRIPTIONS = {
    "volume_zscore":       "Abnormal trading volume (standard deviations from 20-day mean)",
    "price_change_pct":    "Single-day price percentage change",
    "price_range_pct":     "Intraday price range (High-Low) as % of price",
    "gap_up_pct":          "Gap-up from previous close (bullish gap)",
    "gap_down_pct":        "Gap-down from previous close (bearish gap)",
    "volume_price_corr":   "5-day rolling correlation of volume with price direction",
    "close_vs_sma20":      "Price deviation from 20-day moving average",
    "upper_shadow":        "Upper candlestick wick (selling pressure indicator)",
    "lower_shadow":        "Lower candlestick wick (buying pressure indicator)",
}

RULE_EXPLANATIONS = {
    "Abnormal Volume Spikes": (
        "Trading volume significantly exceeded historical norms. "
        "Unusual volume can indicate institutional accumulation, news-driven moves, "
        "or coordinated buying/selling activity."
    ),
    "Price Spike Without Volume": (
        "Large price movements occurred on below-average volume. "
        "In liquid markets, significant price moves are usually accompanied by "
        "elevated volume. Low-volume spikes may indicate thin order books being "
        "manipulated by small actors."
    ),
    "Wash Trade Pattern": (
        "High volume was observed with minimal price movement. "
        "This pattern is a signature of wash trading — where the same actor "
        "buys and sells simultaneously to create artificial volume and the "
        "illusion of market activity without actual price discovery."
    ),
    "Pump & Dump Shape": (
        "The price chart shows a rapid exponential rise followed by a sharp crash. "
        "This is the classic pump-and-dump pattern: coordinated buying drives "
        "the price up, attracting retail investors, before insiders sell at the peak."
    ),
    "ML Anomaly Cluster": (
        "The Isolation Forest model flagged an elevated number of trading days "
        "as statistically anomalous across multiple features simultaneously. "
        "Clusters of anomalies are more indicative of systemic manipulation "
        "than isolated random events."
    ),
}

@dataclass
class Explanation:
    top_features: list = field(default_factory=list)
    rule_explanations: list = field(default_factory=list)
    overall_narrative: str = ""
    recommendations: list = field(default_factory=list)


def generate_explanation(
    manipulation_report,
    anomaly_report,
    fundamental_report=None,
    technical_report=None,
) -> Explanation:
    exp = Explanation()

    # ── Top Anomaly Features ─────────────────────────────────────────────────
    if anomaly_report and anomaly_report.feature_importances:
        top = list(anomaly_report.feature_importances.items())[:5]
        exp.top_features = [
            {
                "feature": k,
                "importance": round(v, 4),
                "description": FEATURE_DESCRIPTIONS.get(k, k),
            }
            for k, v in top if v > 0
        ]

    # ── Rule Explanations ─────────────────────────────────────────────────────
    if manipulation_report and manipulation_report.triggered_rules:
        for rule_hit in manipulation_report.triggered_rules:
            rule_name = rule_hit["rule"]
            exp.rule_explanations.append({
                "rule": rule_name,
                "contribution": rule_hit["contribution"],
                "explanation": RULE_EXPLANATIONS.get(rule_name, ""),
            })

    # ── Overall Narrative ─────────────────────────────────────────────────────
    risk = manipulation_report.risk_level if manipulation_report else "LOW"
    score = manipulation_report.score if manipulation_report else 0

    fund_label = fundamental_report.overall_label if fundamental_report else "UNKNOWN"
    tech_signal = technical_report.overall_signal if technical_report else "UNKNOWN"

    narrative_parts = [
        f"Manipulation Risk Score: {score:.0f}/100 ({risk}).",
        manipulation_report.explanation if manipulation_report else "",
    ]
    if fund_label in ("STRONG BUY", "BULLISH") and risk in ("LOW", "MEDIUM") and tech_signal == "BUY":
        narrative_parts.append("Fundamentals and technicals are aligned bullishly with low manipulation risk — a favorable setup.")
    elif fund_label in ("AVOID", "BEARISH") or risk in ("HIGH", "CRITICAL"):
        narrative_parts.append("Caution advised: weak fundamentals and/or elevated manipulation signals suggest elevated downside risk.")
    else:
        narrative_parts.append("Mixed signals across analytical layers. Independent due diligence is recommended.")
    exp.overall_narrative = " ".join(p for p in narrative_parts if p)

    # ── Recommendations ────────────────────────────────────────────────────────
    recs = []
    if risk == "LOW":
        recs.append("Continue standard monitoring. No immediate red flags detected.")
    elif risk == "MEDIUM":
        recs.append("Increase monitoring frequency. Review news for undisclosed catalysts.")
        recs.append("Check SEC EDGAR or local exchange filings for recent insider transactions.")
    elif risk == "HIGH":
        recs.append("Consider reducing position size or setting tighter stop-losses.")
        recs.append("Review order book depth and bid-ask spreads for signs of thin liquidity.")
        recs.append("Cross-reference trading activity with corporate announcements and social media.")
    else:  # CRITICAL
        recs.append("ALERT: Exercise extreme caution. Do not initiate new positions.")
        recs.append("Report suspicious activity to the relevant regulatory authority (e.g., SEC, FCA, SEBI).")
        recs.append("Engage risk management team and document all anomalies with timestamps.")

    if anomaly_report and len(anomaly_report.anomaly_dates) > 0:
        recs.append(f"Review trading on these flagged dates: {', '.join(anomaly_report.anomaly_dates[-5:])}.")

    exp.recommendations = recs
    return exp
