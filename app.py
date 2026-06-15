# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="QUANTUM-X Terminal")

# 2. CSS - எழுத்துக்களை தெளிவாக மாற்ற
st.markdown("""
    <style>
        .matrix-box { background-color: #0d1117; padding: 20px; border-radius: 6px; border: 1px solid #30363d; margin-bottom: 20px; }
        .text-white { color: #ffffff !important; }
        .action-box { background-color: #161b22; padding: 15px; border-radius: 4px; border: 1px solid #30363d; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# 3. Data Fetching
@st.cache_data(ttl=1)
def fetch_realtime_nse_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        result = response.json()['chart']['result'][0]
        indicators = result['indicators']['quote'][0]
        df = pd.DataFrame({'Close': indicators['close'], 'High': indicators['high'], 'Low': indicators['low']})
        return df.dropna()
    except:
        return pd.DataFrame()

# 4. Sidebar Ticker
ticker = st.sidebar.text_input("ENTER TICKER:", "RELIANCE").upper()
df = fetch_realtime_nse_data(ticker)

# 5. Main Logic & Display
if not df.empty:
    live_price = df.iloc[-1]['Close']
    H = df['High'].max()
    L = df['Low'].min()
    C = live_price
    P = (H + L + C) / 3
    r1_val = (2 * P) - L
    s1_val = (2 * P) - H
    
    # Logic setup
    if live_price < s1_val:
        status = "💥 REAL BREAKDOWN"
        color = "#ff2a5f"
        desc = "விலை முக்கிய சப்போர்ட் எல்லையை உடைத்து கீழே இறங்கிவிட்டது."
        action = "⚡ SELL ACTION: Short பொசிஷன் எடுக்கலாம்!"
    elif live_price > r1_val:
        status = "🔥 REAL BREAKOUT"
        color = "#00ff88"
        desc = "விலை முக்கிய ரெசிஸ்டன்ஸ் எல்லையை உடைத்து மேலே ஏறியுள்ளது."
        action = "⚡ BUY ACTION: Long பொசிஷன் எடுக்கலாம்!"
    else:
        status = "📡 CONSOLIDATION"
        color = "#00b0ff"
        desc = "சந்தையில் பெரிய மாற்றம் இல்லை, காத்திருக்கவும்."
        action = "⏳ WAIT: பொறுமையாக இருக்கவும்."

    # Final Display
    st.markdown(f"""
    <div class="matrix-box" style="border-left: 6px solid {color};">
        <h3 style="color: {color}; margin-top: 0;">{status}</h3>
        <p class="text-white">📊 {desc}</p>
        <div class="action-box" style="color: {color}; font-weight: bold;">
            {action}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    time.sleep(1)
    st.rerun()
else:
    st.error("தரவு கிடைக்கவில்லை. தயவுசெய்து Ticker-ஐச் சரிபார்க்கவும்.")
