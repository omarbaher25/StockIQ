"""
analysis/metadata.py — Data context & metadata analysis layer
Identifies data sources, timeframes, keyword topics, and AI tool fingerprints.
"""
from __future__ import annotations
import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

AI_TOOL_PATTERNS = {
    "ChatGPT / GPT-4": [r"as an ai", r"i cannot", r"i'm unable to", r"language model", r"openai"],
    "Claude (Anthropic)": [r"i'm claude", r"anthropic", r"claude ai"],
    "Gemini (Google)": [r"i'm gemini", r"bard", r"google ai"],
    "Copilot (Microsoft)": [r"microsoft copilot", r"bing chat", r"copilot"],
    "Generic LLM": [r"as an? (ai|llm|chatbot|assistant)", r"training data", r"knowledge cutoff"],
}

FINANCIAL_TOPICS = {
    "Earnings": ["earnings", "eps", "profit", "loss", "revenue", "quarterly", "annual", "guidance"],
    "M&A": ["merger", "acquisition", "takeover", "buyout", "deal", "bid", "offer"],
    "Macro/Economy": ["inflation", "fed", "interest rate", "gdp", "recession", "economy", "unemployment"],
    "Regulation": ["sec", "regulatory", "compliance", "investigation", "lawsuit", "fine", "penalty"],
    "Innovation/Products": ["launch", "product", "innovation", "patent", "technology", "ai", "cloud"],
    "Leadership": ["ceo", "cfo", "executive", "resign", "appoint", "board", "director"],
    "Dividends": ["dividend", "payout", "yield", "buyback", "repurchase"],
    "Analyst Ratings": ["upgrade", "downgrade", "target", "analyst", "rating", "buy", "sell", "hold"],
    "Debt/Credit": ["debt", "bond", "credit", "rating", "default", "refinanc", "loan"],
    "ESG": ["esg", "sustainability", "carbon", "environmental", "governance", "climate"],
}

@dataclass
class MetadataReport:
    ticker: str
    data_sources: list = field(default_factory=list)
    timeframe_start: Optional[str] = None
    timeframe_end: Optional[str] = None
    timeframe_days: int = 0
    data_points: int = 0
    detected_topics: list = field(default_factory=list)
    top_keywords: list = field(default_factory=list)
    ai_tools_detected: list = field(default_factory=list)
    custom_text_word_count: int = 0
    custom_text_provided: bool = False
    analysis_timestamp: str = ""

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "data_sources": self.data_sources,
            "timeframe": f"{self.timeframe_start} → {self.timeframe_end}",
            "timeframe_days": self.timeframe_days,
            "data_points": self.data_points,
            "detected_topics": self.detected_topics,
            "top_keywords": self.top_keywords[:10],
            "ai_tools_detected": self.ai_tools_detected,
            "custom_text_provided": self.custom_text_provided,
            "custom_text_word_count": self.custom_text_word_count,
            "analysis_timestamp": self.analysis_timestamp,
        }


def _detect_ai_tools(text: str) -> list[str]:
    text_lower = text.lower()
    detected = []
    for tool, patterns in AI_TOOL_PATTERNS.items():
        if any(re.search(p, text_lower) for p in patterns):
            detected.append(tool)
    return detected


def _detect_topics(texts: list[str]) -> list[dict]:
    combined = " ".join(texts).lower()
    results = []
    for topic, keywords in FINANCIAL_TOPICS.items():
        hits = sum(combined.count(kw) for kw in keywords)
        if hits > 0:
            results.append({"topic": topic, "hits": hits})
    return sorted(results, key=lambda x: x["hits"], reverse=True)


def _extract_top_keywords(texts: list[str], top_n=15) -> list[dict]:
    stopwords = {
        "the","a","an","and","or","but","in","on","at","to","for","of","with","by","from",
        "is","are","was","were","be","been","have","has","had","will","would","could",
        "should","may","might","it","its","this","that","as","if","so","than","they",
        "we","our","their","said","says","also","s","new","year","quarter","company",
        "stock","market","shares","inc","corp","ltd","plc",
    }
    words = []
    for text in texts:
        tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
        words.extend(t for t in tokens if t not in stopwords)
    return [{"word": w, "count": c} for w, c in Counter(words).most_common(top_n)]


def run_metadata_analysis(
    ticker: str,
    df: Optional[pd.DataFrame] = None,
    headlines: Optional[list[dict]] = None,
    custom_text: str = "",
    info: Optional[dict] = None,
) -> MetadataReport:
    report = MetadataReport(ticker=ticker)
    report.analysis_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Data Sources ─────────────────────────────────────────────────────────
    sources = []
    if df is not None and not df.empty:
        sources.append("Yahoo Finance — OHLCV Historical Data (via yfinance)")
    if info:
        sources.append("Yahoo Finance — Company Fundamentals & Info (via yfinance)")
    if headlines:
        publishers = list({h.get("publisher", "") for h in headlines if h.get("publisher")})
        sources.append(f"Yahoo Finance News — {len(headlines)} articles ({', '.join(publishers[:3])}{'...' if len(publishers) > 3 else ''})")
    if custom_text:
        sources.append("User-Provided Custom Text Input")
    report.data_sources = sources

    # ── Timeframe ─────────────────────────────────────────────────────────────
    if df is not None and not df.empty:
        report.timeframe_start = str(df.index[0].date())
        report.timeframe_end = str(df.index[-1].date())
        report.timeframe_days = (df.index[-1] - df.index[0]).days
        report.data_points = len(df)

    # ── Topic Detection ───────────────────────────────────────────────────────
    all_texts = []
    if headlines:
        all_texts.extend(h.get("title", "") for h in headlines)
    if custom_text:
        all_texts.append(custom_text)
    if info and info.get("summary"):
        all_texts.append(info["summary"])

    report.detected_topics = _detect_topics(all_texts)
    report.top_keywords = _extract_top_keywords(all_texts)

    # ── AI Tool Detection ─────────────────────────────────────────────────────
    if custom_text:
        report.custom_text_provided = True
        report.custom_text_word_count = len(custom_text.split())
        report.ai_tools_detected = _detect_ai_tools(custom_text)

    logger.info(f"Metadata: {ticker} — {len(sources)} sources, {report.timeframe_days}d window, {len(report.detected_topics)} topics")
    return report
