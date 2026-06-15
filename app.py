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

# 🎯 FULLY FIXED HIGH-CONTRAST CSS
st.markdown("""
    <style>
        /* Force White text across the app */
        .stApp, .stMarkdown, .stText, span, div, p, h1, h2, h3, b {
            color: #ffffff !important;
            font-family: 'Inter', sans-serif !important;
        }
        
        .block-container { padding-top: 2rem !important; }
        
        /* Tables Fix */
        .quant-table { width: 100%; border-collapse: collapse; font-size: 13px; background-color: #0d1117 !important; }
        .quant-table th { background-color: #161b22 !important; color: #ffffff !important; padding: 10px 12px; border: 1px solid #30363d !important; font-weight: 700 !important; }
        .quant-table td { border: 1px solid #30363d !important; padding: 10px 12px; color: #ffffff !important; font-weight: 600 !important; }
        
        /* Matrix Box Fix */
        .matrix-box { background-color: #0d1117; padding: 20px; border-radius: 6px; border: 1px solid #30363d; color: #ffffff !important; }
        
        /* Remove Fades */
        div[data-testid="stDataFrameFade"] { display: none !important; }
        .stStatusWidget { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# Session States
if "last_refresh" not in st.session_state: st.session_state.last_refresh = time.time()
if 'watchlist' not in st.session_state: st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]

# Data Functions
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
        yahoo_symbol = f"{symbol}.NS"
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
        # Fallback simulation
        times = pd.date_range(start="09:15", end="15:30", freq="1min")
        df_backup = pd.DataFrame(index=times)
        df_backup['Open'] = 500.0
        df_backup['High'] = 500.8
        df_backup['Low'] = 499.2
        df_backup['Close'] = 500.0
        df_backup['Volume'] = 20000
        return df_backup, "SIM"

# Sidebar
custom_ticker = st.sidebar.text_input("ENTER TICKER SYMBOL:", "").strip().upper()
if custom_ticker and custom_ticker not in st.session_state.watchlist:
    if st.sidebar.button("ADD TICKER"):
        st.session_state.watchlist.append(custom_ticker)
        st.rerun()

selected_focus = st.sidebar.selectbox("⚡ ACTIVE INSTANCE:", options=st.session_state.watchlist)
ticker_clean = custom_ticker if custom_ticker else selected_focus
df, _ = fetch_realtime_nse_data(ticker_clean)

# Main Dashboard
if not df.empty:
    live_price = df.iloc[-1]['Close']
    st.markdown(f"## QUANTUM-X TERMINAL // {ticker_clean}")
    
    # Header Info
    col1, col2 = st.columns(2)
    col1.metric("LIVE PRICE", f"₹ {live_price:.2f}")
    
    # Analysis
    h_930, l_930, c_930 = df['High'].max(), df['Low'].min(), df.iloc[-1]['Close']
    levels = calculate_pivots(h_930, l_930, c_930)
    
    st.markdown("### `🎯 BREAKOUT MATRIX`")
    status_box = "🔥 REAL BREAKOUT" if live_price > levels["R1 (Resistance 1)"] else "📡 NEUTRAL"
    
    st.markdown(f"""
    <div class="matrix-box">
        <strong>STATUS: {status_box}</strong><br>
        Current Price is trading at ₹ {live_price:.2f}
    </div>
    """, unsafe_allow_html=True)
    
    # Table
    st.markdown("### `📊 PIVOT LEVELS`")
    pivot_df = pd.DataFrame(list(levels.items()), columns=["LEVEL", "VALUE"])
    st.markdown(pivot_df.to_html(classes="quant-table", index=False), unsafe_allow_html=True)

    time.sleep(1)
    st.rerun()
