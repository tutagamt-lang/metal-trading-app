import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import time
import pyotp
from SmartApi import SmartConnect

# 1. Page Configuration for Pro Institutional Layout
st.set_page_config(
    layout="wide", 
    page_title="QUANTUM-X Live Trading Terminal",
    initial_sidebar_state="expanded"
)

# =================================================================
# ⚠️ உங்களுடைய ANGEL ONE விபரங்களை இங்கே மாற்றவும் ⚠️
# =================================================================
ANGEL_API_KEY = "YOUR_ANGEL_ONE_API_KEY"
ANGEL_CLIENT_CODE = "YOUR_CLIENT_ID"
ANGEL_MPIN = "YOUR_4_DIGIT_MPIN"
ANGEL_TOTP_KEY = "YOUR_TOTP_QR_SECRET_KEY"

# Angel One டோக்கன் மேப்
TOKEN_MAP = {
    "SBIN": {"token": "3045", "exchange": "NSE"},
    "RELIANCE": {"token": "2885", "exchange": "NSE"},
    "TATASTEEL": {"token": "3499", "exchange": "NSE"},
    "ITC": {"token": "1660", "exchange": "NSE"}
}

# பிரீமியம் CSS வடிவமைப்பு (இதனுள் புதிய Anti-Blur CSS இணைக்கப்பட்டுள்ளது)
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600&display=swap');
        * { font-family: 'Inter', sans-serif; }
        .block-container { padding-top: 2.2rem !important; padding-bottom: 0rem; padding-left: 1.5rem; padding-right: 1.5rem; }
        h2 { font-family: 'Inter', sans-serif; font-weight: 600; letter-spacing: -0.5px; margin-top: 5px !important; margin-bottom: 10px !important; }
        h4 { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #566275; margin-top: 15px; margin-bottom: 8px; }
        .mono-text { font-family: 'JetBrains Mono', monospace !important; }
        .pivot-table { width: 100%; border-collapse: collapse; font-size: 14px; background-color: #0b0c10; }
        .pivot-table td, .pivot-table th { border: 1px solid #1f2833; padding: 8px 12px; font-family: 'JetBrains Mono', monospace; }

        /* 🎯 இங்கிருந்து புதிய பகுதி: இதுதான் டேபிள்கள் மங்கலாவதைத் (Blur/Fade) தடுக்கும் */
        [data-testid="stDataFrameFade"], 
        [data-testid="stElementOverlay"] {
            opacity: 1 !important;
            filter: none !important;
            transition: none !important;
        }
    </style>
""", unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]

# -----------------------------------------------------------------
# ANGEL ONE ENGINE CONNECTION
# -----------------------------------------------------------------
@st.cache_resource
def get_angel_session():
    try:
        smartApi = SmartConnect(api_key=ANGEL_API_KEY)
        totp = pyotp.TOTP(ANGEL_TOTP_KEY).now()
        data = smartApi.generateSession(ANGEL_CLIENT_CODE, ANGEL_MPIN, totp)
        if data['status']:
            return smartApi
    except:
        return None
    return None

def fetch_angel_realtime_price(symbol):
    api = get_angel_session()
    if api and symbol in TOKEN_MAP:
        try:
            token = TOKEN_MAP[symbol]["token"]
            exch = TOKEN_MAP[symbol]["exchange"]
            ltp_data = api.ltpData(exch, f"{symbol}-EQ", token)
            if ltp_data['status']:
                return float(ltp_data['data']['ltp']), "ANGEL_LIVE (0-DELAY)"
        except:
            pass
            
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1m&range=1d"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3).json()
        return float(res['chart']['result'][0]['indicators']['quote'][0]['close'][-1]), "YAHOO_BACKUP"
    except:
        return 1000.0, "SIMULATED"

@st.cache_data(ttl=5)
def fetch_historical_pipeline(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1m&range=1d"
        result = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()['chart']['result'][0]
        indicators = result['indicators']['quote'][0]
        df = pd.DataFrame({
            'Open': indicators['open'], 'High': indicators['high'],
            'Low': indicators['low'], 'Close': indicators['close'], 'Volume': indicators['volume']
        }, index=pd.to_datetime(result['timestamp'], unit='s', utc=True).tz_convert('Asia/Kolkata'))
        return df.dropna()
    except:
        times = pd.date_range(start="09:15", end="15:30", freq="1min")
        df_b = pd.DataFrame(index=times)
        base = {"TATASTEEL": 197.80, "RELIANCE": 1293.0, "ITC": 285.10, "SBIN": 1017.15}.get(symbol, 500.0)
        df_b['Open'] = base + np.random.uniform(-0.5, 0.5, len(times))
        df_b['High'] = df_b['Open'] + np.random.uniform(0, 0.8, len(times))
        df_b['Low'] = df_b['Open'] - np.random.uniform(0, 0.8, len(times))
        df_b['Close'] = (df_b['High'] + df_b['Low']) / 2
        df_b['Volume'] = np.random.randint(15000, 50000, len(times))
        return df_b

def get_oi_movement(oi_change, price_diff):
    if oi_change > 0 and price_diff > 0: return "LONG BUILDUP"
    elif oi_change > 0 and price_diff <= 0: return "SHORT BUILDUP"
    elif oi_change <= 0 and price_diff <= 0: return "PROFIT BOOKING"
    else: return "SHORT COVERING"

def calculate_pivots(H, L, C):
    P = (H + L + C) / 3
    return {
        "R3 (Resistance 3)": H + 2 * (P - L), "R2 (Resistance 2)": P + (H - L), "R1 (Resistance 1)": (2 * P) - L,
        "P (Pivot Point)": P, "S1 (Support 1)": (2 * P) - H, "S2 (Support 2)": P - (H - L), "S3 (Support 3)": L - 2 * (H - P)
    }

# -----------------------------------------------------------------
# SIDEBAR TERMINAL
# -----------------------------------------------------------------
st.sidebar.markdown("### `📡 RADAR TERMINAL`")
custom_ticker = st.sidebar.text_input("ENTER TICKER SYMBOL:", "").strip().upper()

if custom_ticker and custom_ticker not in st.session_state.watchlist:
    if st.sidebar.button(f"[+] ADD {custom_ticker}", use_container_width=True):
        st.session_state.watchlist.append(custom_ticker)
        st.rerun()

selected_focus = st.sidebar.selectbox("⚡ ACTIVE INSTANCE:", options=st.session_state.watchlist)
ticker_clean = custom_ticker if custom_
