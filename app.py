# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import streamlit.components.v1 as components
import time

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="QUANTUM-X Live Trading Terminal", initial_sidebar_state="expanded")

# 🎯 HIGH-CONTRAST ANTI-BLUR TERMINAL STYLE MATRIX
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght=400;700&family=Inter:wght=400;600&display=swap');
        * { font-family: 'Inter', sans-serif; }
        .block-container { padding-top: 2rem !important; padding-bottom: 0rem; padding-left: 1.5rem; padding-right: 1.5rem; }
        h2 { font-weight: 600; letter-spacing: -0.5px; margin-top: 5px !important; margin-bottom: 10px !important; }
        .mono-text { font-family: 'JetBrains Mono', monospace !important; }
        .quant-table { width: 100%; border-collapse: collapse; font-size: 13px; background-color: #0d1117 !important; margin-bottom: 15px; }
        .quant-table th { background-color: #161b22 !important; color: #c9d1d9 !important; text-align: left; padding: 10px 12px; font-family: 'JetBrains Mono', monospace; border: 1px solid #30363d !important; font-size: 11px; letter-spacing: 0.5px; font-weight: 700 !important; }
        .quant-table td { border: 1px solid #30363d !important; padding: 10px 12px; font-family: 'JetBrains Mono', monospace; color: #ffffff !important; font-weight: 600 !important; }
    </style>
""", unsafe_allow_html=True)

if "last_refresh" not in st.session_state: st.session_state.last_refresh = time.time()
if 'watchlist' not in st.session_state: st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]

# --- DATA ENGINE PIPELINE ---
def get_oi_movement(oi_change, price_diff):
    if oi_change > 0 and price_diff > 0: return "LONG BUILDUP"
    elif oi_change > 0 and price_diff <= 0: return "SHORT BUILDUP"
    elif oi_change <= 0 and price_diff <= 0: return "PROFIT BOOKING"
    else: return "SHORT COVERING"

def calculate_pivots(H, L, C):
    P = (H + L + C) / 3
    return {
        "R3 (Resistance 3)": H + 2 * (P - L),
        "R2 (Resistance 2)": P + (H - L),
        "R1 (Resistance 1)": (2 * P) - L,
        "P (Pivot Point)": P,
        "S1 (Support 1)": (2 * P) - H,
        "S2 (Support 2)": P - (H - L),
        "S3 (Support 3)": L - 2 * (H - P)
    }

@st.cache_data(ttl=1)
def fetch_realtime_nse_data(symbol):
    try:
        yahoo_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?interval=1m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        result = response.json()['chart']['result'][0]
        indicators = result['indicators']['quote'][0]
        timestamps = result['timestamp']
        df = pd.DataFrame({
            'Open': indicators['open'], 'High': indicators['high'],
            'Low': indicators['low'], 'Close': indicators['close'],
            'Volume': indicators['volume']
        }, index=pd.to_datetime(timestamps, unit='s', utc=True).tz_convert('Asia/Kolkata'))
        return df.dropna(), "LIVE"
    except:
        times = pd.date_range(start="09:15", end="15:30", freq="1min")
        df_backup = pd.DataFrame(index=times)
        base = {"TATASTEEL": 197.80, "RELIANCE": 1293.0, "ITC": 285.10, "SBIN": 1017.15}.get(symbol, 500.0)
        df_backup['Open'] = base + np.random.uniform(-0.5, 0.5, len(times))
        df_backup['High'] = df_backup['Open'] + np.random.uniform(0, 0.8, len(times))
        df_backup['Low'] = df_backup['Open'] - np.random.uniform(0, 0.8, len(times))
        df_backup['Close'] = (df_backup['High'] + df_backup['Low']) / 2
        df_backup['Volume'] = np.random.randint(15000, 50000, len(times))
        return df_backup, "SIM"

# --- SIDEBAR TERMINAL ---
st.sidebar.markdown("### `📡 RADAR TERMINAL`")
custom_ticker = st.sidebar.text_input("ENTER TICKER SYMBOL:", "").strip().upper()
if custom_ticker and custom_ticker not in st.session_state.watchlist:
    if st.sidebar.button(f"[+] ADD {custom_ticker}", use_container_width=True):
        st.session_state.watchlist.append(custom_ticker)
        st.rerun()

selected_focus = st.sidebar.selectbox("⚡ ACTIVE INSTANCE:", options=st.session_state.watchlist)
ticker_clean = custom_ticker if custom_ticker else selected_focus

# --- DASHBOARD ---
df, data_status = fetch_realtime_nse_data(ticker_clean)
if len(df) >= 1:
    # Math Core
    df['VWAP'] = ((df['High'] + df['Low'] + df['Close']) / 3 * df['Volume']).cumsum() / df['Volume'].cumsum()
    current_vwap = df.iloc[-1]['VWAP']
    df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
    live_price = df.iloc[-1]['Close']
    levels = calculate_pivots(float(df['High'].max()), float(df['Low'].min()), float(df.iloc[0]['Close']))
    
    st.markdown(f"<h2>QUANTUM-X NSE TERMINAL // <span style='color:#00ff88;'>{ticker_clean}</span></h2>", unsafe_allow_html=True)
    
    # UI Display (Layout implemented here)
    st.write(f"Live Price: {live_price:.2f}") # உங்கள் முழுமையான UI லாஜிக்கை இங்கே இணைக்கவும்.
    
    time.sleep(1)
    st.rerun()
