"""
data/fetcher.py — Multi-source financial data acquisition layer
"""
from __future__ import annotations

import time
import logging
from datetime import datetime, timedelta
from typing import Optional

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import re

from config import DEFAULT_PERIOD, DEFAULT_INTERVAL, GLOBAL_NEWS_FEEDS, BOND_TICKERS
from data.web_scraper import fetch_google_news_rss, fetch_mubasher_news

logger = logging.getLogger(__name__)


# ─── Risk-Free Rate ──────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_risk_free_rate(country: str = "US") -> float:
    """
    Fetch current 10-Year Treasury Yield proxy for risk-free rate.
    """
    proxies = {
        "US": "^TNX",
        "UK": "^GILT10", # Not always available, fallback needed
        "DE": "^BUND10",
        "EG": "EGX30", # Proxy spread
    }
    symbol = proxies.get(country, "^TNX")
    try:
        tnx = yf.Ticker(symbol)
        rate = tnx.info.get("regularMarketPrice") or tnx.info.get("previousClose")
        if rate:
            # For non-US, might need normalization
            return rate / 100.0 if rate < 100 else rate / 1000.0
        return 0.042
    except Exception:
        return 0.042


# ─── Macro Data ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400)
def fetch_macro_data(country: str) -> dict:
    """
    Fetch key macroeconomic indicators for a country.
    """
    # Hardcoded recent fallbacks/proxies since live macro APIs are often restricted
    macro_map = {
        "Egypt": {"inflation": 0.325, "interest_rate": 0.2725, "gdp_growth": 0.024, "currency": "EGP"},
        "United States": {"inflation": 0.034, "interest_rate": 0.0525, "gdp_growth": 0.021, "currency": "USD"},
        "United Kingdom": {"inflation": 0.023, "interest_rate": 0.0525, "gdp_growth": 0.003, "currency": "GBP"},
        "Germany": {"inflation": 0.022, "interest_rate": 0.0425, "gdp_growth": -0.002, "currency": "EUR"},
    }
    return macro_map.get(country, macro_map["United States"])


# ─── Company Info ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_company_info(ticker: str) -> dict:
    """
    Return company metadata dict from yfinance.
    Keys: longName, sector, industry, country, marketCap, employees,
          website, summary, currency, exchange, logo_url
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return {
            "ticker": ticker.upper(),
            "name": info.get("longName") or info.get("shortName", ticker.upper()),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "country": info.get("country", "N/A"),
            "exchange": info.get("exchange", "N/A"),
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("marketCap"),
            "employees": info.get("fullTimeEmployees"),
            "website": info.get("website", ""),
            "summary": info.get("longBusinessSummary", ""),
            "logo_url": info.get("logo_url", ""),
            # Valuation quick-access
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "previous_close": info.get("previousClose"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "beta": info.get("beta"),
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "dividend_yield": info.get("dividendYield"),
            "eps": info.get("trailingEps"),
            "book_value": info.get("bookValue"),
            "price_to_book": info.get("priceToBook"),
            "enterprise_value": info.get("enterpriseValue"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "return_on_equity": info.get("returnOnEquity"),
            "return_on_assets": info.get("returnOnAssets"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "gross_margins": info.get("grossMargins"),
            "ebitda_margins": info.get("ebitdaMargins"),
            "free_cashflow": info.get("freeCashflow"),
            "operating_cashflow": info.get("operatingCashflow"),
            "recommendation": info.get("recommendationKey", "N/A"),
            "analyst_target": info.get("targetMeanPrice"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "float_shares": info.get("floatShares"),
            "short_ratio": info.get("shortRatio"),
            "peg_ratio": info.get("pegRatio"),
        }
    except Exception as e:
        logger.error(f"fetch_company_info error for {ticker}: {e}")
        return {"ticker": ticker.upper(), "name": ticker.upper(), "error": str(e)}


# ─── OHLCV Historical Data ───────────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_stock_data(
    ticker: str,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch OHLCV historical data.
    Returns a DataFrame with columns: Open, High, Low, Close, Volume
    Index: DatetimeIndex (UTC-normalized)
    """
    try:
        t = yf.Ticker(ticker)
        if start and end:
            df = t.history(start=start, end=end, interval=interval, auto_adjust=True)
        else:
            df = t.history(period=period, interval=interval, auto_adjust=True)

        if df.empty:
            raise ValueError(f"No OHLCV data returned for {ticker}")

        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(subset=["Close"], inplace=True)
        logger.info(f"Fetched {len(df)} rows for {ticker}")
        return df
    except Exception as e:
        logger.error(f"fetch_stock_data error for {ticker}: {e}")
        raise


