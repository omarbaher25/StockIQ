"""
analysis/fundamental.py — Fundamental financial analysis engine
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from config import PE_FAIR_LOW, PE_FAIR_HIGH, DEBT_EQUITY_SAFE, CURRENT_RATIO_SAFE, GROSS_MARGIN_GOOD

logger = logging.getLogger(__name__)

@dataclass
class MetricResult:
    name: str
    value: Optional[float]
    score: float
    label: str
    interpretation: str
    unit: str = ""

    def formatted_value(self) -> str:
        if self.value is None: return "N/A"
        if self.unit == "%": return f"{self.value * 100:.2f}%"
        if self.unit == "x": return f"{self.value:.2f}x"
        if abs(self.value) >= 1e9: return f"${self.value / 1e9:.2f}B"
        if abs(self.value) >= 1e6: return f"${self.value / 1e6:.2f}M"
        return f"{self.value:.2f}"

@dataclass
class FundamentalReport:
    ticker: str
    metrics: list = field(default_factory=list)
    overall_score: float = 0.0
    overall_label: str = "N/A"
    summary: str = ""

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "overall_score": round(self.overall_score, 2),
            "overall_label": self.overall_label,
            "summary": self.summary,
            "metrics": [{"name": m.name, "value": m.formatted_value(), "score": round(m.score,1), "label": m.label, "interpretation": m.interpretation} for m in self.metrics],
        }

def _score_pe(pe):
    if pe is None or pe <= 0 or pe > 2000:
        return MetricResult("P/E Ratio", pe, 5.0, "N/A", "P/E unavailable — company may be unprofitable.", "x")
    if pe < PE_FAIR_LOW: score, label, interp = 8.5, "UNDERVALUED", f"P/E {pe:.1f}x below fair-value floor ({PE_FAIR_LOW}x)."
    elif pe <= PE_FAIR_HIGH: score, label, interp = 7.0, "FAIR", f"P/E {pe:.1f}x within fair-value band."
    elif pe <= 40: score, label, interp = 5.0, "ELEVATED", f"P/E {pe:.1f}x elevated — high growth expectations priced in."
    else: score, label, interp = 3.0, "EXPENSIVE", f"P/E {pe:.1f}x very high — aggressive growth assumed."
    return MetricResult("P/E Ratio", pe, score, label, interp, "x")

def _score_forward_pe(fpe):
    if fpe is None or fpe <= 0:
        return MetricResult("Forward P/E", fpe, 5.0, "N/A", "Forward P/E unavailable.", "x")
    if fpe < 15: score, label, interp = 8.0, "ATTRACTIVE", f"Forward P/E {fpe:.1f}x — strong earnings growth expected."
    elif fpe <= 25: score, label, interp = 6.5, "FAIR", f"Forward P/E {fpe:.1f}x within typical growth ranges."
    else: score, label, interp = 4.0, "STRETCHED", f"Forward P/E {fpe:.1f}x — high assumptions carry valuation risk."
    return MetricResult("Forward P/E", fpe, score, label, interp, "x")

def _score_gross_margin(gm):
    if gm is None:
        return MetricResult("Gross Margin", gm, 5.0, "N/A", "Gross margin unavailable.", "%")
    if gm >= 0.60: score, label, interp = 9.5, "EXCELLENT", f"Gross margin {gm*100:.1f}% — very high pricing power."
    elif gm >= GROSS_MARGIN_GOOD: score, label, interp = 7.5, "STRONG", f"Gross margin {gm*100:.1f}% — healthy product economics."
    elif gm >= 0.20: score, label, interp = 5.5, "MODERATE", f"Gross margin {gm*100:.1f}% — acceptable but below best-in-class."
    elif gm >= 0.05: score, label, interp = 3.5, "THIN", f"Gross margin {gm*100:.1f}% — thin, vulnerable to cost increases."
    else: score, label, interp = 1.5, "CRITICAL", f"Gross margin {gm*100:.1f}% — near zero or negative."
    return MetricResult("Gross Margin", gm, score, label, interp, "%")

def _score_operating_margin(om):
    if om is None:
        return MetricResult("Operating Margin", om, 5.0, "N/A", "Operating margin unavailable.", "%")
    if om >= 0.25: score, label, interp = 9.0, "EXCELLENT", f"Operating margin {om*100:.1f}% — highly efficient."
    elif om >= 0.10: score, label, interp = 7.0, "STRONG", f"Operating margin {om*100:.1f}% — solid cost discipline."
    elif om >= 0.03: score, label, interp = 5.0, "FAIR", f"Operating margin {om*100:.1f}% — positive but modest."
    elif om >= 0: score, label, interp = 3.0, "WEAK", f"Operating margin {om*100:.1f}% — barely profitable."
    else: score, label, interp = 1.5, "LOSS-MAKING", f"Negative operating margin {om*100:.1f}% — burning cash."
    return MetricResult("Operating Margin", om, score, label, interp, "%")

def _score_net_margin(nm):
    if nm is None:
        return MetricResult("Net Margin", nm, 5.0, "N/A", "Net margin unavailable.", "%")
    if nm >= 0.20: score, label, interp = 9.0, "EXCELLENT", f"Net margin {nm*100:.1f}% — exceptional profitability."
    elif nm >= 0.08: score, label, interp = 7.0, "STRONG", f"Net margin {nm*100:.1f}% — healthy bottom line."
    elif nm >= 0.02: score, label, interp = 5.0, "FAIR", f"Net margin {nm*100:.1f}% — marginally profitable."
    elif nm >= 0: score, label, interp = 3.0, "THIN", f"Near-zero net margin {nm*100:.1f}%."
    else: score, label, interp = 1.5, "NET LOSS", f"Net loss — margin {nm*100:.1f}%."
    return MetricResult("Net Margin", nm, score, label, interp, "%")

def _score_revenue_growth(rg):
    if rg is None:
        return MetricResult("Revenue Growth (YoY)", rg, 5.0, "N/A", "Revenue growth unavailable.", "%")
    if rg >= 0.30: score, label, interp = 9.5, "HYPERGROWTH", f"Revenue growing {rg*100:.1f}% YoY — exceptional."
    elif rg >= 0.15: score, label, interp = 8.0, "STRONG", f"Revenue growing {rg*100:.1f}% YoY."
    elif rg >= 0.05: score, label, interp = 6.0, "MODERATE", f"Revenue growing {rg*100:.1f}% YoY — steady."
    elif rg >= 0: score, label, interp = 4.0, "FLAT", f"Near-flat revenue growth {rg*100:.1f}%."
    else: score, label, interp = 2.0, "DECLINING", f"Revenue declining {abs(rg)*100:.1f}% YoY."
    return MetricResult("Revenue Growth (YoY)", rg, score, label, interp, "%")

def _score_debt_equity(de):
    if de is None:
        return MetricResult("Debt/Equity", de, 5.0, "N/A", "D/E unavailable.", "x")
    de_norm = de / 100 if de > 10 else de
    if de_norm <= 0.3: score, label, interp = 9.0, "CONSERVATIVE", f"D/E {de_norm:.2f}x — very low leverage."
    elif de_norm <= DEBT_EQUITY_SAFE: score, label, interp = 7.0, "MANAGEABLE", f"D/E {de_norm:.2f}x — within safe range."
    elif de_norm <= 2.0: score, label, interp = 5.0, "ELEVATED", f"D/E {de_norm:.2f}x — moderate leverage."
    else: score, label, interp = 2.5, "HIGH LEVERAGE", f"D/E {de_norm:.2f}x — significant financial risk."
    return MetricResult("Debt/Equity", de_norm, score, label, interp, "x")

def _score_current_ratio(cr):
    if cr is None:
        return MetricResult("Current Ratio", cr, 5.0, "N/A", "Current ratio unavailable.", "x")
    if cr >= CURRENT_RATIO_SAFE: score, label, interp = 8.5, "HEALTHY", f"Current ratio {cr:.2f}x — sufficient liquidity."
    elif cr >= 1.0: score, label, interp = 6.0, "ADEQUATE", f"Current ratio {cr:.2f}x — tight but manageable."
    else: score, label, interp = 3.0, "STRESSED", f"Current ratio {cr:.2f}x — current liabilities exceed assets."
    return MetricResult("Current Ratio", cr, score, label, interp, "x")

def _score_roe(roe):
    if roe is None:
        return MetricResult("Return on Equity", roe, 5.0, "N/A", "ROE unavailable.", "%")
    if roe >= 0.20: score, label, interp = 9.0, "EXCELLENT", f"ROE {roe*100:.1f}% — exceptional shareholder returns."
    elif roe >= 0.10: score, label, interp = 7.0, "GOOD", f"ROE {roe*100:.1f}% above cost-of-equity benchmarks."
    elif roe >= 0.05: score, label, interp = 5.0, "FAIR", f"ROE {roe*100:.1f}% — positive but below hurdle rates."
    elif roe >= 0: score, label, interp = 3.5, "WEAK", f"Near-zero ROE {roe*100:.1f}%."
    else: score, label, interp = 2.0, "NEGATIVE", f"Negative ROE {roe*100:.1f}% — equity being eroded."
    return MetricResult("Return on Equity", roe, score, label, interp, "%")

def _score_peg(peg):
    if peg is None or peg <= 0:
        return MetricResult("PEG Ratio", peg, 5.0, "N/A", "PEG ratio unavailable.", "x")
    if peg < 1.0: score, label, interp = 9.0, "UNDERVALUED", f"PEG {peg:.2f}x < 1 — undervalued vs growth rate."
    elif peg <= 2.0: score, label, interp = 6.5, "FAIR", f"PEG {peg:.2f}x — growth fairly priced."
    else: score, label, interp = 3.5, "OVERVALUED", f"PEG {peg:.2f}x > 2 — growth is expensive."
    return MetricResult("PEG Ratio", peg, score, label, interp, "x")

def run_fundamental_analysis(info: dict) -> FundamentalReport:
    ticker = info.get("ticker", "UNKNOWN")
    report = FundamentalReport(ticker=ticker)
    metrics = [
        _score_pe(info.get("trailing_pe")),
        _score_forward_pe(info.get("forward_pe")),
        _score_peg(info.get("peg_ratio")),
        _score_gross_margin(info.get("gross_margins")),
        _score_operating_margin(info.get("operating_margin")),
        _score_net_margin(info.get("profit_margin")),
        _score_revenue_growth(info.get("revenue_growth")),
        _score_debt_equity(info.get("debt_to_equity")),
        _score_current_ratio(info.get("current_ratio")),
        _score_roe(info.get("return_on_equity")),
    ]
    report.metrics = metrics
    valid = [m for m in metrics if m.label != "N/A"]
    report.overall_score = round(np.mean([m.score for m in valid]), 2) if valid else 5.0
    if report.overall_score >= 8.0:   report.overall_label, report.summary = "STRONG BUY", "Excellent fundamentals across valuation, profitability, and balance sheet health."
    elif report.overall_score >= 6.5: report.overall_label, report.summary = "BULLISH", "Solid fundamentals with minor concerns. Suitable for growth-oriented investors."
    elif report.overall_score >= 5.0: report.overall_label, report.summary = "NEUTRAL", "Mixed fundamentals. Stable but lacking strong catalysts."
    elif report.overall_score >= 3.5: report.overall_label, report.summary = "BEARISH", "Weak fundamentals. Exercise caution and monitor closely."
    else:                              report.overall_label, report.summary = "AVOID", "Poor fundamentals across multiple dimensions. High risk."
    logger.info(f"Fundamental: {ticker} → {report.overall_label} ({report.overall_score}/10)")
    return report
