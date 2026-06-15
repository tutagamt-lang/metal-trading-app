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
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600&display=swap');
        * { font-family: 'Inter', sans-serif; }
        .block-container { padding-top: 2rem !important; }
        h2 { font-family: 'Inter', sans-serif; font-weight: 600; color: #ffffff !important; }
        .mono-text { font-family: 'JetBrains Mono', monospace !important; }
        
        .quant-table { width: 100%; border-collapse: collapse; font-size: 13px; background-color: #0d1117 !important; }
        .quant-table th { background-color: #161b22 !important; color: #c9d1d9 !important; padding: 10px; border: 1px solid #30363d !important; font-size: 11px; }
        .quant-table td { border: 1px solid #30363d !important; padding: 10px; color: #ffffff !important; font-weight: 600 !important; }
        
        .matrix-box { background-color: #0d1117; padding: 20px; border-radius: 6px; border: 1px solid #30363d; line-height: 1.8; margin-bottom: 20px; }
        
        div[data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }
    </style>
""", unsafe_allow_html=True)

if "last_refresh" not in st.session_state: st.session_state.last_refresh = time.time()
if 'watchlist' not in st.session_state: st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]

# --- DATA ENGINE ---
def get_oi_movement(oi_change, price_diff):
    if oi_change > 0 and price_diff > 0: return "LONG BUILDUP"
    elif oi_change > 0 and price_diff <= 0: return "SHORT BUILDUP"
    elif oi_change <= 0 and price_diff <= 0: return "PROFIT BOOKING"
    else: return "SHORT COVERING"

def calculate_pivots(H, L, C):
    P = (H + L + C) / 3
    return {"R3": H + 2*(P-L), "R2": P+(H-L), "R1": (2*P)-L, "P": P, "S1": (2*P)-H, "S2": P-(H-L), "S3": L-2*(H-P)}

@st.cache_data(ttl=1)
def fetch_realtime_nse_data(symbol):
    try:
        yahoo_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?interval=1m&range=1d"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()
        data = res['chart']['result'][0]
        indicators = data['indicators']['quote'][0]
        df = pd.DataFrame(indicators, index=pd.to_datetime(data['timestamp'], unit='s', utc=True).tz_convert('Asia/Kolkata'))
        return df.dropna(), "LIVE"
    except:
        return pd.DataFrame(), "SIM"

# --- SIDEBAR ---
st.sidebar.markdown("### `📡 RADAR TERMINAL`")
custom_ticker = st.sidebar.text_input("ENTER TICKER SYMBOL:", "").strip().upper()
if custom_ticker and custom_ticker not in st.session_state.watchlist:
    if st.sidebar.button(f"[+] ADD {custom_ticker}"):
        st.session_state.watchlist.append(custom_ticker); st.rerun()

ticker_clean = custom_ticker if custom_ticker else st.sidebar.selectbox("⚡ ACTIVE INSTANCE:", options=st.session_state.watchlist)
df, _ = fetch_realtime_nse_data(ticker_clean)

# --- DASHBOARD ---
if len(df) >= 1:
    df['VWAP'] = ((df['high'] + df['low'] + df['close']) / 3 * df['volume']).cumsum() / df['volume'].cumsum()
    live_price = df.iloc[-1]['close']
    h_930, l_930, c_930 = df['high'].max(), df['low'].min(), df.iloc[-1]['close']
    levels = calculate_pivots(h_930, l_930, c_930)

    st.markdown(f"<h2>QUANTUM-X NSE TERMINAL // <span style='color:#00ff88;'>{ticker_clean}</span></h2>", unsafe_allow_html=True)
    
    st.markdown(f"<h1 style='color:#ffffff; font-size:40px;'>₹ {live_price:.2f}</h1>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### `🎯 BREAKOUT SCANNED MATRIX`")
        status_box = "📡 MARKET STATUS: ANALYZING"
        st.markdown(f"<div class='matrix-box'><p style='color:#ffffff !important;'>{status_box}</p></div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("### `📊 MARKET DEPTH`")
        st.markdown(f"<table class='quant-table'><tr><td>PRICE</td><td>₹ {live_price:.2f}</td></tr></table>", unsafe_allow_html=True)

    time.sleep(1)
    st.rerun()
else:
    st.error("தரவுகள் கிடைப்பதில் சிக்கல்... மீண்டும் இணைக்கப்படுகிறது.")