# ─── Financial Statements ────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_financials(ticker: str) -> dict[str, pd.DataFrame]:
    """
    Return annual income statement, balance sheet, cash flow statement.
    Keys: 'income', 'balance', 'cashflow'
    """
    try:
        t = yf.Ticker(ticker)
        return {
            "income": t.financials,          # Annual income statement
            "balance": t.balance_sheet,       # Annual balance sheet
            "cashflow": t.cashflow,           # Annual cash flow
            "income_q": t.quarterly_financials,
            "balance_q": t.quarterly_balance_sheet,
            "cashflow_q": t.quarterly_cashflow,
        }
    except Exception as e:
        logger.error(f"fetch_financials error for {ticker}: {e}")
        return {}


# ─── News Headlines ──────────────────────────────────────────────────────────

@st.cache_data(ttl=600)
def fetch_news_headlines(ticker: str) -> list[dict]:
    """
    Return list of recent news items from multiple sources.
    """
    results = []
    
    # 1. Yahoo Finance
    try:
        t = yf.Ticker(ticker)
        news = t.news or []
        for item in news[:10]:
            results.append({
                "title": item.get("title", ""),
                "publisher": item.get("publisher", ""),
                "link": item.get("link", ""),
                "published": datetime.fromtimestamp(
                    item.get("providerPublishTime", 0)
                ).strftime("%Y-%m-%d %H:%M"),
                "source": "Yahoo"
            })
    except Exception as e:
        logger.error(f"Yahoo news error for {ticker}: {e}")

    # 2. Google News RSS (Fallback/Complement)
    clean_ticker = ticker.split('.')[0]
    try:
        gn_news = fetch_google_news_rss(f"{clean_ticker} stock news")
        for n in gn_news[:10]:
            n["source"] = "Google"
            results.append(n)
    except Exception as e:
        logger.error(f"Google news error: {e}")

    # 3. Market Specific (e.g. Mubasher for EGX)
    if ".CA" in ticker:
        try:
            mub_news = fetch_mubasher_news(clean_ticker)
            for n in mub_news:
                n["source"] = "Mubasher"
                results.append(n)
        except Exception as e:
            logger.error(f"Mubasher news error: {e}")

    # De-duplicate by title
    seen = set()
    unique_results = []
    for r in results:
        t_lower = r["title"].lower().strip()
        if t_lower not in seen:
            seen.add(t_lower)
            unique_results.append(r)
            
    # Sort by "published" if possible, but keep original order for relevance
    return unique_results[:30]


# ─── Global Market Data ──────────────────────────────────────────────────────

@st.cache_data(ttl=600)
def fetch_global_market_news() -> list[dict]:
    """
    Fetch and aggregate general market news from multiple global RSS feeds.
    """
    all_news = []
    for source, url in GLOBAL_NEWS_FEEDS.items():
        try:
            # We can reuse the fetch_google_news_rss logic or a generic one
            # For simplicity, let's use a generic RSS fetcher logic here
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if resp.status_code != 200:
                continue
            
            items = re.findall(r'<item>(.*?)</item>', resp.text, re.DOTALL)
            for item in items[:8]:
                title = re.search(r'<title>(.*?)</title>', item)
                link = re.search(r'<link>(.*?)</link>', item)
                pub_date = re.search(r'<pubDate>(.*?)</pubDate>', item)
                
                if title and link:
                    all_news.append({
                        "title": title.group(1).replace("<![CDATA[", "").replace("]]>", "").strip(),
                        "publisher": source,
                        "link": link.group(1).strip(),
                        "published": pub_date.group(1) if pub_date else "Recent",
                        "source": source
                    })
        except Exception as e:
            logger.error(f"Error fetching global news from {source}: {e}")
            
    # Sort by "published" if needed, or just return mixed
    return all_news


@st.cache_data(ttl=300)
def fetch_bond_data() -> dict[str, float]:
    """
    Fetch current yields for major bond indices.
    """
    bond_data = {}
    for name, ticker in BOND_TICKERS.items():
        try:
            t = yf.Ticker(ticker)
            # Yield indices are usually priced as 10x the actual yield (e.g. 42.50 = 4.25%)
            price = t.info.get("regularMarketPrice") or t.info.get("previousClose")
            if price:
                # Normalize: if it's > 10 it's likely a yield index like ^TNX
                bond_data[name] = price / 10.0 if price > 10 else price
            else:
                bond_data[name] = 0.0
        except Exception as e:
            logger.error(f"Error fetching bond data for {name}: {e}")
            bond_data[name] = 0.0
    return bond_data
