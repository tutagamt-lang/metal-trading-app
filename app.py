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
st.set_page_config(layout="wide", page_title="QUANTUM-X Live Trading Terminal")

# 🎯 LIGHT-MODE HIGH-CONTRAST TERMINAL STYLE
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600;700&display=swap');
        .stApp { background-color: #F8FAFC !important; color: #0F172A !important; }
        * { font-family: 'Inter', sans-serif; }
        .quant-table { width: 100%; border-collapse: collapse; font-size: 15px; background-color: #FFFFFF !important; margin-bottom: 15px; border: 2px solid #0F172A !important; }
        .quant-table th { background-color: #0F172A !important; color: #FFFFFF !important; padding: 12px 14px; font-family: 'JetBrains Mono', monospace; border: 2px solid #0F172A !important; }
        .quant-table td { border: 2px solid #E2E8F0 !important; padding: 12px 14px; font-family: 'JetBrains Mono', monospace; color: #0F172A !important; font-weight: 700 !important; }
        .matrix-box { background-color: #FFFFFF; padding: 22px; border-radius: 6px; border: 2px solid #0F172A; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
        .mono-text { font-family: 'JetBrains Mono', monospace !important; font-weight: 700 !important; }
    </style>
""", unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]

# DATA ENGINE
def get_oi_movement(oi_change, price_diff):
    if oi_change > 0 and price_diff > 0: return "LONG BUILDUP"
    elif oi_change > 0 and price_diff <= 0: return "SHORT BUILDUP"
    elif oi_change <= 0 and price_diff <= 0: return "PROFIT BOOKING"
    else: return "SHORT COVERING"

def calculate_pivots(H, L, C, O):
    P = (H + C + L + O) / 4
    R1 = (2 * P) - L
    S1 = (2 * P) - H
    return {
        "R3": H + 2 * (P - L),
        "R2": P + (R1 - S1),
        "R1": R1,
        "P": P,
        "S1": S1,
        "S2": P - (R1 - S1),
        "S3": L - 2 * (H - P)
    }

@st.cache_data(ttl=1)
def fetch_realtime_nse_data(symbol):
    try:
        yahoo_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?interval=1m&range=1d"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        result = response.json()['chart']['result'][0]
        indicators = result['indicators']['quote'][0]
        df = pd.DataFrame({
            'Open': indicators['open'], 'High': indicators['high'],
            'Low': indicators['low'], 'Close': indicators['close'],
            'Volume': indicators['volume']
        }, index=pd.to_datetime(result['timestamp'], unit='s', utc=True).tz_convert('Asia/Kolkata'))
        return df.dropna(), "LIVE"
    except:
        return pd.DataFrame(), "SIM"

# SIDEBAR
st.sidebar.markdown("### `📡 RADAR TERMINAL`")
custom_ticker = st.sidebar.text_input("ENTER TICKER SYMBOL:", "").strip().upper()
if custom_ticker and custom_ticker not in st.session_state.watchlist:
    if st.sidebar.button(f"[+] ADD {custom_ticker}", use_container_width=True):
        st.session_state.watchlist.append(custom_ticker)
        st.rerun()

ticker_clean = custom_ticker if custom_ticker else st.sidebar.selectbox("⚡ ACTIVE INSTANCE:", options=st.session_state.watchlist)

# MAIN DASHBOARD
df, _ = fetch_realtime_nse_data(ticker_clean)

if len(df) >= 1:
    # Calculations
    h_930, l_930 = df.iloc[0:15]['High'].max(), df.iloc[0:15]['Low'].min()
    live_price = df.iloc[-1]['Close']
    
    # Pivot Calculation (New Formula)
    levels = calculate_pivots(float(h_930), float(l_930), float(live_price), float(df.iloc[0]['Open']))
    
    # Correct Keys Access
    r1_val = levels["R1"]
    s1_val = levels["S1"]
    
    # Rest of the Dashboard UI...
    st.markdown(f"<h2>QUANTUM-X NSE TERMINAL // {ticker_clean}</h2>", unsafe_allow_html=True)
    
    # Logic Blocks (Same as your original)
    if live_price < s1_val:
        status_box, color_box = "💥 REAL BREAKDOWN", "#DC2626"
    elif live_price > r1_val:
        status_box, color_box = "🔥 REAL BREAKOUT", "#059669"
    else:
        status_box, color_box = "📡 CONSOLIDATION", "#2563EB"
        
    st.markdown(f"### {status_box}")
    
    # Pivot Table
    st.markdown("#### `🎯 ALIGNED BREAKOUT MATRIX ENGINE`")
    table_html = "<table class='quant-table'><thead><tr><th>PIVOT</th><th>VALUE</th></tr></thead><tbody>"
    for lvl, val in levels.items():
        table_html += f"<tr><td>{lvl}</td><td>₹ {val:.2f}</td></tr>"
    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)

time.sleep(2)
st.rerun()
