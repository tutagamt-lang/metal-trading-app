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

# Page Config
st.set_page_config(layout="wide", page_title="QUANTUM-X Terminal")

# --- DATA ENGINE ---
def calculate_pivots(H, L, C):
    P = (H + L + C) / 3
    return {
        "R1": (2 * P) - L,
        "P": P,
        "S1": (2 * P) - H
    }

@st.cache_data(ttl=1)
def fetch_realtime_nse_data(symbol):
    # ... (உங்கள் பழைய fetch logic அப்படியே இருக்கட்டும்) ...
    pass 

# --- MAIN LOGIC ---
ticker_clean = st.sidebar.text_input("ENTER TICKER:", "RELIANCE").upper()
df, data_status = fetch_realtime_nse_data(ticker_clean)

if not df.empty:
    live_price = df.iloc[-1]['Close']
    # பிழை ஏற்படாமல் இருக்க pivots-ஐ முதலில் கணக்கிடவும்
    pivots = calculate_pivots(df['High'].max(), df['Low'].min(), df.iloc[-1]['Close'])
    r1_val = pivots["R1"]
    s1_val = pivots["S1"]
    
    is_near_resistance = abs(live_price - r1_val) <= (live_price * 0.006)
    is_near_support = abs(live_price - s1_val) <= (live_price * 0.006)
    
    # தமிழ் விளக்கங்களைத் தனி வேரியபிள்களாகப் பிரிக்கவும் (f-string பிழை வராது)
    if live_price < s1_val:
        status_box = "💥 REAL BREAKDOWN"
        color_box = "#ff2a5f"
        tamil_desc = "விலை முக்கிய சப்போர்ட் எல்லையை உடைத்து கீழே இறங்கிவிட்டது."
        trade_action = "⚡ SELL ACTION: Short பொசிஷன் எடுக்கலாம்!"
    elif live_price > r1_val:
        status_box = "🔥 REAL BREAKOUT"
        color_box = "#00ff88"
        tamil_desc = "விலை முக்கிய ரெசிஸ்டன்ஸ் எல்லையை உடைத்து மேலே ஏறியுள்ளது."
        trade_action = "⚡ BUY ACTION: Long பொசிஷன் எடுக்கலாம்!"
    else:
        status_box = "📡 CONSOLIDATION"
        color_box = "#00b0ff"
        tamil_desc = "விலை தற்போதைக்கு நடுநிலையாக உள்ளது."
        trade_action = "⏳ WAIT: காத்திருக்கவும்."

    # UI Display
    st.markdown(f"""
    <div style="border-left: 6px solid {color_box}; padding: 20px; background: #0d1117;">
        <h3 style="color: {color_box};">{status_box}</h3>
        <p style="color: #ffffff;">{tamil_desc}</p>
        <div style="background: #161b22; padding: 10px; color: {color_box}; font-weight: bold;">
            {trade_action}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    time.sleep(1)
    st.rerun()
