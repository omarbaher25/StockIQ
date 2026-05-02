"""
ml/anomaly_detector.py — Isolation Forest anomaly detection on price/volume features
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

CONTAMINATION = 0.05   # Expected anomaly rate
N_ESTIMATORS  = 200
RANDOM_STATE  = 42

@dataclass
class AnomalyReport:
    ticker: str
    anomaly_dates: list = field(default_factory=list)   # list of date strings
    anomaly_scores: pd.Series = field(default=None, repr=False)
    feature_names: list = field(default_factory=list)
    feature_importances: dict = field(default_factory=dict)  # approximate
    contamination_rate: float = 0.0
    df_with_flags: Optional[pd.DataFrame] = field(default=None, repr=False)

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "anomaly_count": len(self.anomaly_dates),
            "contamination_rate": round(self.contamination_rate, 4),
            "recent_anomalies": self.anomaly_dates[-10:],
            "feature_importances": {k: round(v, 4) for k, v in self.feature_importances.items()},
        }


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    feats = pd.DataFrame(index=df.index)
    close = df["Close"]
    volume = df["Volume"]

    feats["price_change_pct"] = close.pct_change()
    feats["price_range_pct"]  = (df["High"] - df["Low"]) / close.shift(1).replace(0, np.nan)
    feats["gap_up_pct"]       = (df["Open"] - close.shift(1)) / close.shift(1).replace(0, np.nan)
    feats["gap_down_pct"]     = (close.shift(1) - df["Open"]) / close.shift(1).replace(0, np.nan)

    vol_mean = volume.rolling(20).mean()
    vol_std  = volume.rolling(20).std().replace(0, np.nan)
    feats["volume_zscore"]    = (volume - vol_mean) / vol_std
    feats["volume_price_corr"] = (feats["price_change_pct"] * feats["volume_zscore"]).rolling(5).mean()

    feats["close_vs_sma20"]   = (close / close.rolling(20).mean()) - 1
    feats["upper_shadow"]     = (df["High"] - df[["Open","Close"]].max(axis=1)) / (close + 0.001)
    feats["lower_shadow"]     = (df[["Open","Close"]].min(axis=1) - df["Low"]) / (close + 0.001)

    feats.replace([np.inf, -np.inf], np.nan, inplace=True)
    feats.dropna(inplace=True)
    return feats


def run_anomaly_detection(df: pd.DataFrame, ticker: str = "") -> AnomalyReport:
    report = AnomalyReport(ticker=ticker)
    if len(df) < 40:
        logger.warning(f"Anomaly detection: insufficient data for {ticker} ({len(df)} rows).")
        return report

    feats = _build_features(df)
    if feats.empty or len(feats) < 20:
        return report

    scaler = StandardScaler()
    X = scaler.fit_transform(feats.values)

    model = IsolationForest(
        n_estimators=N_ESTIMATORS,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    preds = model.fit_predict(X)           # -1 = anomaly, 1 = normal
    scores = model.score_samples(X)        # lower = more anomalous

    anomaly_mask = preds == -1
    anomaly_dates = [str(d.date()) if hasattr(d, 'date') else str(d) for d in feats.index[anomaly_mask]]

    report.anomaly_dates = anomaly_dates
    report.contamination_rate = anomaly_mask.mean()
    report.feature_names = feats.columns.tolist()

    # ── Approximate feature importance (mean absolute deviation in anomalous vs normal rows) ──
    X_df = pd.DataFrame(X, columns=feats.columns, index=feats.index)
    importances = {}
    for col in feats.columns:
        normal_mean  = X_df.loc[~anomaly_mask, col].abs().mean()
        anomaly_mean = X_df.loc[anomaly_mask, col].abs().mean() if anomaly_mask.any() else 0
        importances[col] = round(float(anomaly_mean - normal_mean), 4)
    report.feature_importances = dict(sorted(importances.items(), key=lambda x: -x[1]))

    # ── Attach flags to original df ──────────────────────────────────────────
    df_out = df.copy()
    df_out["anomaly_score"] = np.nan
    df_out["is_anomaly"]    = False
    df_out.loc[feats.index, "anomaly_score"] = -scores   # invert: higher = more anomalous
    df_out.loc[feats.index, "is_anomaly"]    = anomaly_mask
    report.df_with_flags  = df_out
    report.anomaly_scores = pd.Series(-scores, index=feats.index)

    logger.info(f"Anomaly detection: {ticker} — {len(anomaly_dates)} anomalies ({report.contamination_rate:.1%})")
    return report
