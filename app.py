import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import time

# Page Configuration
st.set_page_config(layout="wide", page_title="Universal Real-Time NSE Trading Dashboard")

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# Initialize watchlist securely to prevent AttributeError or KeyError
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]
elif not isinstance(st.session_state.watchlist, list):
    st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]

# -----------------------------------------------------------------
# 1. HELPER FUNCTIONS & REAL-TIME DATA FETCH ENGINE
# -----------------------------------------------------------------
def get_oi_movement(oi_change, price_diff):
    if oi_change > 0 and price_diff > 0: return "Long Buildup (🟢)"
    elif oi_change > 0 and price_diff <= 0: return "Short Buildup (🔴)"
    elif oi_change <= 0 and price_diff <= 0: return "Profit Booking (🟡)"
    else: return "Short Covering (🟤)"

def calculate_pivots(H, L, C):
    P = (H + L + C) / 3
    return {
        "P (Pivot Point)": P,
        "R1 (Resistance 1)": (2 * P) - L,
        "S1 (Support 1)": (2 * P) - H,
        "R2 (Resistance 2)": P + (H - L),
        "S2 (Support 2)": P - (H - L),
        "R3 (Resistance 3)": H + 2 * (P - L),
        "S3 (Support 3)": L - 2 * (H - P)
    }

@st.cache_data(ttl=2)
def fetch_realtime_nse_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=5m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 429:
            raise Exception("Rate limited")
            
        result = response.json()['chart']['result'][0]
        indicators = result['indicators']['quote'][0]
        timestamps = result['timestamp']
        
        df = pd.DataFrame({
            'Open': indicators['open'],
            'High': indicators['high'],
            'Low': indicators['low'],
            'Close': indicators['close'],
            'Volume': indicators['volume']
        }, index=pd.to_datetime(timestamps, unit='s', utc=True).tz_convert('Asia/Kolkata'))
        df = df.dropna()
        if len(df) == 0:
            raise Exception("Empty Data")
        return df, "LIVE REAL-TIME FEED"
    except Exception as e:
        times = pd.date_range(start="09:15", end="15:30", freq="5min")
        df_backup = pd.DataFrame(index=times)
        base = {"TATASTEEL": 172.0, "HINDALCO": 655.0, "JSWSTEEL": 910.0, "VEDL": 452.0, "RELIANCE": 2450.0, "ITC": 282.20, "SBIN": 1006.20}.get(symbol, 500.0)
        df_backup['Open'] = base + np.random.uniform(-2, 2, len(times))
        df_backup['High'] = df_backup['Open'] + np.random.uniform(0, 4, len(times))
        df_backup['Low'] = df_backup['Open'] - np.random.uniform(0, 4, len(times))
        df_backup['Close'] = (df_backup['High'] + df_backup['Low']) / 2
        df_backup['Volume'] = np.random.randint(15000, 50000, len(times))
        return df_backup, "LIVE SIMULATION FEED"

# -----------------------------------------------------------------
# 2. SIDEBAR: SEARCH STOCKS & WATCHLIST SCANNER
# -----------------------------------------------------------------
st.sidebar.header("🔍 Universal Stock Search")

custom_ticker = st.sidebar.text_input("பங்கின் குறியீட்டு பெயர் (Ticker Symbol):", "").strip().upper()

if custom_ticker:
    if custom_ticker not in st.session_state.watchlist:
        if st.sidebar.button(f"➕ {custom_ticker} - ஐ வாட்ச்லிஸ்ட்டில் சேர்"):
            st.session_state.watchlist.append(custom_ticker)
            st.rerun()
    else:
        if st.sidebar.button(f"➖ {custom_ticker} - ஐ வாட்ச்லிஸ்ட்டில் இருந்து நீக்கு"):
            st.session_state.watchlist.remove(custom_ticker)
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🔥 Multi-Stock Live Scanner")
current_list = st.session_state.watchlist

if current_list:
    scanner_data = []
    for s in current_list:
        s_df, _ = fetch_realtime_nse_data(s)
        if len(s_df) >= 1:
            s_c915 = s_df.iloc[0]['Close']
            s_c930 = s_df.iloc[min(2, len(s_df)-1)]['Close']
            s_oi915 = int(s_df.iloc[0]['Volume'] * 0.42)
            s_oi930 = int(s_df.iloc[min(2, len(s_df)-1)]['Volume'] * 0.48)
            
            s_p_diff = s_c930 - s_c
