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
        .block-container { padding-top: 2rem !important; padding-bottom: 0rem; padding-left: 1.5rem; padding-right: 1.5rem; }
        h2 { font-weight: 600; letter-spacing: -0.5px; margin-top: 5px !important; margin-bottom: 10px !important; }
        .mono-text { font-family: 'JetBrains Mono', monospace !important; }
        .quant-table { width: 100%; border-collapse: collapse; font-size: 13px; background-color: #0d1117 !important; margin-bottom: 15px; }
        .quant-table th { background-color: #161b22 !important; color: #c9d1d9 !important; text-align: left; padding: 10px 12px; font-family: 'JetBrains Mono', monospace; border: 1px solid #30363d !important; font-size: 11px; letter-spacing: 0.5px; font-weight: 700 !important; }
        .quant-table td { border: 1px solid #30363d !important; padding: 10px 12px; font-family: 'JetBrains Mono', monospace; color: #ffffff !important; font-weight: 600 !important; }
        div[data-testid="stDataFrameFade"], [data-testid="stElementOverlay"] { opacity: 1 !important; filter: none !important; transition: none !important; display: none !important; visibility: hidden !important; }
    </style>
""", unsafe_allow_html=True)

if "last_refresh" not in st.session_state: st.session_state.last_refresh = time.time()
if 'watchlist' not in st.session_state: st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]

def get_oi_movement(oi_change, price_diff):
    if oi_change > 0 and price_diff > 0: return "LONG BUILDUP"
    elif oi_change > 0 and price_diff <= 0: return "SHORT BUILDUP"
    elif oi_change <= 0 and price_diff <= 0: return "PROFIT BOOKING"
    else: return "SHORT COVERING"

def calculate_pivots(H, L, C):
    P = (H + L + C) / 3
    return {"R3 (Resistance 3)": H + 2*(P-L), "R2 (Resistance 2)": P+(H-L), "R1 (Resistance 1)": (2*P)-L, "P (Pivot Point)": P, "S1 (Support 1)": (2*P)-H, "S2 (Support 2)": P-(H-L), "S3 (Support 3)": L-2*(H-P)}

@st.cache_data(ttl=1)
def fetch_realtime_nse_data(symbol):
    try:
        yahoo_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?interval=1m&range=1d"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        res_data = res.json()['chart']['result'][0]
        quote = res_data['indicators']['quote'][0]
        df = pd.DataFrame({'Open': quote['open'], 'High': quote['high'], 'Low': quote['low'], 'Close': quote['close'], 'Volume': quote['volume']}, index=pd.to_datetime(res_data['timestamp'], unit='s', utc=True).tz_convert('Asia/Kolkata'))
        return df.dropna(), "LIVE"
    except:
        return pd.DataFrame(), "SIM"

# SIDEBAR
ticker_input = st.sidebar.text_input("ENTER TICKER SYMBOL:", "").strip().upper()
if ticker_input and ticker_input not in st.session_state.watchlist:
    if st.sidebar.button(f"[+] ADD {ticker_input}"):
        st.session_state.watchlist.append(ticker_input)
        st.rerun()

ticker_clean = ticker_input if ticker_input else st.sidebar.selectbox("⚡ ACTIVE INSTANCE:", st.session_state.watchlist)
df, data_status = fetch_realtime_nse_data(ticker_clean)

# MAIN TERMINAL
if len(df) >= 1:
    live_price = df.iloc[-1]['Close']
    st.markdown(f"<h2>QUANTUM-X NSE TERMINAL // <span style='color:#00ff88;'>{ticker_clean}</span></h2>", unsafe_allow_html=True)
    
    # Logic setup
    H, L = df['High'].max(), df['Low'].min()
    levels = calculate_pivots(H, L, live_price)
    r1_val, s1_val = levels["R1 (Resistance 1)"], levels["S1 (Support 1)"]
    
    # Status Variables (Tamil Content)
    if live_price < s1_val:
        status, color, desc = "💥 REAL BREAKDOWN", "#ff2a5f", "விலை முக்கிய சப்போர்ட் எல்லையை உடைத்து கீழே இறங்கிவிட்டது."
        action = "⚡ SELL ACTION: Short பொசிஷன் எடுக்கலாம்!"
    elif live_price > r1_val:
        status, color, desc = "🔥 REAL BREAKOUT", "#00ff88", "விலை முக்கிய ரெசிஸ்டன்ஸ் எல்லையை உடைத்து மேலே ஏறியுள்ளது."
        action = "⚡ BUY ACTION: Long பொசிஷன் எடுக்கலாம்!"
    else:
        status, color, desc = "📡 CONSOLIDATION", "#00b0ff", "சந்தையில் பெரிய மாற்றம் இல்லை, காத்திருக்கவும்."
        action = "⏳ WAIT: பொறுமையாக இருக்கவும்."

    # UI Render
    st.markdown(f"""
    <div style="border-left: 6px solid {color}; background: #0d1117; padding: 20px; border-radius: 5px;">
        <h3 style="color: {color}; margin:0;">{status}</h3>
        <p style="color: #ffffff; font-size: 16px;">📊 {desc}</p>
        <div style="background: #161b22; padding: 12px; color: {color}; font-weight: bold; border-radius: 4px;">
            {action}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    time.sleep(1)
    st.rerun()
else:
    st.error("Engine pipeline error. Retrying connection...")
