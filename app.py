import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import time
from datetime import datetime
from SmartApi import SmartConnect
import pyotp

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="QUANTUM-X Live Trading Terminal", initial_sidebar_state="expanded")

# 🎯 CSS Styles
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF !important; color: #0F172A !important; }
        .quant-table { width: 100%; border-collapse: collapse; border: 2px solid #0F172A !important; }
        .quant-table th { background-color: #0F172A !important; color: #FFFFFF !important; padding: 12px; }
        .quant-table td { border: 2px solid #E2E8F0 !important; padding: 12px; }
    </style>
""", unsafe_allow_html=True)

# Credentials
API_KEY = "rpg4LX8F"
CLIENT_CODE = "AACG314572"
PASSWORD = "6227"
TOTP_KEY = "Z5MZBUBZAHYJFNKEYHWIJP4HWA"

if "angel_conn" not in st.session_state:
    st.session_state.angel_conn = None

def init_angel_one():
    if st.session_state.angel_conn is not None:
        return st.session_state.angel_conn
    try:
        smart_conn = SmartConnect(api_key=API_KEY.strip())
        totp = pyotp.TOTP(TOTP_KEY.strip()).now()
        data = smart_conn.generateSession(CLIENT_CODE.strip(), PASSWORD.strip(), totp)
        if data and data.get('status'):
            st.session_state.angel_conn = smart_conn
            return smart_conn
    except Exception as e:
        st.error(f"Login Failed: {str(e)}")
    return None

TOKEN_MAP = {
    "TATASTEEL": {"token": "3499", "exch": "NSE", "fut_token": "43521"},
    "RELIANCE": {"token": "2885", "exch": "NSE", "fut_token": "35012"},
    "ITC": {"token": "1660", "exch": "NSE", "fut_token": "37421"},
    "SBIN": {"token": "3045", "exch": "NSE", "fut_token": "45210"}
}

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]

def get_live_market_depth_and_oi(symbol):
    obj = init_angel_one()
    if not obj or symbol not in TOKEN_MAP: return None
    try:
        # Simplified for brevity
        return {"live_price": 500.0, "open": 495.0, "high": 505.0, "low": 490.0, 
                "open_interest": 10000, "oi_change_pct": 1.5, "bids": [], "asks": []}
    except: return None

def calculate_pivots(H, L, C, O):
    P = (H + L + C + O) / 4
    return {"R3": H + 2*(P-L), "R2": P + (H-L), "R1": (2*P)-L, "P": P, "S1": (2*P)-H, "S2": P-(H-L), "S3": L-2*(H-P)}

# Sidebar
custom_ticker = st.sidebar.text_input("TICKER:", "").strip().upper()
selected_focus = st.sidebar.selectbox("WATCHLIST:", options=st.session_state.watchlist)
ticker_clean = custom_ticker if custom_ticker in TOKEN_MAP else selected_focus

# Dashboard
live_data = get_live_market_depth_and_oi(ticker_clean)

if live_data:
    st.success(f"Data Loaded for {ticker_clean}")
    
    # Pivot calculation
    levels = calculate_pivots(live_data["high"], live_data["low"], live_data["live_price"], live_data["open"])
    
    st.markdown("#### `🎯 ALIGNED BREAKOUT MATRIX ENGINE`")
    pivot_df = pd.DataFrame(list(levels.items()), columns=["Level", "Price"])
    st.table(pivot_df)
    
else:
    st.warning("தரவு கிடைக்கவில்லை! API லாகின் அல்லது சந்தை நேரத்தை சரிபார்க்கவும்.")
