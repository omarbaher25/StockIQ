"""
analysis/sentiment.py — News headline sentiment analysis using VADER
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from collections import Counter
import re
from typing import Optional

logger = logging.getLogger(__name__)

FINANCIAL_STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with","by","from",
    "is","are","was","were","be","been","being","have","has","had","do","does","did",
    "will","would","could","should","may","might","shall","its","it","this","that",
    "these","those","as","if","so","than","then","their","they","we","our","your","my",
    "s","said","says","according","also","million","billion","percent","share","shares",
    "stock","market","company","quarter","year","annual","fiscal","report","reported",
    "inc","corp","ltd","llc","plc","co",
}

@dataclass
class SentimentReport:
    ticker: str
    overall_sentiment: str = "NEUTRAL"   # BULLISH | BEARISH | NEUTRAL
    compound_score: float = 0.0          # -1 to +1
    positive_pct: float = 0.0
    negative_pct: float = 0.0
    neutral_pct: float = 0.0
    article_count: int = 0
    top_keywords: list = field(default_factory=list)
    headline_results: list = field(default_factory=list)
    custom_text_score: Optional[float] = None

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "overall_sentiment": self.overall_sentiment,
            "compound_score": round(self.compound_score, 4),
            "positive_pct": round(self.positive_pct, 3),
            "negative_pct": round(self.negative_pct, 3),
            "neutral_pct": round(self.neutral_pct, 3),
            "article_count": self.article_count,
            "top_keywords": self.top_keywords[:10],
        }


def _extract_keywords(texts: list[str], top_n: int = 15) -> list[tuple[str, int]]:
    words = []
    for text in texts:
        tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
        words.extend(t for t in tokens if t not in FINANCIAL_STOPWORDS)
    return Counter(words).most_common(top_n)


def run_sentiment_analysis(
    ticker: str,
    headlines: list[dict],
    custom_text: str = "",
) -> SentimentReport:
    report = SentimentReport(ticker=ticker)

    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
    except ImportError:
        logger.warning("vaderSentiment not installed. Skipping sentiment analysis.")
        report.overall_sentiment = "NEUTRAL"
        report.compound_score = 0.0
        return report

    scores = []
    results = []
    texts_for_keywords = []

    for item in headlines:
        title = item.get("title", "")
        if not title:
            continue
        s = sia.polarity_scores(title)
        scores.append(s["compound"])
        texts_for_keywords.append(title)
        label = "POSITIVE" if s["compound"] >= 0.05 else "NEGATIVE" if s["compound"] <= -0.05 else "NEUTRAL"
        results.append({
            "title": title,
            "publisher": item.get("publisher", ""),
            "published": item.get("published", ""),
            "compound": round(s["compound"], 4),
            "label": label,
        })

    if custom_text:
        cs = sia.polarity_scores(custom_text)
        report.custom_text_score = round(cs["compound"], 4)
        scores.append(cs["compound"])
        texts_for_keywords.append(custom_text)

    report.headline_results = results
    report.article_count = len(results)

    if scores:
        avg = sum(scores) / len(scores)
        report.compound_score = round(avg, 4)
        positives = sum(1 for s in scores if s >= 0.05)
        negatives = sum(1 for s in scores if s <= -0.05)
        neutrals  = len(scores) - positives - negatives
        n = len(scores)
        report.positive_pct = positives / n
        report.negative_pct = negatives / n
        report.neutral_pct  = neutrals  / n

        if avg >= 0.15:   report.overall_sentiment = "BULLISH"
        elif avg <= -0.15: report.overall_sentiment = "BEARISH"
        else:              report.overall_sentiment = "NEUTRAL"
    else:
        report.overall_sentiment = "NEUTRAL"

    report.top_keywords = [
        {"word": w, "count": c} for w, c in _extract_keywords(texts_for_keywords)
    ]

    logger.info(f"Sentiment: {ticker} → {report.overall_sentiment} (score={report.compound_score})")
    return report
