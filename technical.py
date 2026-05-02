"""
analysis/technical.py — Technical indicator engine (RSI, MACD, Bollinger, MAs, ATR, OBV)
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import numpy as np
from config import (RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
                    BB_PERIOD, BB_STD, ATR_PERIOD, SMA_SHORT, SMA_MED, SMA_LONG, VOLUME_ZSCORE_WINDOW)

logger = logging.getLogger(__name__)


@dataclass
class TechnicalSignal:
    indicator: str
    value: Optional[float]
    signal: str        # BUY | SELL | NEUTRAL
    confidence: float  # 0–1
    note: str

@dataclass
class TechnicalReport:
    ticker: str
    signals: list = field(default_factory=list)
    overall_signal: str = "NEUTRAL"
    overall_confidence: float = 0.0
    df: Optional[pd.DataFrame] = field(default=None, repr=False)

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "overall_signal": self.overall_signal,
            "overall_confidence": round(self.overall_confidence, 3),
            "signals": [{"indicator": s.indicator, "value": round(s.value, 4) if s.value else None,
                         "signal": s.signal, "confidence": round(s.confidence, 2), "note": s.note}
                        for s in self.signals],
        }


# ─── Indicator Computations ───────────────────────────────────────────────────

def _compute_rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _compute_macd(close: pd.Series):
    ema_fast = close.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = close.ewm(span=MACD_SLOW, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def _compute_bollinger(close: pd.Series):
    sma = close.rolling(BB_PERIOD).mean()
    std = close.rolling(BB_PERIOD).std()
    upper = sma + BB_STD * std
    lower = sma - BB_STD * std
    return upper, sma, lower

def _compute_atr(high, low, close, period=ATR_PERIOD):
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def _compute_obv(close, volume):
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()

def _compute_volume_zscore(volume, window=VOLUME_ZSCORE_WINDOW):
    mean = volume.rolling(window).mean()
    std = volume.rolling(window).std()
    return (volume - mean) / std.replace(0, np.nan)


# ─── Signal Analysis ──────────────────────────────────────────────────────────

def _analyze_rsi(df: pd.DataFrame) -> TechnicalSignal:
    rsi = df["RSI"].dropna()
    if rsi.empty:
        return TechnicalSignal("RSI", None, "NEUTRAL", 0.0, "Insufficient data.")
    val = rsi.iloc[-1]
    if val >= RSI_OVERBOUGHT:
        sig, conf, note = "SELL", min(1.0, (val - RSI_OVERBOUGHT) / 30), f"RSI {val:.1f} — overbought. Reversal risk."
    elif val <= RSI_OVERSOLD:
        sig, conf, note = "BUY", min(1.0, (RSI_OVERSOLD - val) / 30), f"RSI {val:.1f} — oversold. Potential bounce."
    else:
        sig, conf, note = "NEUTRAL", 0.4, f"RSI {val:.1f} — in neutral territory."
    return TechnicalSignal("RSI (14)", val, sig, conf, note)

def _analyze_macd(df: pd.DataFrame) -> TechnicalSignal:
    macd = df["MACD"].dropna()
    sig_line = df["MACD_Signal"].dropna()
    hist = df["MACD_Hist"].dropna()
    if len(macd) < 2:
        return TechnicalSignal("MACD", None, "NEUTRAL", 0.0, "Insufficient data.")
    macd_val = macd.iloc[-1]
    hist_val = hist.iloc[-1]
    prev_hist = hist.iloc[-2]
    if hist_val > 0 and hist_val > prev_hist:
        sig, conf, note = "BUY", min(1.0, abs(hist_val) / (abs(macd_val) + 0.001)), "MACD histogram expanding above zero — bullish momentum."
    elif hist_val < 0 and hist_val < prev_hist:
        sig, conf, note = "SELL", min(1.0, abs(hist_val) / (abs(macd_val) + 0.001)), "MACD histogram expanding below zero — bearish momentum."
    elif hist_val > 0 and hist_val < prev_hist:
        sig, conf, note = "NEUTRAL", 0.35, "MACD positive but histogram shrinking — momentum fading."
    else:
        sig, conf, note = "NEUTRAL", 0.35, "MACD negative but histogram shrinking — possible stabilization."
    return TechnicalSignal("MACD (12/26/9)", macd_val, sig, conf, note)

def _analyze_bollinger(df: pd.DataFrame) -> TechnicalSignal:
    close = df["Close"].iloc[-1]
    upper = df["BB_Upper"].iloc[-1]
    lower = df["BB_Lower"].iloc[-1]
    mid = df["BB_Mid"].iloc[-1]
    if pd.isna(upper):
        return TechnicalSignal("Bollinger Bands", None, "NEUTRAL", 0.0, "Insufficient data.")
    band_width = upper - lower
    position = (close - lower) / band_width if band_width > 0 else 0.5
    if close > upper:
        sig, conf, note = "SELL", 0.70, f"Price above upper band (${upper:.2f}) — overbought extension."
    elif close < lower:
        sig, conf, note = "BUY", 0.70, f"Price below lower band (${lower:.2f}) — oversold extension."
    elif position > 0.7:
        sig, conf, note = "NEUTRAL", 0.45, "Price in upper Bollinger zone — approaching resistance."
    elif position < 0.3:
        sig, conf, note = "NEUTRAL", 0.45, "Price in lower Bollinger zone — approaching support."
    else:
        sig, conf, note = "NEUTRAL", 0.30, "Price within Bollinger bands — no directional signal."
    return TechnicalSignal("Bollinger Bands", position, sig, conf, note)

def _analyze_moving_averages(df: pd.DataFrame) -> list:
    signals = []
    close = df["Close"].iloc[-1]
    for label, col in [("SMA 20", "SMA_20"), ("SMA 50", "SMA_50"), ("SMA 200", "SMA_200")]:
        if col in df.columns and not pd.isna(df[col].iloc[-1]):
            ma = df[col].iloc[-1]
            if close > ma:
                signals.append(TechnicalSignal(label, ma, "BUY", 0.60, f"Price ${close:.2f} above {label} ${ma:.2f} — bullish."))
            else:
                signals.append(TechnicalSignal(label, ma, "SELL", 0.60, f"Price ${close:.2f} below {label} ${ma:.2f} — bearish."))
    # Golden/Death cross (SMA50 vs SMA200)
    if "SMA_50" in df.columns and "SMA_200" in df.columns:
        sma50 = df["SMA_50"].dropna()
        sma200 = df["SMA_200"].dropna()
        if len(sma50) >= 2 and len(sma200) >= 2:
            if sma50.iloc[-1] > sma200.iloc[-1] and sma50.iloc[-2] <= sma200.iloc[-2]:
                signals.append(TechnicalSignal("Golden Cross", sma50.iloc[-1], "BUY", 0.85, "SMA50 crossed above SMA200 — Golden Cross bullish signal."))
            elif sma50.iloc[-1] < sma200.iloc[-1] and sma50.iloc[-2] >= sma200.iloc[-2]:
                signals.append(TechnicalSignal("Death Cross", sma50.iloc[-1], "SELL", 0.85, "SMA50 crossed below SMA200 — Death Cross bearish signal."))
    return signals

def _analyze_volume(df: pd.DataFrame) -> TechnicalSignal:
    if "Volume_ZScore" not in df.columns:
        return TechnicalSignal("Volume", None, "NEUTRAL", 0.0, "Volume Z-score unavailable.")
    z = df["Volume_ZScore"].iloc[-1]
    if pd.isna(z):
        return TechnicalSignal("Volume Z-Score", None, "NEUTRAL", 0.0, "Insufficient data.")
    if z > 3.0:
        sig, conf, note = "NEUTRAL", 0.80, f"Volume Z-score {z:.2f} — extreme spike. Possible news catalyst or manipulation."
    elif z > 2.0:
        sig, conf, note = "NEUTRAL", 0.60, f"Volume Z-score {z:.2f} — significant above-average volume."
    elif z < -1.0:
        sig, conf, note = "NEUTRAL", 0.40, f"Volume Z-score {z:.2f} — unusually low volume. Low conviction."
    else:
        sig, conf, note = "NEUTRAL", 0.30, f"Volume Z-score {z:.2f} — normal volume."
    return TechnicalSignal("Volume Z-Score", z, sig, conf, note)


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def run_technical_analysis(df: pd.DataFrame, ticker: str = "") -> TechnicalReport:
    df = df.copy()
    close, high, low, volume = df["Close"], df["High"], df["Low"], df["Volume"]

    df["RSI"] = _compute_rsi(close)
    df["MACD"], df["MACD_Signal"], df["MACD_Hist"] = _compute_macd(close)
    df["BB_Upper"], df["BB_Mid"], df["BB_Lower"] = _compute_bollinger(close)
    df["SMA_20"] = close.rolling(SMA_SHORT).mean()
    df["SMA_50"] = close.rolling(SMA_MED).mean()
    df["SMA_200"] = close.rolling(SMA_LONG).mean()
    df["EMA_12"] = close.ewm(span=12, adjust=False).mean()
    df["EMA_26"] = close.ewm(span=26, adjust=False).mean()
    df["ATR"] = _compute_atr(high, low, close)
    df["OBV"] = _compute_obv(close, volume)
    df["Volume_ZScore"] = _compute_volume_zscore(volume)

    signals = []
    signals.append(_analyze_rsi(df))
    signals.append(_analyze_macd(df))
    signals.append(_analyze_bollinger(df))
    signals.extend(_analyze_moving_averages(df))
    signals.append(_analyze_volume(df))

    buy_score = sum(s.confidence for s in signals if s.signal == "BUY")
    sell_score = sum(s.confidence for s in signals if s.signal == "SELL")
    total = buy_score + sell_score
    if total == 0:
        overall, conf = "NEUTRAL", 0.0
    elif buy_score > sell_score:
        overall, conf = "BUY", buy_score / (total + 0.001)
    else:
        overall, conf = "SELL", sell_score / (total + 0.001)

    report = TechnicalReport(ticker=ticker, signals=signals, overall_signal=overall,
                             overall_confidence=round(conf, 3), df=df)
    logger.info(f"Technical: {ticker} → {overall} ({conf:.2%})")
    return report
