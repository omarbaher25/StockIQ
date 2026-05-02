"""
ui/theme.py — Custom CSS + dark glassmorphism theme injected into Streamlit
"""
import streamlit as st
from config import COLORS

def inject_theme():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {{
        --bg-dark:    {COLORS['bg_dark']};
        --bg-card:    {COLORS['bg_card']};
        --bg-card2:   {COLORS['bg_card2']};
        --blue:       {COLORS['accent_blue']};
        --gold:       {COLORS['accent_gold']};
        --green:      {COLORS['accent_green']};
        --red:        {COLORS['accent_red']};
        --purple:     {COLORS['accent_purple']};
        --text:       {COLORS['text_primary']};
        --text-muted: {COLORS['text_secondary']};
        --border:     {COLORS['border']};
    }}

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
        background-color: var(--bg-dark) !important;
        color: var(--text) !important;
    }}
    .stApp {{ background-color: var(--bg-dark) !important; }}

    /* ── Sidebar ─────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #0D1526 0%, #0A0E1A 100%) !important;
        border-right: 1px solid var(--border);
    }}
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label {{
        color: var(--text-muted) !important;
    }}

    /* ── Inputs ──────────────────────────────────────────────────── */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stTextArea textarea {{
        background: var(--bg-card2) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text) !important;
        font-family: 'Inter', sans-serif !important;
    }}
    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus {{
        border-color: var(--blue) !important;
        box-shadow: 0 0 0 2px rgba(59,130,246,0.25) !important;
    }}

    /* ── Buttons ─────────────────────────────────────────────────── */
    .stButton > button {{
        background: linear-gradient(135deg, var(--blue) 0%, #1D4ED8 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.3px !important;
        transition: all 0.25s ease !important;
        box-shadow: 0 4px 15px rgba(59,130,246,0.35) !important;
        width: 100%;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(59,130,246,0.50) !important;
    }}

    /* ── Tabs ────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {{
        background: var(--bg-card) !important;
        border-radius: 12px !important;
        padding: 4px !important;
        border: 1px solid var(--border);
        gap: 4px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent !important;
        color: var(--text-muted) !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.2rem !important;
        font-weight: 500 !important;
        border: none !important;
        transition: all 0.2s ease !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, var(--blue) 0%, #1D4ED8 100%) !important;
        color: white !important;
        box-shadow: 0 2px 10px rgba(59,130,246,0.4) !important;
    }}

    /* ── Metrics ─────────────────────────────────────────────────── */
    [data-testid="stMetricValue"] {{
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: var(--text) !important;
    }}
    [data-testid="stMetricDelta"] {{ font-size: 0.85rem !important; }}

    /* ── Expanders ───────────────────────────────────────────────── */
    .streamlit-expanderHeader {{
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text) !important;
        font-weight: 500 !important;
    }}
    .streamlit-expanderContent {{
        background: var(--bg-card2) !important;
        border: 1px solid var(--border) !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
    }}

    /* ── Scrollbar ───────────────────────────────────────────────── */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: var(--bg-dark); }}
    ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--blue); }}

    /* ── Custom Cards ────────────────────────────────────────────── */
    .glass-card {{
        background: rgba(17,24,39,0.85);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}
    .glass-card:hover {{
        border-color: rgba(59,130,246,0.4);
        box-shadow: 0 0 20px rgba(59,130,246,0.1);
    }}
    .metric-card {{
        background: linear-gradient(135deg, rgba(17,24,39,0.9) 0%, rgba(26,34,53,0.9) 100%);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        text-align: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .metric-card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 25px rgba(0,0,0,0.3); }}
    .metric-label {{ font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.3rem; }}
    .metric-value {{ font-size: 1.5rem; font-weight: 700; color: var(--text); }}
    .metric-sub   {{ font-size: 0.75rem; color: var(--text-muted); margin-top: 0.2rem; }}

    .score-badge {{
        display: inline-block;
        padding: 0.25rem 0.85rem;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }}
    .badge-green  {{ background: rgba(16,185,129,0.2); color: #10B981; border: 1px solid rgba(16,185,129,0.4); }}
    .badge-yellow {{ background: rgba(245,158,11,0.2); color: #F59E0B; border: 1px solid rgba(245,158,11,0.4); }}
    .badge-red    {{ background: rgba(239,68,68,0.2);  color: #EF4444; border: 1px solid rgba(239,68,68,0.4); }}
    .badge-purple {{ background: rgba(139,92,246,0.2); color: #8B5CF6; border: 1px solid rgba(139,92,246,0.4); }}
    .badge-blue   {{ background: rgba(59,130,246,0.2); color: #3B82F6; border: 1px solid rgba(59,130,246,0.4); }}

    .section-title {{
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: var(--text-muted);
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--border);
    }}
    .hero-ticker {{
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #fff 0%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.1;
    }}
    .hero-name {{
        font-size: 1.1rem;
        color: var(--text-muted);
        font-weight: 400;
        margin-top: 0.2rem;
    }}
    .divider {{
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--border), transparent);
        margin: 1.5rem 0;
    }}
    .stAlert {{ border-radius: 10px !important; }}
    div[data-testid="stHorizontalBlock"] > div {{ gap: 0.75rem; }}
    </style>
    """, unsafe_allow_html=True)
