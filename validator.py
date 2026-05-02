"""
data/validator.py — Data quality validation layer
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

MIN_ROWS = 30  # Minimum rows for meaningful analysis


@dataclass
class ValidationResult:
    ok: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        parts = []
        if self.errors:
            parts.append("ERRORS: " + "; ".join(self.errors))
        if self.warnings:
            parts.append("WARNINGS: " + "; ".join(self.warnings))
        return " | ".join(parts) if parts else "All checks passed"


def validate_ohlcv(df: pd.DataFrame) -> ValidationResult:
    """
    Validate an OHLCV DataFrame for analysis readiness.
    """
    warnings: list[str] = []
    errors: list[str] = []

    # ── Row count ────────────────────────────────────────────────────────────
    if df is None or df.empty:
        errors.append("DataFrame is empty — no data was fetched.")
        return ValidationResult(ok=False, errors=errors)

    if len(df) < MIN_ROWS:
        warnings.append(
            f"Only {len(df)} rows available (< {MIN_ROWS}). "
            "Analysis may be less reliable."
        )

    # ── Required columns ─────────────────────────────────────────────────────
    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required - set(df.columns)
    if missing:
        errors.append(f"Missing columns: {missing}")
        return ValidationResult(ok=False, errors=errors)

    # ── NaN check ────────────────────────────────────────────────────────────
    nan_counts = df[list(required)].isna().sum()
    high_nan = nan_counts[nan_counts > len(df) * 0.05]
    if not high_nan.empty:
        warnings.append(
            f"High NaN rates in: "
            + ", ".join(f"{c}={v}" for c, v in high_nan.items())
        )

    # ── Negative / zero prices ───────────────────────────────────────────────
    if (df["Close"] <= 0).any():
        n = (df["Close"] <= 0).sum()
        errors.append(f"{n} rows with non-positive Close prices detected.")

    # ── Zero-volume days (suspicious) ────────────────────────────────────────
    zero_vol = (df["Volume"] == 0).sum()
    if zero_vol > len(df) * 0.10:
        warnings.append(
            f"{zero_vol} zero-volume days ({zero_vol/len(df):.1%}). "
            "Possible illiquid or halted trading periods."
        )

    # ── OHLC consistency ─────────────────────────────────────────────────────
    inconsistent = ((df["High"] < df["Low"]) | (df["High"] < df["Open"]) |
                    (df["High"] < df["Close"])).sum()
    if inconsistent > 0:
        warnings.append(f"{inconsistent} rows with inconsistent OHLC values.")

    # ── Extreme single-day moves (>50%) — data error flag ────────────────────
    daily_ret = df["Close"].pct_change().abs()
    extreme = (daily_ret > 0.50).sum()
    if extreme > 2:
        warnings.append(
            f"{extreme} days with >50% price change. "
            "Possible data error or stock split not adjusted."
        )

    ok = len(errors) == 0
    return ValidationResult(ok=ok, warnings=warnings, errors=errors)


def validate_company_info(info: dict) -> ValidationResult:
    """Validate that essential company info fields are present."""
    warnings: list[str] = []
    errors: list[str] = []

    if "error" in info:
        errors.append(f"API error: {info['error']}")
        return ValidationResult(ok=False, errors=errors)

    if not info.get("name") or info.get("name") == info.get("ticker"):
        warnings.append("Company name not found — ticker may be invalid or delisted.")

    # Essential: Price
    if not info.get("current_price"):
        errors.append("Current price data missing. Analysis cannot proceed.")

    # Market-specific leniency
    exchange = info.get("exchange", "").upper()
    is_intl = any(ex in exchange for ex in ["CA", "LSE", "EGX", "PAR", "FRA", "HKG", "JP", "CN"])
    
    if not info.get("sector") or info.get("sector") == "N/A":
        warnings.append("Sector information unavailable.")

    if not info.get("market_cap"):
        warnings.append("Market cap unavailable — typical for some micro-caps or international listings.")
    
    if not is_intl and not info.get("float_shares"):
        warnings.append("Float shares data missing.")

    return ValidationResult(ok=len(errors) == 0, warnings=warnings, errors=errors)
