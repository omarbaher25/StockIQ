"""
analysis/valuation.py — Advanced valuation models (WACC, DCF, Fair Value)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import numpy as np
from config import MARKET_RISK_PREMIUM, DEFAULT_TAX_RATE, DEFAULT_GROWTH_RATE

@dataclass
class ValuationReport:
    ticker: str
    current_price: float
    
    # WACC components
    cost_of_equity: float = 0.0
    cost_of_debt: float = 0.0
    wacc: float = 0.0
    equity_weight: float = 0.0
    debt_weight: float = 0.0
    
    # Fair Value estimates
    dcf_value: Optional[float] = None
    graham_value: Optional[float] = None
    fair_value_avg: Optional[float] = None
    upside_pct: Optional[float] = None
    
    # Metadata
    methodology: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

def run_valuation_analysis(ticker: str, info: dict, financials: dict, rf_rate: float, country_risk_premium: float = 0.0) -> ValuationReport:
    report = ValuationReport(ticker=ticker, current_price=info.get("current_price", 0.0))
    
    # 1. Cost of Equity (CAPM)
    beta = info.get("beta") or 1.0
    # Adjusted CAPM: Rf + Beta * ERP + Country Risk Premium
    report.cost_of_equity = rf_rate + beta * (MARKET_RISK_PREMIUM + country_risk_premium)
    
    # 2. Cost of Debt
    total_debt = info.get("totalDebt")
    # If not in info, try balance sheet
    if total_debt is None and "balance" in financials and not financials["balance"].empty:
        try:
            total_debt = financials["balance"].loc["Total Debt"].iloc[0]
        except:
            total_debt = 0.0
            
    interest_expense = 0.0
    if "income" in financials and not financials["income"].empty:
        try:
            interest_expense = abs(financials["income"].loc["Interest Expense"].iloc[0])
        except:
            pass
            
    if total_debt and total_debt > 0:
        pre_tax_cost_of_debt = interest_expense / total_debt
    else:
        pre_tax_cost_of_debt = rf_rate + 0.02 # Proxy: RF + 2% spread
        
    tax_rate = DEFAULT_TAX_RATE
    # Try to estimate tax rate from financials
    if "income" in financials and not financials["income"].empty:
        try:
            tax_prov = abs(financials["income"].loc["Tax Provision"].iloc[0])
            ebit = abs(financials["income"].loc["EBIT"].iloc[0])
            if ebit > 0:
                tax_rate = min(0.4, tax_prov / ebit)
        except:
            pass
            
    report.cost_of_debt = pre_tax_cost_of_debt * (1 - tax_rate)
    
    # 3. WACC calculation
    market_cap = info.get("market_cap") or 0.0
    total_val = market_cap + (total_debt or 0.0)
    
    if total_val > 0:
        report.equity_weight = market_cap / total_val
        report.debt_weight = (total_debt or 0.0) / total_val
        report.wacc = (report.equity_weight * report.cost_of_equity) + \
                      (report.debt_weight * report.cost_of_debt)
    else:
        report.wacc = report.cost_of_equity # Default to COE if no debt info
        
    # 4. DCF Valuation (Simple 5-year)
    fcf = info.get("free_cashflow")
    shares = info.get("shares_outstanding")
    
    if fcf and shares and report.wacc > DEFAULT_GROWTH_RATE:
        # Simple Gordon Growth / Exit Multiple hybrid
        terminal_val = (fcf * (1 + DEFAULT_GROWTH_RATE)) / (report.wacc - DEFAULT_GROWTH_RATE)
        # Discount terminal value (5 years)
        pv_terminal = terminal_val / ((1 + report.wacc) ** 5)
        # Simplified: assume FCF stays constant for 5 years then terminal
        pv_fcf = sum([(fcf) / ((1 + report.wacc) ** i) for i in range(1, 6)])
        report.dcf_value = (pv_fcf + pv_terminal) / shares
    else:
        report.warnings.append("Insufficient FCF or shares data for DCF model.")

    # 5. Graham Number (√(22.5 * EPS * BookValue))
    eps = info.get("eps")
    bvps = info.get("book_value")
    if eps and bvps and eps > 0 and bvps > 0:
        report.graham_value = np.sqrt(22.5 * eps * bvps)
    
    # 6. Aggregate Fair Value
    values = [v for v in [report.dcf_value, report.graham_value, info.get("analyst_target")] if v is not None and v > 0]
    if values:
        report.fair_value_avg = sum(values) / len(values)
        if report.current_price > 0:
            report.upside_pct = (report.fair_value_avg - report.current_price) / report.current_price
            
    report.methodology = "Hybrid model using CAPM for WACC, 5-year DCF for intrinsic value, and Graham Number for value floor."
    
    return report
