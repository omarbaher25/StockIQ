"""
data/web_scraper.py — Supplementary market-specific web scrapers
Uses requests and regex to extract data from financial sites.
"""
from __future__ import annotations
import re
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

def fetch_mubasher_news(ticker: str) -> list[dict]:
    """
    Scrape recent news from Mubasher.info for Egyptian/MENA tickers.
    Ticker should be clean (e.g. 'COMI' not 'COMI.CA')
    """
    clean_ticker = ticker.split('.')[0].upper()
    url = f"https://www.mubasher.info/markets/EGX/stocks/{clean_ticker}/news"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        
        # Simple regex to find news titles and links
        # This is a placeholder for actual structural parsing
        # Mubasher uses <a> tags with specific classes or structures
        titles = re.findall(r'<a[^>]*class="[^"]*news-item__title[^"]*"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
        links = re.findall(r'<a[^>]*class="[^"]*news-item__title[^"]*"[^>]*href="([^"]*)"', resp.text)
        
        results = []
        for t, l in zip(titles[:10], links[:10]):
            results.append({
                "title": re.sub(r'<.*?>', '', t).strip(),
                "publisher": "Mubasher Egypt",
                "link": f"https://www.mubasher.info{l}" if l.startswith('/') else l,
                "published": "Recent"
            })
        return results
    except Exception as e:
        logger.error(f"fetch_mubasher_news error: {e}")
        return []

def fetch_google_news_rss(query: str) -> list[dict]:
    """
    Fetch news from Google News RSS.
    """
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        
        # Regex for RSS <item> tags
        items = re.findall(r'<item>(.*?)</item>', resp.text, re.DOTALL)
        results = []
        for item in items[:15]:
            title = re.search(r'<title>(.*?)</title>', item)
            link = re.search(r'<link>(.*?)</link>', item)
            pub_date = re.search(r'<pubDate>(.*?)</pubDate>', item)
            source = re.search(r'<source[^>]*>(.*?)</source>', item)
            
            if title and link:
                results.append({
                    "title": title.group(1).replace("<![CDATA[", "").replace("]]>", ""),
                    "publisher": source.group(1) if source else "Google News",
                    "link": link.group(1),
                    "published": pub_date.group(1) if pub_date else ""
                })
        return results
    except Exception as e:
        logger.error(f"fetch_google_news_rss error: {e}")
        return []

def get_market_hub_links(ticker: str, exchange: str) -> list[dict]:
    """
    Returns a list of deep links for external research based on the exchange.
    """
    clean_ticker = ticker.split('.')[0].upper()
    links = [
        {"name": "TradingView", "url": f"https://www.tradingview.com/symbols/{ticker}/", "color": "#2962FF"},
        {"name": "Investing.com", "url": f"https://www.investing.com/search/?q={clean_ticker}", "color": "#191919"},
    ]
    
    # Global/Universal Links
    links.append({"name": "MarketCap Rank", "url": f"https://companiesmarketcap.com/?s={clean_ticker}", "color": "#10B981"})

    if ".CA" in ticker or "EGX" in exchange:
        links.extend([
            {"name": "Mubasher EG", "url": f"https://www.mubasher.info/markets/EGX/stocks/{clean_ticker}", "color": "#007BFF"},
            {"name": "EGX Official", "url": f"https://www.egx.com.eg/en/HomePage.aspx", "color": "#1E2D42"},
            {"name": "Enterprise Egypt", "url": f"https://enterprise.press/search/?q={clean_ticker}", "color": "#8B5CF6"},
            {"name": "EGX Stats", "url": f"https://www.egx.com.eg/en/companystatistics.aspx?symbol={clean_ticker}", "color": "#10B981"},
        ])
    elif ".NS" in ticker or ".BO" in ticker or "NSE" in exchange or "BSE" in exchange:
        links.extend([
            {"name": "NSE India", "url": f"https://www.nseindia.com/get-quotes/equity?symbol={clean_ticker}", "color": "#003399"},
            {"name": "StockAnalysis IN", "url": f"https://stockanalysis.com/list/nse-india/", "color": "#2563EB"},
            {"name": "MoneyControl", "url": f"https://www.moneycontrol.com/india/stockpricequote/{clean_ticker}", "color": "#D32F2F"},
            {"name": "Screener.in", "url": f"https://www.screener.in/company/{clean_ticker}/", "color": "#10B981"},
        ])
    elif ".L" in ticker:
        links.extend([
            {"name": "LSE News", "url": f"https://www.londonstockexchange.com/stock/{clean_ticker}/company-page", "color": "#001E62"},
            {"name": "Investegate", "url": f"https://www.investegate.co.uk/search.aspx?q={clean_ticker}", "color": "#D32F2F"},
        ])
    else:
        links.extend([
            {"name": "MarketWatch", "url": f"https://www.marketwatch.com/investing/stock/{clean_ticker}", "color": "#D32F2F"},
            {"name": "Seeking Alpha", "url": f"https://seekingalpha.com/symbol/{clean_ticker}", "color": "#FFAB00"},
            {"name": "Finviz", "url": f"https://finviz.com/quote.ashx?t={clean_ticker}", "color": "#10B981"},
        ])
        
    return links
