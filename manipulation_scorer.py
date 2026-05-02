"""
ml/manipulation_scorer.py — Hybrid rule-based + ML manipulation risk scorer
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from config import (MANIPULATION_WEIGHTS, MANIPULATION_THRESHOLDS,
                    VOLUME_SPIKE_ZSCORE, PRICE_SPIKE_PCT)

logger = logging.getLogger(__name__)

@dataclass
class ManipulationReport:
    ticker: str
    score: float = 0.0                  # 0–100
    risk_level: str = "LOW"             # LOW | MEDIUM | HIGH | CRITICAL
    triggered_rules: list = field(default_factory=list)
    explanation: str = ""
    evidence: list = field(default_factory=list)

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "score": round(self.score, 1),
            "risk_level": self.risk_level,
            "triggered_rules": self.triggered_rules,
            "explanation": self.explanation,
            "evidence": self.evidence,
        }


def _check_abnormal_volume(df: pd.DataFrame) -> tuple[float, list]:
    """Rule 1: Volume spikes > VOLUME_SPIKE_ZSCORE standard deviations."""
    if "Volume_ZScore" not in df.columns:
        return 0.0, []
    recent = df["Volume_ZScore"].tail(30)
    spikes = recent[recent > VOLUME_SPIKE_ZSCORE]
    if len(spikes) >= 3:
        evidence = [f"Volume spike on {str(d.date() if hasattr(d,'date') else d)}: Z={v:.2f}"
                    for d, v in spikes.tail(5).items()]
        return float(MANIPULATION_WEIGHTS["abnormal_volume"]), evidence
    elif len(spikes) >= 1:
        return float(MANIPULATION_WEIGHTS["abnormal_volume"]) * 0.5, [f"{len(spikes)} volume spike(s) detected in last 30 days."]
    return 0.0, []


def _check_price_spike_no_volume(df: pd.DataFrame) -> tuple[float, list]:
    """Rule 2: Large price moves on below-average volume (price manipulation pattern)."""
    daily_ret = df["Close"].pct_change().abs()
    big_moves = daily_ret[daily_ret > PRICE_SPIKE_PCT].tail(30)
    if big_moves.empty:
        return 0.0, []
    evidence = []
    suspicious = 0
    for date, ret in big_moves.items():
        if "Volume_ZScore" in df.columns:
            vol_z = df.loc[date, "Volume_ZScore"] if date in df.index else np.nan
            if not pd.isna(vol_z) and vol_z < 0:
                suspicious += 1
                evidence.append(f"{str(date.date() if hasattr(date,'date') else date)}: price moved {ret*100:.1f}% on below-avg volume (Z={vol_z:.2f})")
    if suspicious >= 2:
        return float(MANIPULATION_WEIGHTS["price_spike_no_news"]), evidence
    elif suspicious == 1:
        return float(MANIPULATION_WEIGHTS["price_spike_no_news"]) * 0.5, evidence
    return 0.0, []


def _check_wash_trade_pattern(df: pd.DataFrame) -> tuple[float, list]:
    """Rule 3: High volume + very small price range (wash trading signature)."""
    if "Volume_ZScore" not in df.columns:
        return 0.0, []
    price_range_pct = (df["High"] - df["Low"]) / df["Close"].replace(0, np.nan)
    high_vol = df["Volume_ZScore"] > 2.0
    flat_price = price_range_pct < 0.005   # <0.5% range
    wash_days = (high_vol & flat_price).sum()
    if wash_days >= 3:
        return float(MANIPULATION_WEIGHTS["wash_trade_pattern"]), [f"{wash_days} days with high volume but flat price range (<0.5%) — possible wash trading."]
    elif wash_days >= 1:
        return float(MANIPULATION_WEIGHTS["wash_trade_pattern"]) * 0.4, [f"{wash_days} potential wash-trade day(s) detected."]
    return 0.0, []


def _check_pump_dump_shape(df: pd.DataFrame) -> tuple[float, list]:
    """Rule 4: Exponential rise followed by sharp crash pattern."""
    close = df["Close"]
    if len(close) < 60:
        return 0.0, []
    # Look at rolling max drawdown from peak within windows
    peaks = []
    for window in [30, 60]:
        rolling_max = close.rolling(window).max()
        drawdown = (close - rolling_max) / rolling_max
        worst = drawdown.min()
        if worst < -0.30:   # 30% drawdown from peak within window
            # Check if there was a run-up of >40% before the peak
            peak_idx = rolling_max.iloc[-window:].idxmax()
            if peak_idx in close.index:
                loc = close.index.get_loc(peak_idx)
                if loc >= 20:
                    pre_peak = close.iloc[max(0, loc-20):loc]
                    run_up = (pre_peak.iloc[-1] - pre_peak.iloc[0]) / pre_peak.iloc[0] if pre_peak.iloc[0] > 0 else 0
                    if run_up > 0.40:
                        peaks.append((window, run_up, worst))
    if peaks:
        best = max(peaks, key=lambda x: x[1])
        return float(MANIPULATION_WEIGHTS["pump_dump_shape"]), [
            f"Pump & dump pattern detected: +{best[1]*100:.1f}% run-up followed by {best[2]*100:.1f}% crash within {best[0]} days."
        ]
    return 0.0, []


def _check_isolation_forest(anomaly_report) -> tuple[float, list]:
    """Rule 5: Use anomaly detection output."""
    if anomaly_report is None:
        return 0.0, []
    rate = anomaly_report.contamination_rate
    count = len(anomaly_report.anomaly_dates)
    if rate > 0.08 or count >= 10:
        return float(MANIPULATION_WEIGHTS["isolation_forest_cluster"]), [
            f"ML anomaly detector flagged {count} suspicious trading days ({rate*100:.1f}% of window)."
        ]
    elif rate > 0.05 or count >= 5:
        return float(MANIPULATION_WEIGHTS["isolation_forest_cluster"]) * 0.6, [
            f"ML model detected {count} anomalous trading days."
        ]
    return 0.0, []


def run_manipulation_scoring(
    df: pd.DataFrame,
    ticker: str = "",
    anomaly_report=None,
) -> ManipulationReport:
    report = ManipulationReport(ticker=ticker)

    rules = [
        ("Abnormal Volume Spikes",      _check_abnormal_volume(df)),
        ("Price Spike Without Volume",  _check_price_spike_no_volume(df)),
        ("Wash Trade Pattern",          _check_wash_trade_pattern(df)),
        ("Pump & Dump Shape",           _check_pump_dump_shape(df)),
        ("ML Anomaly Cluster",          _check_isolation_forest(anomaly_report)),
    ]

    total_score = 0.0
    triggered = []
    all_evidence = []
    for name, (score_contribution, evidence) in rules:
        if score_contribution > 0:
            triggered.append({"rule": name, "contribution": round(score_contribution, 1)})
            all_evidence.extend(evidence)
            total_score += score_contribution

    report.score = min(100.0, round(total_score, 1))
    report.triggered_rules = triggered
    report.evidence = all_evidence

    for level, (lo, hi) in MANIPULATION_THRESHOLDS.items():
        if lo <= report.score < hi:
            report.risk_level = level
            break
    else:
        report.risk_level = "CRITICAL"

    explanations = {
        "LOW":      "No significant manipulation patterns detected. Trading activity appears within normal parameters.",
        "MEDIUM":   "Some unusual patterns detected. Proceed with caution and monitor volume/price activity closely.",
        "HIGH":     "Multiple manipulation indicators triggered. High probability of coordinated price/volume activity.",
        "CRITICAL": "Extreme manipulation risk. Multiple rule violations and ML anomalies suggest orchestrated market activity.",
    }
    report.explanation = explanations[report.risk_level]
    logger.info(f"Manipulation: {ticker} → {report.risk_level} (score={report.score})")
    return report
