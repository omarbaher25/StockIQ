"""
analysis/macro.py — Macroeconomic analysis & risk scoring
Evaluates country-level risk factors (Inflation, Interest Rates, GDP).
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class MacroReport:
    country: str
    inflation_rate: float
    interest_rate: float
    gdp_growth: float
    currency: str
    risk_score: float = 0.0 # 0-10 (higher is riskier)
    risk_label: str = "LOW"
    summary: str = ""
    timestamp: str = ""

    def to_dict(self):
        return self.__dict__

def run_macro_analysis(country: str, macro_data: dict) -> MacroReport:
    """
    Score the macroeconomic risk of a country.
    """
    report = MacroReport(
        country=country,
        inflation_rate=macro_data.get("inflation", 0.0),
        interest_rate=macro_data.get("interest_rate", 0.0),
        gdp_growth=macro_data.get("gdp_growth", 0.0),
        currency=macro_data.get("currency", "USD"),
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    # 1. Inflation Risk (Target ~2%)
    inf = report.inflation_rate
    inf_points = min(4, max(0, (inf - 0.02) * 20)) # 20% inflation = 3.6 points
    
    # 2. Interest Rate Risk (Cost of Capital)
    ir = report.interest_rate
    ir_points = min(3, max(0, (ir - 0.02) * 10)) # 5% IR = 0.3 points, 20% IR = 1.8 points
    
    # 3. GDP Risk (Growth stability)
    gdp = report.gdp_growth
    gdp_points = 3 if gdp < 0 else 2 if gdp < 0.01 else 1 if gdp < 0.03 else 0
    
    report.risk_score = min(10.0, inf_points + ir_points + gdp_points)
    
    if report.risk_score < 3:
        report.risk_label = "LOW"
        report.summary = f"Stable macroeconomic environment in {country}."
    elif report.risk_score < 6:
        report.risk_label = "MEDIUM"
        report.summary = f"Moderate macroeconomic headwinds in {country} (e.g. inflation or slowing growth)."
    else:
        report.risk_label = "HIGH"
        report.summary = f"High macroeconomic risk in {country}. Elevated inflation or interest rates may compress valuations."

    return report
