"""
config.py — Global configuration, constants, and thresholds
"""

# ─── Exchange suffix map ────────────────────────────────────────────────────
EXCHANGE_SUFFIXES = {
    "NYSE / NASDAQ (US)": "",
    "London Stock Exchange (UK)": ".L",
    "Toronto Stock Exchange (CA)": ".TO",
    "Australian Securities Exchange": ".AX",
    "Frankfurt (DE)": ".DE",
    "Paris (FR)": ".PA",
    "Tokyo (JP)": ".T",
    "Hong Kong": ".HK",
    "Shanghai (CN)": ".SS",
    "Bombay Stock Exchange (IN)": ".BO",
    "National Stock Exchange (IN)": ".NS",
    "Euronext Amsterdam": ".AS",
    "Madrid (ES)": ".MC",
    "Swiss Exchange": ".SW",
    "Korea Exchange": ".KS",
    "Egyptian Exchange (EG)": ".CA",
}

# ─── Data fetch defaults ────────────────────────────────────────────────────
DEFAULT_PERIOD = "1y"
DEFAULT_INTERVAL = "1d"
CACHE_TTL_SECONDS = 300  # 5-minute cache

# ─── Technical analysis parameters ─────────────────────────────────────────
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BB_PERIOD = 20
BB_STD = 2
ATR_PERIOD = 14
SMA_SHORT = 20
SMA_MED = 50
SMA_LONG = 200
VOLUME_ZSCORE_WINDOW = 20

# ─── Fundamental scoring thresholds ────────────────────────────────────────
PE_FAIR_LOW = 10
PE_FAIR_HIGH = 25
DEBT_EQUITY_SAFE = 1.0
CURRENT_RATIO_SAFE = 1.5
GROSS_MARGIN_GOOD = 0.40

# ─── Manipulation detection weights ─────────────────────────────────────────
MANIPULATION_WEIGHTS = {
    "abnormal_volume": 25,
    "price_spike_no_news": 20,
    "wash_trade_pattern": 15,
    "pump_dump_shape": 20,
    "isolation_forest_cluster": 20,
}
MANIPULATION_THRESHOLDS = {
    "LOW": (0, 25),
    "MEDIUM": (25, 50),
    "HIGH": (50, 75),
    "CRITICAL": (75, 100),
}
VOLUME_SPIKE_ZSCORE = 3.0
PRICE_SPIKE_PCT = 0.08  # 8% single-day move

# ─── Valuation Assumptions ───────────────────────────────────────────────────
MARKET_RISK_PREMIUM = 0.055  # 5.5% average
DEFAULT_TAX_RATE = 0.21      # 21% default if not found
DEFAULT_GROWTH_RATE = 0.03    # 3% terminal growth for DCF

# ─── UI colors ───────────────────────────────────────────────────────────────
COLORS = {
    "bg_dark": "#0A0E1A",
    "bg_card": "#111827",
    "bg_card2": "#1A2235",
    "accent_blue": "#3B82F6",
    "accent_gold": "#F59E0B",
    "accent_green": "#10B981",
    "accent_red": "#EF4444",
    "accent_purple": "#8B5CF6",
    "text_primary": "#F1F5F9",
    "text_secondary": "#94A3B8",
    "border": "#1E2D42",
    "gradient_start": "#1E3A5F",
    "gradient_end": "#0A0E1A",
}

RISK_COLORS = {
    "LOW": "#10B981",
    "MEDIUM": "#F59E0B",
    "HIGH": "#EF4444",
    "CRITICAL": "#8B5CF6",
}

# ─── Global Market Feeds ─────────────────────────────────────────────────────
GLOBAL_NEWS_FEEDS = {
    "MarketWatch": "https://www.marketwatch.com/rss/topstories",
    "CNBC Investing": "https://www.cnbc.com/id/15839069/device/rss/rss.html",
    "Reuters Business": "http://feeds.reuters.com/reuters/businessNews",
    "Investing.com": "https://www.investing.com/rss/news.rss",
    "Seeking Alpha": "https://seekingalpha.com/feed/stock-market-news",
}

BOND_TICKERS = {
    "US 10Y": "^TNX",
    "US 30Y": "^TYX",
    "US 5Y": "^FVX",
    "US 13W": "^IRX",
    "UK 10Y": "0P00007P73.L", # Proxy for Gilt 10Y
    "Egypt 3M": "EGX30",      # Macro proxy
}
